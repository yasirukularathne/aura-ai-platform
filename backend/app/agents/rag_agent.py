import logging
from typing import TypedDict

from app.rag.generation.llm import get_llm
from app.rag.generation.prompt import RAG_PROMPT
from app.rag.query.query_processor import process_query
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

SAFE_RESPONSE = (
    "I couldn't find enough information in the "
    "provided documents to answer this question."
)


class RAGAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_sufficient: bool = Field(
        description=(
            "True only when the provided context contains enough "
            "explicit information to answer the question."
        )
    )
    reason: str = Field(
        description="Brief explanation of the evidence assessment."
    )
    answer: str = Field(
        description=(
            "A concise answer based exclusively on the provided context. "
            "If evidence is insufficient, return an abstention."
        )
    )


class RAGState(TypedDict, total=False):
    question: str
    search_query: str
    tenant_id: str
    workspace_id: str | None
    security_blocked: bool
    retrieved_documents: list
    reranked_documents: list
    retrieval_sufficient: bool
    evidence_sufficient: bool
    evidence_score: float
    evidence_reason: str
    answer: str
    citations: list
    error: str | None


def analyze_node(state: RAGState):
    result = process_query(state["question"])
    return {"search_query": result["search_query"]}


def hybrid_retrieve_node(state: RAGState):
    from app.rag.retrieval.hybrid_retriever import HybridRetriever

    retriever = HybridRetriever(
        tenant_id=state.get("tenant_id"),
        workspace_id=state.get("workspace_id"),
    )

    return {
        "retrieved_documents": retriever.retrieve(
            state["search_query"],
            k=5,
        )
    }


def rerank_node(state: RAGState):
    from app.rag.reranking.reranker import Reranker

    reranker = Reranker()

    results = reranker.rerank(
        query=state["search_query"],
        documents=state["retrieved_documents"],
        top_k=5,
    )

    return {"reranked_documents": results}


def evidence_node(state: RAGState):
    from app.rag.security.evidence_checker import check_reranked_evidence

    result = check_reranked_evidence(
        state.get("reranked_documents", [])
    )

    return {
        "retrieval_sufficient": result["sufficient"],
        "evidence_score": result["score"],
        "evidence_reason": result["reason"],
        "error": None if result["sufficient"] else result["reason"],
    }


def evidence_router(state: RAGState):
    if state.get("retrieval_sufficient"):
        return "assess"

    return "safe_response"


def assess_and_generate_node(state: RAGState):
    documents = [
        item["document"]
        for item in state.get("reranked_documents", [])
    ]

    context = "\n\n".join(
        document.page_content
        for document in documents
        if document.page_content.strip()
    )

    try:
        prompt = RAG_PROMPT.format(
            context=context,
            question=state["question"],
        )

        structured_llm = get_llm().with_structured_output(
            RAGAssessment,
            method="json_schema",
            strict=True,
        )

        assessment = structured_llm.invoke(prompt)

        if (
            not assessment.evidence_sufficient
            or not assessment.answer.strip()
        ):
            reason = assessment.reason or (
                "The provided documents do not contain enough "
                "information to answer this question."
            )

            return {
                "evidence_sufficient": False,
                "evidence_reason": reason,
                "answer": SAFE_RESPONSE,
                "citations": [],
                "error": reason,
            }

        citations = [
            {
                "document": document.metadata.get("source"),
                "page": document.metadata.get("page"),
            }
            for document in documents
        ]

        return {
            "evidence_sufficient": True,
            "evidence_reason": assessment.reason,
            "answer": assessment.answer,
            "citations": citations,
            "error": None,
        }

    except Exception:
        logger.exception("RAG evidence assessment or generation failed")

        return {
            "evidence_sufficient": False,
            "evidence_reason": (
                "Evidence assessment failed. The answer could not "
                "be verified."
            ),
            "answer": SAFE_RESPONSE,
            "citations": [],
            "error": "Evidence assessment failed; unable to verify an answer.",
        }


def safe_response_node(_state: RAGState):
    return {
        "evidence_sufficient": False,
        "answer": SAFE_RESPONSE,
        "citations": [],
    }


def security_node(state: RAGState):
    from app.security.input_guard import detect_prompt_injection

    result = detect_prompt_injection(state["question"])

    if result["blocked"]:
        return {
            "security_blocked": True,
            "error": "Potential prompt injection detected.",
        }

    return {"security_blocked": False}


def security_router(state: RAGState):
    if state.get("security_blocked"):
        return "blocked"

    return "continue"


def build_rag_graph():
    graph = StateGraph(RAGState)

    graph.add_node("security", security_node)
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", hybrid_retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("evidence_check", evidence_node)
    graph.add_node("assess_and_generate", assess_and_generate_node)
    graph.add_node("safe_response", safe_response_node)

    graph.add_edge(START, "security")

    graph.add_conditional_edges(
        "security",
        security_router,
        {
            "continue": "analyze",
            "blocked": "safe_response",
        },
    )

    graph.add_edge("analyze", "retrieve")
    graph.add_edge("retrieve", "rerank")
    graph.add_edge("rerank", "evidence_check")

    graph.add_conditional_edges(
        "evidence_check",
        evidence_router,
        {
            "assess": "assess_and_generate",
            "safe_response": "safe_response",
        },
    )

    graph.add_edge("assess_and_generate", END)
    graph.add_edge("safe_response", END)

    return graph.compile()


rag_graph = build_rag_graph()
