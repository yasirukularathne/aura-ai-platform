from app.agents.rag_agent import rag_graph


QUESTIONS = [
    (
        "Test 1 - Normal question",
        "Is HIV testing required before employment?",
    ),
    ("Test 2 - Vague question", "What about HIV?"),
    (
        "Test 3 - Unsupported question",
        "What is the company's policy for Mars colonization?",
    ),
]


def run_test(label: str, question: str) -> None:
    print(f"\n{'=' * 70}")
    print(label)
    print(f"Question: {question}")
    print(f"{'=' * 70}")

    result = rag_graph.invoke({"question": question})
    search_query = result.get("search_query", question)

    print("\n--- Query Processing ---")
    print(f"Original query: {question}")
    print(f"Search query:   {search_query}")
    if search_query.strip().lower() != question.strip().lower():
        print("Query was rewritten for retrieval.")

    retrieved = result.get("retrieved_documents", [])
    reranked = result.get("reranked_documents", [])
    print("\n--- Retrieval ---")
    print(f"Retrieved documents: {len(retrieved)}")
    print(f"Reranked documents:  {len(reranked)}")

    print("\n--- Evidence Check ---")
    if result.get("evidence_sufficient"):
        print("Relevant evidence found.")
    else:
        print(f"Low or insufficient relevance: {result.get('error', 'Unknown reason')}")

    print("\n--- Answer ---")
    print(result.get("answer", "No answer returned."))

    print("\n--- Citations ---")
    citations = result.get("citations", [])
    if citations:
        for citation in citations:
            print(citation)
    else:
        print("No citations.")


def main() -> None:
    for label, question in QUESTIONS:
        run_test(label, question)


if __name__ == "__main__":
    main()