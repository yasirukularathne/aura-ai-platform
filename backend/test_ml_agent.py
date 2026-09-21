from app.agents.ml_agent import ml_graph


CUSTOMERS = [
    (
        "Test 1 - Existing customer",
        "7590-VHVEG",
    ),
    (
        "Test 2 - Another customer",
        "5575-GNVDE",
    ),
    (
        "Test 3 - Non-existing customer",
        "INVALID-CUSTOMER",
    ),
]


def run_test(label: str, customer_id: str) -> None:

    print(f"\n{'=' * 70}")
    print(label)
    print(f"Customer ID: {customer_id}")
    print(f"{'=' * 70}")

    result = ml_graph.invoke(
        {
            "customer_id": customer_id
        }
    )

    print("\n--- Customer ---")

    print(
        f"Customer ID: "
        f"{result.get('customer_id', customer_id)}"
    )

    if result.get("error"):

        print("\n--- Error ---")
        print(result["error"])
        return

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

    print(
        f"Churn probability: {probability:.4f}"
    )

    print("\n--- Customer Data ---")

    customer_data = result.get(
        "customer_data",
        {}
    )

    for key, value in customer_data.items():
        print(f"{key}: {value}")


def main() -> None:

    for label, customer_id in CUSTOMERS:

        run_test(
            label,
            customer_id
        )


if __name__ == "__main__":
    main()