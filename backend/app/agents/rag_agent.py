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

    security_blocked: bool

    retrieved_documents: list
    reranked_documents: list

    evidence_sufficient: bool
    evidence_score: float

    answer: str
    citations: list

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
# 3. HYBRID RETRIEVE NODE
# ============================================================

def hybrid_retrieve_node(state):

    # Temporary development implementation.
    # Later this will use a persistent document index.

    from app.rag.retrieval.retriever import get_retriever

    retriever = get_retriever()

    documents = retriever.invoke(
        state["search_query"]
    )

    return {
        "retrieved_documents": documents
    }
# ============================================================
# 4. RERANK DOCUMENTS
# ============================================================
def rerank_node(state):

    from app.rag.reranking.reranker import Reranker

    reranker = Reranker()

    results = reranker.rerank(
        query=state["search_query"],
        documents=state["retrieved_documents"],
        top_k=5
    )

    return {
        "reranked_documents": results
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


def evidence_node(state):

    from app.rag.security.evidence_checker import (
        check_reranked_evidence
    )

    result = check_reranked_evidence(
        state["reranked_documents"]
    )

    return {
        "evidence_sufficient": result["sufficient"],
        "evidence_score": result["score"],
        "error": result["reason"]
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

def generate_node(state):

    from app.rag.generation.llm import get_llm
    from app.rag.generation.prompt import RAG_PROMPT

    documents = [
        item["document"]
        for item in state["reranked_documents"]
    ]

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
            "page": document.metadata.get("page"),
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
# 7. Security node
# ============================================================

def security_node(state):

    from app.security.input_guard import detect_prompt_injection

    result = detect_prompt_injection(
        state["question"]
    )

    if result["blocked"]:

        return {
            "security_blocked": True,
            "error": "Potential prompt injection detected."
        }

    return {
        "security_blocked": False
    }

# ============================================================
# 7. Security router
# ============================================================

def security_router(state):

    if state.get("security_blocked"):
        return "blocked"

    return "continue"

# ============================================================
# 8. BUILD LANGGRAPH
# ============================================================

def build_rag_graph():

    graph = StateGraph(RAGState)

    graph.add_node(
        "analyze",
        analyze_node
    )

    graph.add_node(
        "retrieve",
        hybrid_retrieve_node
    )

    graph.add_node(
        "rerank",
        rerank_node
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

    graph.add_edge(
        START,
        "analyze"
    )

    graph.add_edge(
        "analyze",
        "retrieve"
    )

    graph.add_edge(
        "retrieve",
        "rerank"
    )

    graph.add_edge(
        "rerank",
        "evidence_check"
    )

    graph.add_conditional_edges(
        "evidence_check",
        evidence_router,
        {
            "generate": "generate",
            "safe_response": "safe_response"
        }
    )

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