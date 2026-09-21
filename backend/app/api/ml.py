from fastapi import APIRouter
from pydantic import BaseModel

from app.ml.prediction.predictor import (
    ChurnPredictor
)


router = APIRouter(

    prefix="/api/ml",

    tags=[
        "Machine Learning"
    ]

)


predictor = ChurnPredictor()


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

    return predictor.predict(
        request.customer
    )