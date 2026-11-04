"""Tests for the Streamlit UI in app.py.

The UI tests run the real script headlessly with Streamlit's AppTest. Every
test points CHROMA_DB_DIR at a temporary directory (never ./chroma_db) and
replaces Ollama's HTTP API with an in-process fake, so nothing touches the
network or a real model.

Run from the project root with:  python -m unittest discover -s tests -t . -v
"""

import io
import json
import os
import re
import tempfile
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import streamlit as st
from streamlit.testing.v1 import AppTest

import app
from src.document_processor import DocumentChunk, DocumentProcessor
from src.vector_store import VectorStore
from tests.test_document_processor import make_pdf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_PATH = str(PROJECT_ROOT / "app.py")
URLOPEN = "src.rag_pipeline.urllib.request.urlopen"

CORPUS = [
    DocumentChunk("Jupiter is the largest planet in the solar system and has dozens of moons.", "space.pdf", 4, 0),
    DocumentChunk("Saturn is a gas giant planet with spectacular rings made of ice.", "space.pdf", 5, 1),
    DocumentChunk(
        "Employees accrue 1.5 days of paid vacation per month and must request leave two weeks in advance.",
        "hr.pdf", 7, 0,
    ),
]


def shown(markdown: str) -> str:
    """Markdown source as displayed: drop the backslash escapes the app adds."""
    return re.sub(r"\\(.)", r"\1", markdown)


def upload(name: str, data: bytes) -> SimpleNamespace:
    """Stands in for Streamlit's UploadedFile."""
    return SimpleNamespace(name=name, getvalue=lambda: data)


class FakeOllama:
    """Plays the role of Ollama's /api/tags and /api/chat endpoints."""

    def __init__(self) -> None:
        self.models = ["qwen3:4b"]
        self.reply = "Jupiter is the largest planet [space.pdf, page 4]."
        self.running = True
        self.chat_error: Exception | None = None
        self.chat_payloads: list[dict] = []

    def __call__(self, request, timeout):
        if not self.running:
            raise urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
        if request.full_url.endswith("/api/tags"):
            return io.BytesIO(json.dumps({"models": [{"name": m} for m in self.models]}).encode())
        payload = json.loads(request.data)
        self.chat_payloads.append(payload)
        if self.chat_error:
            raise self.chat_error
        body = {"model": payload["model"], "message": {"role": "assistant", "content": self.reply},
                "done": True, "done_reason": "stop", "prompt_eval_count": 300, "eval_count": 30}
        return io.BytesIO(json.dumps(body).encode())

    def prompt(self, index: int = -1) -> str:
        return self.chat_payloads[index]["messages"][1]["content"]


class TempStoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.db_dir = str(Path(self._tmp.name) / "chroma_db")


class IngestFilesTests(TempStoreTestCase):
    def setUp(self):
        super().setUp()
        self.store = VectorStore(self.db_dir)
        self.processor = DocumentProcessor()
        self.hashes: dict[str, str] = {}
        self.pdf = make_pdf([["Mercury is the closest planet to the Sun."], ["Venus is the hottest planet."]])

    def ingest(self, *files, replace=False):
        return app.ingest_files(list(files), self.processor, self.store, self.hashes, replace_existing=replace)

    def test_indexes_a_pdf(self):
        [result] = self.ingest(upload("planets.pdf", self.pdf))
        self.assertEqual(result.status, "indexed")
        self.assertIn("2 chunks from 2 page(s)", result.message)
        self.assertEqual(self.store.list_documents()[0].source, "planets.pdf")
        self.assertIn("planets.pdf", self.hashes)

    def test_same_file_again_is_skipped(self):
        self.ingest(upload("planets.pdf", self.pdf))
        with mock.patch.object(self.store, "add_documents") as add:
            [result] = self.ingest(upload("planets.pdf", self.pdf))
            add.assert_not_called()
        self.assertEqual(result.status, "skipped")
        self.assertIn("unchanged", result.message)

    def test_unchanged_file_skipped_even_when_replace_requested(self):
        self.ingest(upload("planets.pdf", self.pdf))
        [result] = self.ingest(upload("planets.pdf", self.pdf), replace=True)
        self.assertEqual(result.status, "skipped")

    def test_existing_name_with_new_content_needs_replace(self):
        self.ingest(upload("planets.pdf", self.pdf))
        changed = make_pdf([["Mars is red."]])
        [skipped] = self.ingest(upload("planets.pdf", changed))
        self.assertEqual(skipped.status, "skipped")
        self.assertIn("Re-index", skipped.message)

        [replaced] = self.ingest(upload("planets.pdf", changed), replace=True)
        self.assertEqual(replaced.status, "indexed")
        self.assertTrue(replaced.message.startswith("Re-indexed 1 chunks"))
        self.assertEqual(self.store.count(), 1)

    def test_document_indexed_in_an_earlier_session_is_not_reingested(self):
        self.ingest(upload("planets.pdf", self.pdf))
        self.hashes.clear()  # new browser session: no memory of what was indexed
        [result] = self.ingest(upload("planets.pdf", self.pdf))
        self.assertEqual(result.status, "skipped")

    def test_same_content_under_another_name_is_skipped(self):
        self.ingest(upload("planets.pdf", self.pdf))
        [result] = self.ingest(upload("planets copy.pdf", self.pdf))
        self.assertEqual(result.status, "skipped")
        self.assertIn("planets.pdf", result.message)

    def test_duplicate_within_one_upload(self):
        results = self.ingest(upload("planets.pdf", self.pdf), upload("planets.pdf", self.pdf))
        self.assertEqual([r.status for r in results], ["indexed", "skipped"])

    def test_invalid_and_empty_pdfs(self):
        results = self.ingest(
            upload("broken.pdf", b"not a pdf"),
            upload("scan.pdf", make_pdf([[], []])),
            upload("good.pdf", self.pdf),
        )
        self.assertEqual([r.status for r in results], ["error", "empty", "indexed"])
        self.assertIn("not a valid PDF", results[0].message)
        self.assertIn("scanned", results[1].message)
        self.assertEqual([d.source for d in self.store.list_documents()], ["good.pdf"])

    def test_document_text_never_logged(self):
        secret = "Confidential balance 98765 for account holder Zephyrina Quill."
        pdf = make_pdf([[secret]])
        with self.assertLogs("src", level="DEBUG") as src_logs, self.assertLogs("app", level="DEBUG") as app_logs:
            self.ingest(upload("private.pdf", pdf))
        logged = "\n".join(src_logs.output + app_logs.output)
        self.assertIn("private.pdf", logged)
        for fragment in ("98765", "Zephyrina", "Confidential"):
            self.assertNotIn(fragment, logged)


class HelperTests(unittest.TestCase):
    def test_escape_markdown(self):
        self.assertEqual(app.escape_markdown("my_file [v2].pdf"), r"my\_file \[v2\]\.pdf")

    def test_escape_dollars_keeps_other_markdown(self):
        self.assertEqual(app.escape_dollars("**$4.2m** to $5m"), r"**\$4.2m** to \$5m")

    def test_settings_default_to_project_database(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            settings = app.Settings.from_env()
        self.assertEqual((settings.db_dir, settings.ollama_url, settings.model),
                         ("./chroma_db", "http://localhost:11434", "qwen3:4b"))


class AppUITestCase(TempStoreTestCase):
    """Runs app.py headlessly with a temporary database and a fake Ollama."""

    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"CHROMA_DB_DIR": self.db_dir})
        env.start()
        self.addCleanup(env.stop)
        self.ollama = FakeOllama()
        patcher = mock.patch(URLOPEN, side_effect=self.ollama)
        patcher.start()
        self.addCleanup(patcher.stop)
        st.cache_resource.clear()
        st.cache_data.clear()
        self.addCleanup(st.cache_resource.clear)
        self.addCleanup(st.cache_data.clear)

    def seed(self, chunks=CORPUS) -> None:
        VectorStore(self.db_dir).add_documents(chunks)

    def run_app(self) -> AppTest:
        at = AppTest.from_file(APP_PATH, default_timeout=120).run()
        self.assert_no_exception(at)
        return at

    def assert_no_exception(self, at: AppTest) -> None:
        self.assertEqual([e.value for e in at.exception], [])

    def ask(self, at: AppTest, question: str) -> AppTest:
        at.chat_input[0].set_value(question).run()
        self.assert_no_exception(at)
        return at

    @staticmethod
    def sidebar_button(at: AppTest, label: str):
        return next(b for b in at.sidebar.button if b.label == label)

    @staticmethod
    def sidebar_text(at: AppTest) -> str:
        parts = [m.value for m in at.sidebar.markdown]
        parts += [e.value for kind in ("success", "info", "warning", "error") for e in getattr(at.sidebar, kind)]
        parts += [f"{m.label}={m.value}" for m in at.sidebar.metric]
        return shown("\n".join(parts))


class LayoutAndStatusTests(AppUITestCase):
    def test_title_subtitle_and_healthy_status(self):
        at = self.run_app()
        self.assertEqual(at.title[0].value, "📄 Document Intelligence Assistant")
        self.assertIn("running entirely on your machine", at.caption[0].value)
        text = self.sidebar_text(at)
        self.assertIn("✅ **Ollama** running", text)
        self.assertIn("✅ **Model** `qwen3:4b` available", text)
        self.assertIn("✅ **ChromaDB** persistent storage", text)
        self.assertIn(str(Path(self.db_dir).resolve()), text)

    def test_never_uses_the_real_database(self):
        at = self.run_app()
        self.assertNotIn(str((PROJECT_ROOT / "chroma_db").resolve()) + "`", self.sidebar_text(at))

    def test_empty_store_prompts_for_upload_and_disables_chat(self):
        at = self.run_app()
        self.assertIn("Upload a PDF", at.info[0].value)
        self.assertTrue(at.chat_input[0].disabled)
        self.assertIn("Documents=0", self.sidebar_text(at))

    def test_document_and_chunk_counts(self):
        self.seed()
        at = self.run_app()
        text = self.sidebar_text(at)
        self.assertIn("Documents=2", text)
        self.assertIn("Chunks=3", text)
        self.assertIn("**space.pdf**  \n2 chunks", text)
        self.assertFalse(at.chat_input[0].disabled)

    def test_ollama_not_running(self):
        self.seed()
        self.ollama.running = False
        at = self.run_app()
        self.assertIn("Ollama isn't running", at.error[0].value)
        self.assertIn("ollama serve", at.error[0].value)
        self.assertIn("❌ **Ollama** not reachable", self.sidebar_text(at))
        self.assertTrue(at.chat_input[0].disabled)

    def test_model_missing(self):
        self.seed()
        self.ollama.models = ["llama3.2:latest"]
        at = self.run_app()
        self.assertIn("ollama pull qwen3:4b", at.warning[0].value)
        self.assertIn("❌ **Model** `qwen3:4b` not downloaded", self.sidebar_text(at))
        self.assertTrue(at.chat_input[0].disabled)


class DocumentManagementTests(AppUITestCase):
    def test_upload_and_process(self):
        at = self.run_app()
        pdf = make_pdf([["Mercury is the closest planet to the Sun."]])
        at.sidebar.file_uploader[0].upload("mercury.pdf", pdf, "application/pdf").run()
        self.sidebar_button(at, "Upload and process").click().run()
        self.assert_no_exception(at)
        text = self.sidebar_text(at)
        self.assertIn("Indexed 1 chunks from 1 page(s)", text)
        self.assertIn("**mercury.pdf**  \n1 chunks", text)
        self.assertEqual(at.sidebar.file_uploader[0].value, [], "uploader is cleared after processing")

        at.sidebar.file_uploader[0].upload("mercury.pdf", pdf, "application/pdf").run()
        self.sidebar_button(at, "Upload and process").click().run()
        self.assertIn("Already indexed and unchanged", self.sidebar_text(at))
        self.assertEqual(VectorStore(self.db_dir).count(), 1)

    def test_upload_errors_are_shown(self):
        at = self.run_app()
        at.sidebar.file_uploader[0].upload("broken.pdf", b"not a pdf", "application/pdf").run()
        self.sidebar_button(at, "Upload and process").click().run()
        self.assert_no_exception(at)
        self.assertIn("not a valid PDF", at.sidebar.error[0].value)

    def test_upload_button_disabled_without_files(self):
        at = self.run_app()
        self.assertTrue(self.sidebar_button(at, "Upload and process").disabled)

    def test_delete_requires_confirmation(self):
        self.seed()
        at = self.run_app()
        at.sidebar.button(key="delete_space.pdf").click().run()
        at.sidebar.button(key="cancel_delete_space.pdf").click().run()
        self.assertEqual(VectorStore(self.db_dir).count(), 3)

        at.sidebar.button(key="delete_space.pdf").click().run()
        at.sidebar.button(key="confirm_delete_space.pdf").click().run()
        self.assert_no_exception(at)
        self.assertEqual([d.source for d in VectorStore(self.db_dir).list_documents()], ["hr.pdf"])
        text = self.sidebar_text(at)
        self.assertIn("Deleted space.pdf (2 chunks)", text)
        self.assertNotIn("**space.pdf**", text)

    def test_deleting_the_selected_document_resets_the_filter(self):
        self.seed()
        at = self.run_app()
        at.sidebar.selectbox(key="document_filter").set_value("space.pdf").run()
        at.sidebar.button(key="delete_space.pdf").click().run()
        at.sidebar.button(key="confirm_delete_space.pdf").click().run()
        self.assert_no_exception(at)
        self.assertEqual(at.sidebar.selectbox(key="document_filter").value, "All documents")

    def test_refresh_picks_up_documents_added_elsewhere(self):
        at = self.run_app()
        self.seed()
        at.sidebar.button(key="refresh_documents").click().run()
        self.assertIn("Documents=2", self.sidebar_text(at))


class ChatTests(AppUITestCase):
    def setUp(self):
        super().setUp()
        self.seed()
        self.at = self.run_app()

    def assistant(self, index: int = -1):
        return [m for m in self.at.chat_message if m.name == "assistant"][index]

    def test_answer_with_verified_sources_and_excerpts(self):
        self.ask(self.at, "Which planet is the biggest?")
        self.assertEqual([m.name for m in self.at.chat_message], ["user", "assistant"])
        reply = self.assistant()
        markdown = [shown(m.value) for m in reply.markdown]
        self.assertIn("Jupiter is the largest planet [space.pdf, page 4].", markdown)
        self.assertTrue(any("**Sources**" in m and "space.pdf, page 4" in m for m in markdown))
        expander = reply.expander[0]
        self.assertTrue(expander.label.startswith("Retrieved excerpts"))
        excerpt_text = shown("\n".join(m.value for m in expander.markdown))
        self.assertIn("✅ cited", excerpt_text)
        self.assertIn("Jupiter is the largest planet", excerpt_text)
        self.assertIn("Answered locally by qwen3:4b", reply.caption[0].value)
        self.assertEqual(len(self.ollama.chat_payloads), 1)

    def test_other_controls_do_not_call_the_model_again(self):
        self.ask(self.at, "Which planet is the biggest?")
        self.at.sidebar.slider(key="top_k").set_value(3).run()
        self.at.sidebar.selectbox(key="document_filter").set_value("hr.pdf").run()
        self.at.sidebar.button(key="refresh_documents").click().run()
        self.assertEqual(len(self.ollama.chat_payloads), 1)
        self.assertEqual(len(self.at.chat_message), 2, "history survives reruns")

    def test_multiple_questions_keep_history(self):
        self.ask(self.at, "Which planet is the biggest?")
        self.ollama.reply = "Employees accrue 1.5 days per month [hr.pdf, page 7]."
        self.ask(self.at, "How much vacation do employees get?")
        self.assertEqual([m.name for m in self.at.chat_message], ["user", "assistant", "user", "assistant"])
        self.assertEqual(len(self.ollama.chat_payloads), 2)

    def test_document_filter_and_top_k_reach_the_pipeline(self):
        self.at.sidebar.selectbox(key="document_filter").set_value("hr.pdf").run()
        self.at.sidebar.slider(key="top_k").set_value(1).run()
        self.ollama.reply = "Employees accrue 1.5 days per month [hr.pdf, page 7]."
        self.ask(self.at, "How much vacation do employees get?")
        prompt = self.ollama.prompt()
        self.assertIn('source="hr.pdf"', prompt)
        self.assertNotIn("space.pdf", prompt)
        self.assertEqual(prompt.count("<document "), 1)

    def test_not_found_is_clearly_indicated(self):
        self.ollama.reply = "The answer is not available in the provided documents."
        self.ask(self.at, "How many moons does Saturn have exactly?")
        info = self.assistant().info[0].value
        self.assertIn("Not found in your documents", info)
        self.assertFalse(any("**Sources**" in m.value for m in self.assistant().markdown))

    def test_irrelevant_question_skips_the_model(self):
        self.ask(self.at, "Who won the 1998 World Cup?")
        self.assertIn("Not found in your documents", self.assistant().info[0].value)
        self.assertEqual(self.ollama.chat_payloads, [])

    def test_unverified_citations_shown_separately(self):
        self.ollama.reply = "Jupiter is largest [space.pdf, page 4]. Mars is red [mars.pdf, page 1]."
        self.ask(self.at, "Which planet is the biggest?")
        reply = self.assistant()
        sources = shown(next(m.value for m in reply.markdown if "**Sources**" in m.value))
        self.assertIn("space.pdf, page 4", sources)
        self.assertNotIn("mars", sources)
        self.assertIn("Unverified citations", reply.warning[0].value)
        self.assertIn("mars", reply.warning[0].value)

    def test_dollar_amounts_are_not_rendered_as_math(self):
        self.ollama.reply = "Costs rose from $4 to $5 [space.pdf, page 4]."
        self.ask(self.at, "Which planet is the biggest?")
        self.assertIn(r"Costs rose from \$4 to \$5", self.assistant().markdown[0].value)

    def test_ollama_failure_during_chat_is_reported_and_history_kept(self):
        self.ask(self.at, "Which planet is the biggest?")
        self.ollama.chat_error = urllib.error.URLError(ConnectionRefusedError(61, "Connection refused"))
        self.ask(self.at, "Tell me about Saturn's rings")
        self.assertIn("Ollama is not reachable", self.assistant().error[0].value)
        self.assertEqual(len(self.at.chat_message), 4)

    def test_clear_chat(self):
        self.ask(self.at, "Which planet is the biggest?")
        self.sidebar_button(self.at, "Clear chat").click().run()
        self.assertEqual(len(self.at.chat_message), 0)
        self.assertTrue(self.sidebar_button(self.at, "Clear chat").disabled)


if __name__ == "__main__":
    unittest.main()
