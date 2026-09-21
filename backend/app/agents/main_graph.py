def build_ml_graph():

    graph = StateGraph(
        MLState
    )


    # --------------------------------------------------------
    # NODES
    # --------------------------------------------------------

    graph.add_node(
        "identify_customer",
        identify_customer_node
    )

    graph.add_node(
        "retrieve_customer",
        retrieve_customer_node
    )

    graph.add_node(
        "predict_churn",
        predict_churn_node
    )

    graph.add_node(
        "generate_answer",
        generate_ml_answer_node
    )


    # --------------------------------------------------------
    # EDGES
    # --------------------------------------------------------

    graph.add_edge(
        START,
        "identify_customer"
    )

    graph.add_edge(
        "identify_customer",
        "retrieve_customer"
    )

    graph.add_edge(
        "retrieve_customer",
        "predict_churn"
    )

    graph.add_edge(
        "predict_churn",
        "generate_answer"
    )

    graph.add_edge(
        "generate_answer",
        END
    )


    return graph.compile()


ml_graph = build_ml_graph()