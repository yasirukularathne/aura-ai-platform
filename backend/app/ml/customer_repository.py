from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[3]

DATASET_PATH = (
    BASE_DIR
    / "data"
    / "datasets"
    / "customer_churn.csv"
)

class CustomerRepository:

    def __init__(self):
        print("[ML] Loading customer dataset...")

        self.df = pd.read_csv(DATASET_PATH)

        print(f"[ML] Loaded {len(self.df)} customers.")

    def get_customer(self, customer_id: str):

        customer = self.df[
            self.df["customerID"].astype(str)
            == str(customer_id)
        ]

        if customer.empty:
            return None

        return customer.iloc[0].to_dict()