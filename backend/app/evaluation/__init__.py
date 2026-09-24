"""Evaluation utilities for the AURA RAG pipeline."""

from .answer_metrics import EVALUATION_PROMPT, evaluate_answer
from .dataset import load_evaluation_dataset
from .retrieval_metrics import (
    hit_rate,
    mean_reciprocal_rank,
    recall_at_k,
    reciprocal_rank,
)
from .runner import evaluate_configuration

__all__ = [
    "EVALUATION_PROMPT",
    "evaluate_answer",
    "evaluate_configuration",
    "hit_rate",
    "load_evaluation_dataset",
    "mean_reciprocal_rank",
    "recall_at_k",
    "reciprocal_rank",
]