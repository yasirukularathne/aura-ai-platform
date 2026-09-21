from app.ml.prediction.predictor import ChurnPredictor
from app.ml.customer_repository import CustomerRepository


predictor = ChurnPredictor()
customer_repository = CustomerRepository()


def churn_prediction_tool(customer_id: str):

    customer = customer_repository.get_customer(
        customer_id
    )

    if customer is None:
        return {
            "error": (
                f"Customer '{customer_id}' "
                "was not found."
            )
        }

    prediction_result = predictor.predict(
        customer
    )

    return {
        "customer_id": customer_id,
        "customer": customer,
        "churn_prediction": prediction_result[
            "churn_prediction"
        ],
        "churn_probability": prediction_result[
            "churn_probability"
        ]
    }