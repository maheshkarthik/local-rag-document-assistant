from src.vector_store import VectorStore

store = VectorStore()

question = "What does error code E07 mean?"

results = store.search(question, top_k=3, source="kestrel-t2-thermostat-user-manual.pdf")

print(f"\nQuestion: {question}")
print(f"Results found: {len(results)}")

for i, result in enumerate(results, 1):
    print(f"\nResult {i}")
    print(f"Similarity: {result.similarity:.3f}")
    print(f"Page: {result.page}")
    print(f"Text: {result.text[:250]}")
