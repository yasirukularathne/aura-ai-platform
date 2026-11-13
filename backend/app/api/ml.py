from app.ml.prediction.predictor import ChurnPredictor
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(

    prefix="/api/ml",

    tags=[
        "Machine Learning"
    ]

)


try:
    predictor = ChurnPredictor()
except (FileNotFoundError, OSError, ValueError):
    predictor = None


class ChurnRequest(
    BaseModel
):

    customer: dict


@router.post(
    "/churn"
)
def predict_churn(
    request: ChurnRequest
):
    if predictor is None:
        raise HTTPException(
            status_code=503,
            detail="Churn prediction model is not available",
        )

    return predictor.predict(
        request.customer
    )