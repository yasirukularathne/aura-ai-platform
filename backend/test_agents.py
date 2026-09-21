from app.agents.rag_agent import rag_graph
from app.agents.ml_agent import ml_graph


# ============================================================
# RAG AGENT TESTS
# ============================================================

RAG_QUESTIONS = [
    (
        "RAG Test 1 - Normal question",
        "Is HIV testing required before employment?",
    ),
    (
        "RAG Test 2 - Vague question",
        "What about HIV?",
    ),
    (
        "RAG Test 3 - Unsupported question",
        "What is the company's policy for Mars colonization?",
    ),
]


def run_rag_test(label: str, question: str) -> None:

    print("\n")
    print("=" * 70)
    print("RAG AGENT")
    print("=" * 70)

    print(label)
    print(f"Question: {question}")

    print("-" * 70)

    try:

        result = rag_graph.invoke(
            {
                "question": question
            }
        )

        # ----------------------------------------------------
        # Query Processing
        # ----------------------------------------------------

        search_query = result.get(
            "search_query",
            question
        )

        print("\n--- Query Processing ---")
        print(f"Original query: {question}")
        print(f"Search query:   {search_query}")

        if search_query.strip().lower() != question.strip().lower():
            print("Query was rewritten for retrieval.")

        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        retrieved = result.get(
            "retrieved_documents",
            []
        )

        reranked = result.get(
            "reranked_documents",
            []
        )

        print("\n--- Retrieval ---")
        print(
            f"Retrieved documents: {len(retrieved)}"
        )
        print(
            f"Reranked documents:  {len(reranked)}"
        )

        # ----------------------------------------------------
        # Evidence
        # ----------------------------------------------------

        print("\n--- Evidence Check ---")

        if result.get("evidence_sufficient"):

            print("Relevant evidence found.")

            if "evidence_score" in result:
                print(
                    f"Evidence score: "
                    f"{result['evidence_score']}"
                )

        else:

            print(
                "Low or insufficient relevance."
            )

            print(
                f"Reason: "
                f"{result.get('error', 'Unknown reason')}"
            )

        # ----------------------------------------------------
        # Answer
        # ----------------------------------------------------

        print("\n--- Answer ---")

        print(
            result.get(
                "answer",
                "No answer returned."
            )
        )

        # ----------------------------------------------------
        # Citations
        # ----------------------------------------------------

        print("\n--- Citations ---")

        citations = result.get(
            "citations",
            []
        )

        if citations:

            for citation in citations:
                print(citation)

        else:

            print("No citations.")

    except Exception as e:

        print("\n--- RAG ERROR ---")
        print(type(e).__name__)
        print(str(e))


# ============================================================
# ML AGENT TESTS
# ============================================================

ML_CUSTOMERS = [
    (
        "ML Test 1 - Existing customer",
        "7590-VHVEG",
    ),
    (
        "ML Test 2 - Another customer",
        "5575-GNVDE",
    ),
    (
        "ML Test 3 - Non-existing customer",
        "INVALID-CUSTOMER",
    ),
]


def run_ml_test(
    label: str,
    customer_id: str
) -> None:

    print("\n")
    print("=" * 70)
    print("ML AGENT")
    print("=" * 70)

    print(label)
    print(f"Customer ID: {customer_id}")

    print("-" * 70)

    try:

        result = ml_graph.invoke(
            {
                "customer_id": customer_id
            }
        )

        # ----------------------------------------------------
        # Customer
        # ----------------------------------------------------

        print("\n--- Customer ---")

        print(
            f"Customer ID: "
            f"{result.get('customer_id', customer_id)}"
        )

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        if result.get("error"):

            print("\n--- Error ---")

            print(
                result["error"]
            )

            return

        # ----------------------------------------------------
        # Prediction
        # ----------------------------------------------------

        print("\n--- Prediction ---")

        prediction = result.get(
            "churn_prediction"
        )

        probability = result.get(
            "churn_probability"
        )

        print(
            f"Churn prediction: {prediction}"
        )

        if probability is not None:

            print(
                f"Churn probability: "
                f"{probability:.4f}"
            )

        # ----------------------------------------------------
        # Customer Data
        # ----------------------------------------------------

        print("\n--- Customer Data ---")

        customer_data = result.get(
            "customer_data",
            {}
        )

        for key, value in customer_data.items():

            print(
                f"{key}: {value}"
            )

    except Exception as e:

        print("\n--- ML ERROR ---")

        print(
            type(e).__name__
        )

        print(
            str(e)
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("#" * 70)
    print("AURA AI PLATFORM")
    print("AGENT INDEPENDENT INTEGRATION TEST")
    print("#" * 70)

    # ========================================================
    # RAG AGENT
    # ========================================================

    print("\n\n")
    print("#" * 70)
    print("TESTING RAG AGENT")
    print("#" * 70)

    for label, question in RAG_QUESTIONS:

        run_rag_test(
            label,
            question
        )

    # ========================================================
    # ML AGENT
    # ========================================================

    print("\n\n")
    print("#" * 70)
    print("TESTING ML AGENT")
    print("#" * 70)

    for label, customer_id in ML_CUSTOMERS:

        run_ml_test(
            label,
            customer_id
        )

    # ========================================================
    # COMPLETE
    # ========================================================

    print("\n\n")
    print("#" * 70)
    print("ALL AGENT TESTS COMPLETED")
    print("#" * 70)


if __name__ == "__main__":
    main()