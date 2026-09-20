from typing import TypedDict, List, Any

from langgraph.graph import StateGraph, START, END

from app.rag.query.query_processor import process_query
from app.rag.retrieval.retriever import get_retriever
from app.rag.security.evidence_checker import check_evidence
from app.rag.generation.llm import get_llm
from app.rag.generation.prompt import RAG_PROMPT


# ============================================================
# 1. RAG STATE
# ============================================================

class RAGState(TypedDict, total=False):

    question: str

    search_query: str

    retrieved_documents: List[Any]

    reranked_documents: List[Any]

    evidence_sufficient: bool

    answer: str

    citations: List[dict]

    error: str


# ============================================================
# 2. ANALYZE QUESTION
# ============================================================

def analyze_node(state: RAGState):

    result = process_query(
        state["question"]
    )

    return {
        "search_query": result["search_query"]
    }


# ============================================================
# 3. RETRIEVE DOCUMENTS
# ============================================================

def retrieve_node(state: RAGState):

    retriever = get_retriever()

    documents = retriever.invoke(
        state["search_query"]
    )

    return {
        "retrieved_documents": documents
    }


# ============================================================
# 4. CHECK EVIDENCE
# ============================================================

def evidence_node(state: RAGState):

    result = check_evidence(
        state["retrieved_documents"]
    )

    return {
        "evidence_sufficient": result["sufficient"],
        "error": (
            result["reason"]
            if not result["sufficient"]
            else ""
        )
    }


# ============================================================
# 5. ROUTER
# ============================================================

def evidence_router(state: RAGState):

    if state.get("evidence_sufficient"):
        return "generate"

    return "safe_response"


# ============================================================
# 6. GENERATE ANSWER
# ============================================================

def generate_node(state: RAGState):

    documents = state["retrieved_documents"]

    context = "\n\n".join(
        document.page_content
        for document in documents
    )

    prompt = RAG_PROMPT.format(
        context=context,
        question=state["question"]
    )

    llm = get_llm()

    response = llm.invoke(prompt)

    citations = [
        {
            "document": document.metadata.get("source"),
            "page": (
                document.metadata.get("page", 0) + 1
                if isinstance(
                    document.metadata.get("page"),
                    int
                )
                else document.metadata.get("page_label")
            )
        }
        for document in documents
    ]

    return {
        "answer": response.content,
        "citations": citations
    }


# ============================================================
# 7. SAFE RESPONSE
# ============================================================

def safe_response_node(state: RAGState):

    return {
        "answer": (
            "I couldn't find enough information in the "
            "provided documents to answer this question."
        ),
        "citations": []
    }


# ============================================================
# 8. BUILD LANGGRAPH
# ============================================================

def build_rag_graph():

    graph = StateGraph(RAGState)

    # Nodes
    graph.add_node(
        "analyze",
        analyze_node
    )

    graph.add_node(
        "retrieve",
        retrieve_node
    )

    graph.add_node(
        "evidence_check",
        evidence_node
    )

    graph.add_node(
        "generate",
        generate_node
    )

    graph.add_node(
        "safe_response",
        safe_response_node
    )

    # Start
    graph.add_edge(
        START,
        "analyze"
    )

    # Analyze → Retrieve
    graph.add_edge(
        "analyze",
        "retrieve"
    )

    # Retrieve → Evidence Check
    graph.add_edge(
        "retrieve",
        "evidence_check"
    )

    # Evidence Check → Decision
    graph.add_conditional_edges(
        "evidence_check",
        evidence_router,
        {
            "generate": "generate",
            "safe_response": "safe_response"
        }
    )

    # End
    graph.add_edge(
        "generate",
        END
    )

    graph.add_edge(
        "safe_response",
        END
    )

    return graph.compile()


# ============================================================
# 9. COMPILE GRAPH
# ============================================================

rag_graph = build_rag_graph()