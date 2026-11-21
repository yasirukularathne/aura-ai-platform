import app.agents.rag_agent as rag_agent
import pytest
from langchain_core.documents import Document


class FakeStructuredLLM:
    def __init__(self, assessment):
        self.assessment = assessment
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return self.assessment


class FakeLLM:
    def __init__(self, assessment):
        self.structured = FakeStructuredLLM(assessment)

    def with_structured_output(self, schema, **kwargs):
        assert schema is rag_agent.RAGAssessment
        assert kwargs == {
            "method": "json_schema",
            "strict": True,
        }
        return self.structured


def make_state(document):
    return {
        "question": "What is the test marker?",
        "reranked_documents": [
            {"document": document, "score": 2.5}
        ],
    }


def test_supported_question_returns_grounded_answer_and_citation(monkeypatch):
    document = Document(
        page_content="The test marker is AURA_TEST_123.",
        metadata={"source": "test.txt", "page": 1},
    )

    assessment = rag_agent.RAGAssessment(
        evidence_sufficient=True,
        reason="The document explicitly contains the test marker.",
        answer="The test marker is AURA_TEST_123.",
    )

    fake_llm = FakeLLM(assessment)
    monkeypatch.setattr(rag_agent, "get_llm", lambda: fake_llm)

    result = rag_agent.assess_and_generate_node(make_state(document))

    assert result["evidence_sufficient"] is True
    assert result["answer"] == "The test marker is AURA_TEST_123."
    assert result["citations"] == [
        {"document": "test.txt", "page": 1}
    ]
    assert result["error"] is None
    assert "AURA_TEST_123" in fake_llm.structured.prompt


def test_unsupported_question_returns_safe_response_without_citations(
    monkeypatch,
):
    document = Document(
        page_content="The document describes the AURA ingestion test.",
        metadata={"source": "test.txt", "page": 1},
    )

    assessment = rag_agent.RAGAssessment(
        evidence_sufficient=False,
        reason="The document contains no warranty information.",
        answer="Information not available.",
    )

    monkeypatch.setattr(
        rag_agent,
        "get_llm",
        lambda: FakeLLM(assessment),
    )

    result = rag_agent.assess_and_generate_node(make_state(document))

    assert result["evidence_sufficient"] is False
    assert result["answer"] == rag_agent.SAFE_RESPONSE
    assert result["citations"] == []
    assert "warranty" in result["error"].lower()


def test_llm_failure_returns_safe_response_without_citations(monkeypatch):
    def failing_llm():
        raise RuntimeError("Simulated Groq failure")

    monkeypatch.setattr(rag_agent, "get_llm", failing_llm)

    document = Document(
        page_content="Some document content.",
        metadata={"source": "test.txt"},
    )

    result = rag_agent.assess_and_generate_node(make_state(document))

    assert result["evidence_sufficient"] is False
    assert result["answer"] == rag_agent.SAFE_RESPONSE
    assert result["citations"] == []
    assert result["error"] == (
        "Evidence assessment failed; unable to verify an answer."
    )


def test_empty_retrieval_routes_to_safe_response_without_llm(monkeypatch):
    def unexpected_llm_call():
        pytest.fail("LLM should not be called for empty retrieval")

    monkeypatch.setattr(rag_agent, "get_llm", unexpected_llm_call)

    state = {"reranked_documents": []}

    evidence_result = rag_agent.evidence_node(state)

    state.update(evidence_result)

    assert state["retrieval_sufficient"] is False
    assert rag_agent.evidence_router(state) == "safe_response"

    result = rag_agent.safe_response_node(state)

    assert result["evidence_sufficient"] is False
    assert result["answer"] == rag_agent.SAFE_RESPONSE
    assert result["citations"] == []