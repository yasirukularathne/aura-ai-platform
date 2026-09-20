import re


def analyze_query(query: str):

    query = query.strip()

    # Detect exact identifiers, policy IDs, codes, etc.
    has_identifier = bool(
        re.search(r"\b[A-Z]{2,}-\d{2,}\b", query)
    )

    # Very short questions may need rewriting
    needs_rewrite = len(query.split()) < 5

    return {
        "original_query": query,
        "needs_rewrite": needs_rewrite,
        "has_identifier": has_identifier,
    }