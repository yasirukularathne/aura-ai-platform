"""Evaluation utilities for the AURA RAG pipeline."""

from .answer_metrics import EVALUATION_PROMPT, evaluate_answer
from .citation_metrics import citation_correct
from .dataset import load_evaluation_dataset
from .history import store_evaluation_result
from .retrieval_metrics import (
    hit_rate,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from .runner import evaluate_configuration

__all__ = [
    "EVALUATION_PROMPT",
    "evaluate_answer",
    "citation_correct",
    "evaluate_configuration",
    "hit_rate",
    "load_evaluation_dataset",
    "mean_reciprocal_rank",
    "precision_at_k",
    "recall_at_k",
    "reciprocal_rank",
    "store_evaluation_result",
]