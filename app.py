"""Streamlit UI for the Document Intelligence Assistant.

Run with:  streamlit run app.py

Everything runs locally: PDF parsing (pypdf), embeddings (all-MiniLM-L6-v2 via
ChromaDB), hybrid retrieval (ChromaDB + BM25) and answer generation (Ollama).

Optional environment variables:
    CHROMA_DB_DIR   where the vector database lives (default ./chroma_db)
    OLLAMA_URL      where Ollama listens (default http://localhost:11434)
    OLLAMA_MODEL    which Ollama model answers questions (default qwen3:4b)
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import streamlit as st

from src.document_processor import DocumentProcessingError, DocumentProcessor
from src.rag_pipeline import (
    DEFAULT_MODEL,
    DEFAULT_OLLAMA_URL,
    ModelNotFoundError,
    OllamaClient,
    OllamaConnectionError,
    OllamaError,
    RAGPipeline,
    RAGPipelineError,
    RAGResponse,
)
from src.vector_store import DEFAULT_PERSIST_DIRECTORY, DEFAULT_TOP_K, VectorStore, VectorStoreError

APP_TITLE = "Document Intelligence Assistant"
APP_SUBTITLE = (
    "Upload your documents, ask questions, and get AI-powered answers with source citations "
    "— running entirely on your machine."
)
ALL_DOCUMENTS = "All documents"
STATUS_CACHE_SECONDS = 30

logger = logging.getLogger("app")


# --- Configuration ----------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    """Runtime configuration, read from environment variables."""

    db_dir: str
    ollama_url: str
    model: str

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            db_dir=os.getenv("CHROMA_DB_DIR", DEFAULT_PERSIST_DIRECTORY),
            ollama_url=os.getenv("OLLAMA_URL", DEFAULT_OLLAMA_URL),
            model=os.getenv("OLLAMA_MODEL", DEFAULT_MODEL),
        )


def configure_logging() -> None:
    """Send backend logs (operations and counts only, never document text) to the terminal."""
    for name in ("src", "app"):
        log = logging.getLogger(name)
        if not log.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
            log.addHandler(handler)
            log.setLevel(logging.INFO)
            log.propagate = False


# --- Cached backend objects (created once per server process) ----------------

@st.cache_resource(show_spinner="Loading the local embedding model…")
def get_vector_store(db_dir: str) -> VectorStore:
    """Open the persistent ChromaDB store once; this also loads the embedding model."""
    return VectorStore(persist_directory=db_dir)


@st.cache_resource
def get_processor() -> DocumentProcessor:
    return DocumentProcessor()


@st.cache_resource
def get_pipeline(db_dir: str, ollama_url: str, model: str) -> RAGPipeline:
    """Build the RAG pipeline once, sharing the cached vector store."""
    return RAGPipeline(get_vector_store(db_dir), OllamaClient(ollama_url), model=model)


# --- System status ------------------------------------------------------------

@dataclass(frozen=True)
class OllamaStatus:
    """Result of checking the local Ollama server.

    Attributes:
        running: Ollama answered on its API port.
        model_available: The configured model is downloaded.
        message: Explanation suitable for showing to the user.
    """

    running: bool
    model_available: bool
    message: str

    @property
    def ready(self) -> bool:
        return self.running and self.model_available


@st.cache_data(ttl=STATUS_CACHE_SECONDS, show_spinner=False)
def check_ollama(_pipeline: RAGPipeline, ollama_url: str, model: str) -> OllamaStatus:
    """Check Ollama with the pipeline's own health check; cached briefly to avoid a call per rerun.

    ``ollama_url`` and ``model`` are the cache key; ``_pipeline`` is not hashed.
    """
    try:
        _pipeline.check_model_available()
    except ModelNotFoundError as exc:
        return OllamaStatus(running=True, model_available=False, message=str(exc))
    except OllamaError as exc:  # includes OllamaConnectionError
        return OllamaStatus(running=False, model_available=False, message=str(exc))
    return OllamaStatus(running=True, model_available=True, message=f"{model} is ready")


# --- Ingestion ----------------------------------------------------------------

class UploadedPDF(Protocol):
    """What ingestion needs from an upload; Streamlit's UploadedFile satisfies it."""

    name: str

    def getvalue(self) -> bytes: ...


IngestStatus = Literal["indexed", "skipped", "empty", "error"]


@dataclass(frozen=True)
class IngestResult:
    """Outcome of ingesting one uploaded file."""

    filename: str
    status: IngestStatus
    message: str


def ingest_files(
    files: Sequence[UploadedPDF],
    processor: DocumentProcessor,
    store: VectorStore,
    indexed_hashes: dict[str, str],
    replace_existing: bool = False,
) -> list[IngestResult]:
    """Process uploaded PDFs and add them to the vector store, skipping needless re-ingestion.

    A file is skipped when it repeats within the same upload, when it is
    already indexed under the same name (unless ``replace_existing``), when
    it is unchanged since this session indexed it, or when the same content
    is already indexed under another name. ``indexed_hashes`` maps filenames
    to SHA-256 digests of what this session indexed, and is updated in place.

    Args:
        files: Uploaded files.
        processor: Splits PDFs into chunks.
        store: Where chunks are stored.
        indexed_hashes: Session record of indexed content, updated in place.
        replace_existing: Re-index files whose name is already in the store.

    Returns:
        One result per uploaded file, in upload order.
    """
    try:
        existing = {doc.source for doc in store.list_documents()}
    except VectorStoreError as exc:
        return [IngestResult(f.name, "error", f"Could not read the document index: {exc}") for f in files]

    results: list[IngestResult] = []
    seen: set[str] = set()
    for upload in files:
        name = upload.name
        data = upload.getvalue()
        digest = hashlib.sha256(data).hexdigest()

        if name in seen:
            results.append(IngestResult(name, "skipped", "Listed more than once in this upload; processed once."))
            continue
        seen.add(name)

        if name in existing and indexed_hashes.get(name) == digest:
            results.append(IngestResult(name, "skipped", "Already indexed and unchanged."))
            continue
        if name in existing and not replace_existing:
            results.append(IngestResult(
                name, "skipped", "Already indexed. Tick “Re-index files already indexed” to replace it."
            ))
            continue
        twin = next(
            (other for other, h in indexed_hashes.items() if h == digest and other != name and other in existing),
            None,
        )
        if twin:
            results.append(IngestResult(name, "skipped", f"Same content as {twin}, which is already indexed."))
            continue

        try:
            document = processor.process_pdf(data, source_name=name)
        except DocumentProcessingError as exc:
            results.append(IngestResult(name, "error", str(exc)))
            continue
        if document.is_empty:
            results.append(IngestResult(
                name, "empty",
                f"No extractable text in {document.page_count} page(s); it may be a scanned PDF. Nothing was indexed.",
            ))
            continue

        try:
            stored = store.add_documents(document.chunks)
        except VectorStoreError as exc:
            results.append(IngestResult(name, "error", f"Could not store chunks: {exc}"))
            continue

        verb = "Re-indexed" if name in existing else "Indexed"
        indexed_hashes[name] = digest
        existing.add(name)
        note = f" Skipped {len(document.skipped_pages)} page(s) without text." if document.skipped_pages else ""
        results.append(IngestResult(
            name, "indexed", f"{verb} {stored} chunks from {document.page_count} page(s).{note}"
        ))
        logger.info("Ingested %s: %d chunks", name, stored)
    return results


# --- Rendering helpers ----------------------------------------------------------

_MARKDOWN_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$])")


def escape_markdown(text: str) -> str:
    """Escape text so Streamlit shows it literally (filenames, excerpts)."""
    return _MARKDOWN_SPECIAL.sub(r"\\\1", text)


def escape_dollars(text: str) -> str:
    """Stop "$4.2 million ... $5" being rendered as LaTeX while keeping other Markdown."""
    return text.replace("$", r"\$")


def source_label(source: str, page: int) -> str:
    return f"📄 {escape_markdown(source)}, page {page}"


def render_response(response: RAGResponse) -> None:
    """Show an answer with its verified sources, unverified citations and retrieved excerpts."""
    if response.answer_found:
        st.markdown(escape_dollars(response.answer))
    else:
        st.info(f"**Not found in your documents.** {escape_dollars(response.answer)}", icon="🔍")

    if response.citations:
        st.markdown("**Sources**  \n" + "  \n".join(source_label(c.source, c.page) for c in response.citations))

    if response.unverified_citations:
        listed = ", ".join(escape_markdown(str(c)) for c in response.unverified_citations)
        st.warning(
            f"**Unverified citations:** {listed}. These don't match any excerpt the model was given, "
            "so treat them as unreliable.",
            icon="⚠️",
        )

    if response.retrieved_chunks:
        cited = {(c.source, c.page) for c in response.citations}
        with st.expander(f"Retrieved excerpts ({len(response.retrieved_chunks)})"):
            for chunk in response.retrieved_chunks:
                details = [f"similarity {chunk.similarity:.2f}"]
                if chunk.keyword_rank is not None:
                    details.append(f"keyword match #{chunk.keyword_rank}")
                if (chunk.source, chunk.page) in cited:
                    details.append("✅ cited")
                st.markdown(f"**{source_label(chunk.source, chunk.page)}** · " + " · ".join(details))
                st.markdown("> " + escape_markdown(chunk.text).replace("\n", "  \n> "))

    if response.model:
        timing = f" · {response.duration_seconds:.1f}s" if response.duration_seconds else ""
        st.caption(f"Answered locally by {response.model}{timing}")


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(escape_dollars(message["content"]))
        elif message.get("error"):
            st.error(message["error"], icon="🚫")
        else:
            render_response(message["response"])


def ask(pipeline: RAGPipeline, question: str, top_k: int, source: str | None) -> dict:
    """Answer a question and return a chat-history entry (answer or friendly error)."""
    try:
        return {"role": "assistant", "response": pipeline.answer_question(question, top_k=top_k, source=source)}
    except OllamaConnectionError as exc:
        check_ollama.clear()
        return {"role": "assistant", "error": f"Ollama is not reachable. {exc}"}
    except ModelNotFoundError as exc:
        check_ollama.clear()
        return {"role": "assistant", "error": str(exc)}
    except (RAGPipelineError, ValueError) as exc:
        return {"role": "assistant", "error": f"Something went wrong while answering: {exc}"}


# --- Page sections ----------------------------------------------------------------

def init_session_state() -> None:
    defaults = {
        "messages": [],
        "indexed_hashes": {},
        "ingest_results": [],
        "uploader_key": 0,
        "pending_delete": None,
        "notice": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def render_upload_section(processor: DocumentProcessor, store: VectorStore) -> None:
    st.subheader("Upload documents")
    files = st.file_uploader(
        "PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key=f"uploader_{st.session_state.uploader_key}",
        label_visibility="collapsed",
    )
    replace = st.checkbox("Re-index files already indexed", key="replace_existing")
    if st.button("Upload and process", type="primary", disabled=not files, width="stretch"):
        with st.spinner(f"Processing {len(files)} file(s) locally…"):
            st.session_state.ingest_results = ingest_files(
                files, processor, store, st.session_state.indexed_hashes, replace_existing=replace
            )
        st.session_state.uploader_key += 1  # clears the uploader
        st.rerun()

    show = {"indexed": st.success, "skipped": st.info, "empty": st.warning, "error": st.error}
    for result in st.session_state.ingest_results:
        show[result.status](f"**{escape_markdown(result.filename)}** — {escape_markdown(result.message)}")
    if st.session_state.ingest_results and st.button("Dismiss messages", key="dismiss_ingest"):
        st.session_state.ingest_results = []
        st.rerun()


def render_document_list(store: VectorStore, documents: list) -> None:
    header, refresh = st.columns([4, 1], vertical_alignment="center")
    header.subheader("Indexed documents")
    if refresh.button("🔄", key="refresh_documents", help="Refresh the document list and system status"):
        check_ollama.clear()
        st.rerun()

    if st.session_state.notice:
        st.success(st.session_state.notice)
        st.session_state.notice = None

    if not documents:
        st.caption("No documents yet.")
        return

    for doc in documents:
        name_col, delete_col = st.columns([5, 1], vertical_alignment="center")
        name_col.markdown(f"**{escape_markdown(doc.source)}**  \n{doc.chunk_count} chunks")
        if delete_col.button("🗑️", key=f"delete_{doc.source}", help=f"Delete {doc.source}"):
            st.session_state.pending_delete = doc.source
            st.rerun()

        if st.session_state.pending_delete == doc.source:
            st.warning(f"Delete **{escape_markdown(doc.source)}** from the index?")
            yes, no = st.columns(2)
            if yes.button("Delete", key=f"confirm_delete_{doc.source}", type="primary", width="stretch"):
                try:
                    removed = store.delete_document(doc.source)
                    st.session_state.notice = f"Deleted {doc.source} ({removed} chunks)."
                    st.session_state.indexed_hashes.pop(doc.source, None)
                except VectorStoreError as exc:
                    st.session_state.notice = None
                    st.error(f"Could not delete {doc.source}: {exc}")
                st.session_state.pending_delete = None
                st.rerun()
            if no.button("Cancel", key=f"cancel_delete_{doc.source}", width="stretch"):
                st.session_state.pending_delete = None
                st.rerun()


def render_question_settings(documents: list) -> tuple[str | None, int]:
    """Document filter and retrieval depth; returns (source filter, top_k)."""
    st.subheader("Ask about")
    options = [ALL_DOCUMENTS, *(doc.source for doc in documents)]
    if st.session_state.get("document_filter") not in options:
        st.session_state.document_filter = ALL_DOCUMENTS  # e.g. the selected document was deleted
    selected = st.selectbox("Document", options, key="document_filter", label_visibility="collapsed")
    with st.expander("Retrieval settings"):
        top_k = st.slider(
            "Excerpts to retrieve", min_value=1, max_value=10, value=DEFAULT_TOP_K, key="top_k",
            help="More excerpts give the model more context but make answers slower.",
        )
    if st.button("Clear chat", key="clear_chat", width="stretch", disabled=not st.session_state.messages):
        st.session_state.messages = []
        st.rerun()
    return (None if selected == ALL_DOCUMENTS else selected), top_k


def render_status(settings: Settings, store: VectorStore, status: OllamaStatus, documents: list) -> None:
    st.subheader("System status")
    if status.running:
        st.markdown(f"✅ **Ollama** running at `{settings.ollama_url}`")
    else:
        st.markdown(f"❌ **Ollama** not reachable at `{settings.ollama_url}`")
    if status.model_available:
        st.markdown(f"✅ **Model** `{settings.model}` available")
    elif status.running:
        st.markdown(f"❌ **Model** `{settings.model}` not downloaded")
    else:
        st.markdown(f"⚪ **Model** `{settings.model}` unknown (Ollama is down)")
    location = Path(store.persist_directory).resolve()
    st.markdown(f"✅ **ChromaDB** persistent storage  \n`{location}`")
    docs_col, chunks_col = st.columns(2)
    docs_col.metric("Documents", len(documents))
    chunks_col.metric("Chunks", sum(doc.chunk_count for doc in documents))


def render_health_banner(settings: Settings, status: OllamaStatus) -> None:
    if not status.running:
        st.error(
            "**Ollama isn't running**, so questions can't be answered yet. Open the Ollama app or run "
            f"`ollama serve` in a terminal, then press 🔄 in the sidebar.  \n\nDetails: {status.message}",
            icon="🔌",
        )
    elif not status.model_available:
        st.warning(
            f"**Model `{settings.model}` is not downloaded.** Run `ollama pull {settings.model}` in a terminal, "
            "then press 🔄 in the sidebar.",
            icon="📦",
        )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="📄", layout="wide")
    configure_logging()
    init_session_state()
    settings = Settings.from_env()

    st.title(f"📄 {APP_TITLE}")
    st.caption(APP_SUBTITLE)

    try:
        store = get_vector_store(settings.db_dir)
        documents = store.list_documents()
    except VectorStoreError as exc:
        st.error(f"**Could not open the document database** at `{settings.db_dir}`.  \n\n{exc}", icon="🗄️")
        st.stop()
    pipeline = get_pipeline(settings.db_dir, settings.ollama_url, settings.model)
    processor = get_processor()
    status = check_ollama(pipeline, settings.ollama_url, settings.model)

    with st.sidebar:
        render_upload_section(processor, store)
        st.divider()
        render_document_list(store, documents)
        st.divider()
        source, top_k = render_question_settings(documents)
        st.divider()
        render_status(settings, store, status, documents)

    render_health_banner(settings, status)
    if not documents:
        st.info("**Upload a PDF in the sidebar to get started.** Your files are processed on this machine.", icon="📥")

    for message in st.session_state.messages:
        render_message(message)

    scope = "all documents" if source is None else source
    if not documents:
        placeholder = "Upload a document to start asking questions"
    elif not status.ready:
        placeholder = "Waiting for Ollama…"
    else:
        placeholder = f"Ask a question about {scope}"
    question = st.chat_input(placeholder, disabled=not (documents and status.ready))

    if question and question.strip():
        user_message = {"role": "user", "content": question.strip()}
        st.session_state.messages.append(user_message)
        render_message(user_message)
        with st.chat_message("assistant"):
            with st.spinner(f"Searching {scope} and generating an answer locally…"):
                reply = ask(pipeline, question.strip(), top_k, source)
        st.session_state.messages.append(reply)
        st.rerun()  # redraw from history so the new answer renders like earlier ones


if __name__ == "__main__":
    main()
