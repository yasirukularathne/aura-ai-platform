from pathlib import Path

import joblib

from sklearn.model_selection import train_test_split

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    confusion_matrix
)

from xgboost import XGBClassifier

from app.ml.preprocessing.preprocess import (
    load_data,
    clean_data,
    prepare_features,
    create_preprocessor
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(
    __file__
).resolve().parents[4]


DATA_PATH = (
    BASE_DIR
    / "data"
    / "datasets"
    / "customer_churn.csv"
)


MODEL_DIR = (
    BASE_DIR
    / "models"
)


MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# TRAIN
# =========================================================

def train():

    print("\n")
    print("=" * 70)
    print("                 AURA CHURN MODEL TRAINING")
    print("=" * 70)


    # -----------------------------------------------------
    # LOAD DATA
    # -----------------------------------------------------

    print("\n[1/8] Loading dataset...")
    print("-" * 70)

    df = load_data(
        str(DATA_PATH)
    )

    print(
        "Dataset path:",
        DATA_PATH
    )

    print(
        "Raw shape:",
        df.shape
    )

    print(
        "Number of rows:",
        df.shape[0]
    )

    print(
        "Number of columns:",
        df.shape[1]
    )

    print(
        "Columns:",
        df.columns.tolist()
    )


    # -----------------------------------------------------
    # CLEAN
    # -----------------------------------------------------

    print("\n[2/8] Cleaning dataset...")
    print("-" * 70)

    df = clean_data(
        df
    )

    print(
        "Cleaned shape:",
        df.shape
    )

    print(
        "Rows after cleaning:",
        len(df)
    )

    print(
        "Columns after cleaning:",
        len(df.columns)
    )

    print(
        "Cleaning completed successfully."
    )


    # -----------------------------------------------------
    # FEATURES / TARGET
    # -----------------------------------------------------

    print("\n[3/8] Preparing features and target...")
    print("-" * 70)

    X, y = prepare_features(
        df
    )


    print(
        "\nFeatures:"
    )

    print(
        X.columns.tolist()
    )

    print(
        "\nNumber of input features:",
        X.shape[1]
    )

    print(
        "\nTarget distribution:"
    )

    print(
        y.value_counts()
    )

    print(
        "\nTarget distribution (%):"
    )

    print(
        (y.value_counts(normalize=True) * 100).round(2)
    )


    # -----------------------------------------------------
    # TRAIN / TEST SPLIT
    # -----------------------------------------------------

    print("\n[4/8] Splitting dataset...")
    print("-" * 70)

    X_train, X_test, y_train, y_test = (
        train_test_split(
            X,
            y,
            test_size=0.20,
            random_state=42,
            stratify=y
        )
    )


    print(
        "Training samples:",
        len(X_train)
    )

    print(
        "Testing samples:",
        len(X_test)
    )

    print(
        "Training percentage:",
        f"{len(X_train) / len(X) * 100:.2f}%"
    )

    print(
        "Testing percentage:",
        f"{len(X_test) / len(X) * 100:.2f}%"
    )


    # -----------------------------------------------------
    # PREPROCESSOR
    # -----------------------------------------------------

    print("\n[5/8] Preprocessing features...")
    print("-" * 70)

    print(
        "Creating preprocessing pipeline..."
    )

    preprocessor = create_preprocessor(
        X_train
    )


    print(
        "Fitting preprocessor on training data..."
    )

    # IMPORTANT:
    #
    # Fit ONLY on training data.
    #

    X_train_processed = (
        preprocessor.fit_transform(
            X_train
        )
    )


    print(
        "Transforming test data..."
    )

    X_test_processed = (
        preprocessor.transform(
            X_test
        )
    )


    print(
        "\nOriginal training shape:",
        X_train.shape
    )

    print(
        "Processed training shape:",
        X_train_processed.shape
    )

    print(
        "Original testing shape:",
        X_test.shape
    )

    print(
        "Processed testing shape:",
        X_test_processed.shape
    )

    print(
        "\nPreprocessing completed successfully."
    )


    # -----------------------------------------------------
    # XGBOOST
    # -----------------------------------------------------

    print("\n[6/8] Creating XGBoost model...")
    print("-" * 70)


    model = XGBClassifier(

        n_estimators=300,

        max_depth=6,

        learning_rate=0.05,

        subsample=0.8,

        colsample_bytree=0.8,

        eval_metric="logloss",

        random_state=42

    )


    print(
        "Model: XGBClassifier"
    )

    print(
        "Number of boosting rounds:",
        300
    )

    print(
        "Max depth:",
        6
    )

    print(
        "Learning rate:",
        0.05
    )

    print(
        "Subsample:",
        0.8
    )

    print(
        "Column sampling:",
        0.8
    )

    print(
        "Evaluation metric:",
        "logloss"
    )


    print("\nStarting XGBoost training...")
    print(
        "Training progress will be displayed below."
    )

    print(
        "=" * 70
    )


    # -----------------------------------------------------
    # TRAIN MODEL
    # -----------------------------------------------------

    model.fit(
        X_train_processed,
        y_train,

        # Added only for training progress
        # This allows XGBoost to show logloss
        # during training.
        eval_set=[
            (
                X_train_processed,
                y_train
            ),
            (
                X_test_processed,
                y_test
            )
        ],

        # Print every 10 boosting rounds
        verbose=10
    )


    print(
        "=" * 70
    )

    print(
        "\nXGBoost training completed."
    )

    print(
        "Total boosting rounds:",
        model.get_booster().num_boosted_rounds()
    )


    # -----------------------------------------------------
    # PREDICTION
    # -----------------------------------------------------

    print("\n[7/8] Running predictions...")
    print("-" * 70)


    print(
        "Generating class predictions..."
    )

    predictions = (
        model.predict(
            X_test_processed
        )
    )


    print(
        "Generating churn probabilities..."
    )

    probabilities = (
        model.predict_proba(
            X_test_processed
        )[:, 1]
    )


    print(
        "Prediction completed."
    )

    print(
        "Number of predictions:",
        len(predictions)
    )

    print(
        "Probability range:",
        f"{probabilities.min():.4f}",
        "to",
        f"{probabilities.max():.4f}"
    )


    # -----------------------------------------------------
    # METRICS
    # -----------------------------------------------------

    print(
        "\nCalculating evaluation metrics..."
    )


    accuracy = accuracy_score(
        y_test,
        predictions
    )


    precision = precision_score(
        y_test,
        predictions,
        zero_division=0
    )


    recall = recall_score(
        y_test,
        predictions,
        zero_division=0
    )


    f1 = f1_score(
        y_test,
        predictions,
        zero_division=0
    )


    roc_auc = roc_auc_score(
        y_test,
        probabilities
    )


    # -----------------------------------------------------
    # RESULTS
    # -----------------------------------------------------

    print(
        "\n"
        + "=" * 70
    )

    print(
        "                    MODEL EVALUATION"
    )

    print(
        "=" * 70
    )


    print(
        f"Accuracy : {accuracy:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall   : {recall:.4f}"
    )

    print(
        f"F1 Score : {f1:.4f}"
    )

    print(
        f"ROC-AUC  : {roc_auc:.4f}"
    )


    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "No Churn",
                "Churn"
            ],
            zero_division=0
        )
    )


    print(
        "\nConfusion Matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            predictions
        )
    )


    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    print("\n[8/8] Saving trained model...")
    print("-" * 70)


    model_path = (
        MODEL_DIR
        / "churn_model.joblib"
    )


    preprocessor_path = (
        MODEL_DIR
        / "churn_preprocessor.joblib"
    )


    print(
        "Saving XGBoost model..."
    )

    joblib.dump(
        model,
        model_path
    )


    print(
        "Saving preprocessor..."
    )

    joblib.dump(
        preprocessor,
        preprocessor_path
    )


    print(
        "\nModel saved to:"
    )

    print(
        model_path
    )


    print(
        "\nPreprocessor saved to:"
    )

    print(
        preprocessor_path
    )


    print(
        "\n"
        + "=" * 70
    )

    print(
        "             TRAINING COMPLETED SUCCESSFULLY"
    )

    print(
        "=" * 70
    )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    train()
