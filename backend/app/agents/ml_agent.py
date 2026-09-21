from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from app.ml.tools import churn_prediction_tool


# ============================================================
# 1. ML STATE
# ============================================================

class MLState(TypedDict, total=False):

    customer_id: str

    customer_data: dict

    churn_prediction: int

    churn_probability: float

    error: str


# ============================================================
# 2. CHURN PREDICTION NODE
# ============================================================

def churn_prediction_node(state: MLState):

    customer_id = state["customer_id"]

    result = churn_prediction_tool(
        customer_id
    )

    # --------------------------------------------------------
    # Handle error
    # --------------------------------------------------------

    if "error" in result:

        return {
            "error": result["error"]
        }

    # --------------------------------------------------------
    # Return prediction
    # --------------------------------------------------------

    return {
        "customer_id": result["customer_id"],

        "customer_data": result["customer"],

        "churn_prediction":
            result["churn_prediction"],

        "churn_probability":
            result["churn_probability"]
    }


# ============================================================
# 3. BUILD ML LANGGRAPH
# ============================================================

def build_ml_graph():

    graph = StateGraph(
        MLState
    )

    # --------------------------------------------------------
    # Add node
    # --------------------------------------------------------

    graph.add_node(
        "churn_prediction",
        churn_prediction_node
    )

    # --------------------------------------------------------
    # Flow
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "churn_prediction"
    )

    graph.add_edge(
        "churn_prediction",
        END
    )

    # --------------------------------------------------------
    # Compile
    # --------------------------------------------------------

    return graph.compile()


# ============================================================
# 4. COMPILE GRAPH
# ============================================================

ml_graph = build_ml_graph()