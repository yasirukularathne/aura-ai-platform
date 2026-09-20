"""Retrieval accuracy metrics for RAG evaluation."""

from collections.abc import Sequence
from typing import Any


def _unwrap_document(document: Any) -> Any:
    if isinstance(document, dict):
        for key in ("document", "doc"):
            if key in document:
                return document[key]
    return document


def _metadata(document: Any) -> dict[str, Any]:
    document = _unwrap_document(document)
    if isinstance(document, dict):
        metadata = document.get("metadata")
        if isinstance(metadata, dict):
            return metadata
        return document

    metadata = getattr(document, "metadata", {})
    return metadata if isinstance(metadata, dict) else {}


def _normalise_page(page: Any) -> Any:
    if page is None:
        return None
    if isinstance(page, bool):
        return str(page).lower()
    try:
        return int(page)
    except (TypeError, ValueError):
        return str(page).strip().lower()


def _is_expected(document: Any, expected_document: str, expected_page: Any) -> bool:
    metadata = _metadata(document)
    document_name = str(
        metadata.get(
            "source",
            metadata.get(
                "document",
                metadata.get("file_name", metadata.get("file", "")),
            ),
        )
    )

    if expected_document not in document_name:
        return False

    if expected_page is None:
        return True

    return _normalise_page(metadata.get("page")) == _normalise_page(expected_page)


def recall_at_k(
    retrieved_documents: Sequence[Any],
    expected_document: str,
    expected_page: Any,
    k: int = 5,
) -> float:
    """Return 1 when the expected document/page appears in the top ``k``."""
    if k < 1:
        raise ValueError("k must be at least 1")

    top_documents = retrieved_documents[:k]

    for doc in top_documents:
        if _is_expected(doc, expected_document, expected_page):
            return 1.0

    return 0.0


def hit_rate(results: Sequence[float | int | bool]) -> float:
    """Return the proportion of queries that produced a retrieval hit."""
    if not results:
        return 0.0
    return sum(float(result) for result in results) / len(results)


def reciprocal_rank(
    retrieved_documents: Sequence[Any],
    expected_document: str,
    expected_page: Any,
) -> float:
    """Return the reciprocal rank of the first expected document/page."""
    for rank, document in enumerate(retrieved_documents, start=1):
        if _is_expected(document, expected_document, expected_page):
            return 1.0 / rank
    return 0.0


def mean_reciprocal_rank(ranks: Sequence[float]) -> float:
    """Return the mean reciprocal rank across evaluated queries."""
    if not ranks:
        return 0.0
    return sum(ranks) / len(ranks)
