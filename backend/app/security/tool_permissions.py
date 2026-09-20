ALLOWED_TOOLS = {
    "rag_search",
    "churn_prediction",
    "analytics"
}


def is_tool_allowed(tool_name: str):

    return tool_name in ALLOWED_TOOLS