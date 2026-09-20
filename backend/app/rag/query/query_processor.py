from app.rag.query.analyzer import analyze_query
from app.rag.query.rewriter import rewrite_query


def process_query(query: str):

    analysis = analyze_query(query)

    if analysis["needs_rewrite"] and not analysis["has_identifier"]:
        search_query = rewrite_query(query)
    else:
        search_query = query

    return {
        "original_query": query,
        "search_query": search_query,
        "analysis": analysis
    }