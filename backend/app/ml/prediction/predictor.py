"""Prediction helpers for ML workflows."""

from pathlib import Path

import joblib
import pandas as pd

from .risk import (
    calculate_risk
)


BASE_DIR = Path(
    __file__
).resolve().parents[4]


MODEL_PATH = (
    BASE_DIR
    / "models"
    / "churn_model.joblib"
)


PREPROCESSOR_PATH = (
    BASE_DIR
    / "models"
    / "churn_preprocessor.joblib"
)


class ChurnPredictor:

    def __init__(self):
        print(
            "Loading churn model..."
        )

        self.model = joblib.load(
            MODEL_PATH
        )

        print(
            "Loading preprocessor..."
        )

        self.preprocessor = joblib.load(
            PREPROCESSOR_PATH
        )

    def predict(
        self,
        customer: dict
    ):
        # Convert dictionary to DataFrame
        df = pd.DataFrame(
            [customer]
        )

        # Remove ID if supplied
        if "customerID" in df.columns:
            df = df.drop(
                columns=[
                    "customerID"
                ]
            )

        # Apply SAME preprocessing
        processed = (
            self.preprocessor.transform(
                df
            )
        )

        # Probability
        probability = (
            self.model
            .predict_proba(
                processed
            )[0][1]
        )

        risk_level = calculate_risk(
            probability
        )

        # Class
        prediction = int(
            probability >= 0.5
        )

        return {
            "churn_prediction": prediction,
            "churn_probability": float(probability),
            "risk_level": risk_level,
        }
