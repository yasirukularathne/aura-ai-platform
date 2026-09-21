"""Prediction helpers for ML workflows."""

from pathlib import Path

import joblib
import pandas as pd

from ..explainability.shap_explainer import (
    ChurnExplainer
)
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

        self.explainer = ChurnExplainer(
            self.model
        )

        self.feature_names = (
            self.preprocessor
            .get_feature_names_out()
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

        top_factors = self.explainer.top_factors(
            processed,
            self.feature_names
        )

        return {
            "churn_prediction": prediction,
            "churn_probability": float(probability),
            "risk_level": risk_level,
            "top_factors": top_factors,
        }
