import json
from pathlib import Path
from typing import Any


def load_evaluation_dataset(path: str | Path) -> dict[str, Any]:
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, dict):
        raise ValueError("Evaluation dataset must be a JSON object")

    cases = dataset.get("cases")
    if not isinstance(cases, list):
        raise ValueError("Evaluation dataset must contain a cases list")

    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"Evaluation case {index} must be a JSON object")
        if not case.get("question"):
            raise ValueError(f"Evaluation case {index} is missing question")

    return dataset
