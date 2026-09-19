from app.rag.retrieval.retriever import get_retriever


retriever = get_retriever()

query = "What is the refund policy?"

results = retriever.invoke(query)

print(f"Retrieved {len(results)} chunks")

for i, document in enumerate(results):

    print(f"\n===== RESULT {i + 1} =====")

    print(document.page_content)

    print("\nMetadata:")
    print(document.metadata)