import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder


TARGET = "Churn"

ID_COLUMN = "customerID"


def load_data(
    path: str
) -> pd.DataFrame:

    df = pd.read_csv(
        path
    )

    return df


def clean_data(
    df: pd.DataFrame
) -> pd.DataFrame:

    df = df.copy()

    # Remove duplicate rows
    df = df.drop_duplicates()

    # Convert TotalCharges to numeric
    #
    # Invalid/blank values become NaN
    df["TotalCharges"] = pd.to_numeric(
        df["TotalCharges"],
        errors="coerce"
    )

    # Convert target
    df[TARGET] = df[TARGET].map({
        "Yes": 1,
        "No": 0
    })

    return df


def prepare_features(
    df: pd.DataFrame
):

    df = df.copy()

    # Separate target
    y = df[TARGET]

    # Remove target
    X = df.drop(
        columns=[TARGET]
    )

    # Remove customer ID
    #
    # customerID identifies the customer,
    # but it should not be a predictive feature.
    X = X.drop(
        columns=[ID_COLUMN]
    )

    return X, y


def create_preprocessor(
    X: pd.DataFrame
):

    numerical_features = (
        X.select_dtypes(
            include=[
                "int64",
                "float64"
            ]
        )
        .columns
        .tolist()
    )

    categorical_features = (
        X.select_dtypes(
            include=[
                "object",
                "category",
                "bool"
            ]
        )
        .columns
        .tolist()
    )

    numerical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            )
        )
    ])

    categorical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            )
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore"
            )
        )
    ])

    preprocessor = ColumnTransformer([
        (
            "numerical",
            numerical_pipeline,
            numerical_features
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features
        )
    ])

    return preprocessor