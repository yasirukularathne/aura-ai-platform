import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.ml.prediction.predictor import (
    ChurnPredictor
)


predictor = ChurnPredictor()


customer = {

    "gender": "Female",

    "SeniorCitizen": 0,

    "Partner": "yes",

    "Dependents": "Yes",

    "tenure": 3,

    "PhoneService": "No",

    "MultipleLines": "No",

    "InternetService": "Fiber optic",

    "OnlineSecurity": "Yes",

    "OnlineBackup": "Yes",

    "DeviceProtection": "Yes",

    "TechSupport": "Yes",

    "StreamingTV": "No",

    "StreamingMovies": "Yes",

    "Contract": "Month-to-month",

    "PaperlessBilling": "Yes",

    "PaymentMethod": "Electronic check",

    "MonthlyCharges": 1.70,

    "TotalCharges": 0.65

}


result = predictor.predict(
    customer
)


print("\nPrediction:")
print(result)
