from app.agents.rag_agent import rag_graph
from app.agents.ml_agent import ml_graph


# ============================================================
# ROUTER
# ============================================================

def route_request(
    request_type: str,
    question: str | None = None,
    customer_id: str | None = None,
):
    """
    Route a request to the appropriate existing agent.

    request_type:
        - "rag"
        - "ml"
    """

    # ========================================================
    # RAG AGENT
    # ========================================================

    if request_type == "rag":

        if not question:
            return {
                "error": "A question is required for the RAG agent."
            }

        result = rag_graph.invoke(
            {
                "question": question
            }
        )

        return {
            "agent": "rag",
            "result": result
        }

    # ========================================================
    # ML AGENT
    # ========================================================

    if request_type == "ml":

        if not customer_id:
            return {
                "error": "A customer_id is required for the ML agent."
            }

        result = ml_graph.invoke(
            {
                "customer_id": customer_id
            }
        )

        return {
            "agent": "ml",
            "result": result
        }

    # ========================================================
    # UNKNOWN REQUEST
    # ========================================================

    return {
        "error": (
            f"Unknown request type: '{request_type}'. "
            "Expected 'rag' or 'ml'."
        )
    }