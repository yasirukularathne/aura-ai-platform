from app.router import route_request


# ============================================================
# RAG TEST
# ============================================================

def test_rag_request():

    print("\n")
    print("=" * 70)
    print("APPLICATION ROUTER - RAG TEST")
    print("=" * 70)

    result = route_request(
        request_type="rag",
        question="Is HIV testing required before employment?"
    )

    print("\nSelected agent:")
    print(result.get("agent"))

    if result.get("error"):
        print("\nError:")
        print(result["error"])
        return

    rag_result = result["result"]

    print("\nAnswer:")
    print(
        rag_result.get(
            "answer",
            "No answer returned."
        )
    )

    print("\nCitations:")

    citations = rag_result.get(
        "citations",
        []
    )

    for citation in citations:
        print(citation)


# ============================================================
# ML TEST
# ============================================================

def test_ml_request():

    print("\n")
    print("=" * 70)
    print("APPLICATION ROUTER - ML TEST")
    print("=" * 70)

    result = route_request(
        request_type="ml",
        customer_id="7590-VHVEG"
    )

    print("\nSelected agent:")
    print(result.get("agent"))

    if result.get("error"):
        print("\nError:")
        print(result["error"])
        return

    ml_result = result["result"]

    print("\nCustomer ID:")
    print(
        ml_result.get(
            "customer_id",
            "Unknown"
        )
    )

    print("\nPrediction:")

    print(
        f"Churn prediction: "
        f"{ml_result.get('churn_prediction')}"
    )

    probability = ml_result.get(
        "churn_probability"
    )

    if probability is not None:

        print(
            f"Churn probability: "
            f"{probability:.4f}"
        )


# ============================================================
# INVALID REQUEST TEST
# ============================================================

def test_invalid_request():

    print("\n")
    print("=" * 70)
    print("APPLICATION ROUTER - INVALID REQUEST TEST")
    print("=" * 70)

    result = route_request(
        request_type="unknown"
    )

    print("\nResult:")

    print(
        result
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("\n")
    print("#" * 70)
    print("AURA APPLICATION ROUTER TEST")
    print("#" * 70)

    test_rag_request()

    test_ml_request()

    test_invalid_request()

    print("\n")
    print("#" * 70)
    print("ROUTER TESTS COMPLETED")
    print("#" * 70)


if __name__ == "__main__":
    main()