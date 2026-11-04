from pathlib import Path

from src.document_processor import DocumentProcessor
from src.vector_store import VectorStore

SAMPLES_DIR = Path("data/samples")

processor = DocumentProcessor()
store = VectorStore()

# 1. Extract text, create chunks and store them for every sample PDF.
#    Re-running is safe: documents that are already stored are overwritten, not duplicated.
print("\n--- Indexing sample documents ---")
for pdf in sorted(SAMPLES_DIR.glob("*.pdf")):
    document = processor.process_pdf(str(pdf))
    if document.is_empty:
        print(f"{pdf.name}: no extractable text found, skipped")
        continue
    stored = store.add_documents(document.chunks)
    print(f"{document.source}: {document.page_count} pages, {stored} chunks")

# 2. Show what the database now contains
print("\n--- ChromaDB Results ---")
print(f"Documents in database: {len(store.list_documents())}")
print(f"Total chunks in database: {store.count()}")
