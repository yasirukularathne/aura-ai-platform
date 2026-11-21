from collections.abc import Mapping, Sequence
from typing import Any


def _citation_values(citation: Any) -> tuple[str, Any]:
    if not isinstance(citation, Mapping):
        return "", None
    source = citation.get("source", citation.get("document", citation.get("file", "")))
    return str(source), citation.get("page")


def citation_correct(
    citations: Sequence[Any],
    expected_citation: Mapping[str, Any] | None,
) -> float | None:
    """Return one when an expected source/page citation is present."""
    if expected_citation is None:
        return None
    expected_source = str(expected_citation.get("source", ""))
    expected_page = expected_citation.get("page")
    for citation in citations:
        source, page = _citation_values(citation)
        if expected_source in source and str(page) == str(expected_page):
            return 1.0
    return 0.0
