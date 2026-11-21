import argparse
import json
from pathlib import Path
from typing import Any

from .history import store_evaluation_result
from .runner import run_evaluation


def _live_runner(question: str) -> dict[str, Any]:
    from app.agents.rag_agent import rag_graph

    return dict(rag_graph.invoke({"question": question, "tenant_id": "evaluation"}))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AURA RAG evaluation.")
    parser.add_argument(
        "--dataset",
        default="backend/data/evaluation/rag_eval.json",
        type=Path,
    )
    parser.add_argument("--output-dir", default="backend/data/evaluation/results", type=Path)
    parser.add_argument("--k", default=5, type=int)
    args = parser.parse_args()

    result = run_evaluation(
        {"rag": _live_runner},
        args.dataset,
        k=args.k,
    )
    output_path = store_evaluation_result(result, args.output_dir)
    print(json.dumps({"result": str(output_path), "dataset": result["dataset"]}, indent=2))


if __name__ == "__main__":
    main()
