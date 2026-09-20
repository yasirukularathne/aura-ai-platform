from pathlib import Path
from types import SimpleNamespace

import pytest

from app.evaluation import evaluate_configuration, recall_at_k, reciprocal_rank
from app.evaluation.dataset import load_evaluation_dataset


DATASET_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "evaluation" / "rag_eval.json"
)


def _document(source="company_policy.pdf", page=3, text="Company policy text"):
    return SimpleNamespace(
        metadata={"source": source, "page": page},
        page_content=text,
    )


def test_load_evaluation_dataset_validates_current_dataset():
    data = load_evaluation_dataset(DATASET_PATH)

    assert data["dataset"] == "aura-company-policy-rag-evaluation"
    assert len(data["cases"]) == 50
    assert all(case["question"] for case in data["cases"])


def test_missing_dataset_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_evaluation_dataset(DATASET_PATH.with_name("missing.json"))


def test_retrieval_metrics_support_reranked_documents():
    reranked_document = {
        "document": _document(page="7"),
        "score": 0.91,
    }

    assert recall_at_k([reranked_document], "company_policy.pdf", 7, k=1) == 1.0
    assert reciprocal_rank([reranked_document], "company_policy.pdf", 7) == 1.0


def test_evaluate_configuration_scores_current_dataset_shape():
    case = {
        "id": "hiv-001",
        "category": "grounded",
        "question": "Is HIV testing required before employment?",
        "expected_behavior": "answer_with_evidence",
        "reference_answer": (
            "No. HIV testing is not a prerequisite for employment, and "
            "the company does not conduct pre-employment testing."
        ),
        "required_terms": [
            "not a prerequisite",
            "employment",
            "pre-employment testing",
        ],
        "must_have_sources": True,
        "expected_document": "company_policy.pdf",
        "expected_page": 3,
    }

    def runner(question):
        return {
            "answer": case["reference_answer"],
            "documents": [
                _document(
                    page=3,
                    text=case["reference_answer"],
                )
            ],
            "sources": [{"source": "company_policy.pdf", "page": 3}],
        }

    result = evaluate_configuration("fake", [case], runner, k=1)
    row = result["results"][0]

    assert result["recall_at_1"] == 1.0
    assert result["mrr"] == 1.0
    assert result["required_term_coverage"] == 1.0
    assert result["source_expectation_accuracy"] == 1.0
    assert row["faithfulness"] == 1.0


def test_evaluate_configuration_marks_unavailable_retrieval_ground_truth():
    data = load_evaluation_dataset(DATASET_PATH)
    case = data["cases"][0]

    def runner(question):
        return {
            "answer": case["reference_answer"],
            "context": case["reference_answer"],
            "sources": [{"source": "company_policy.pdf", "page": 1}],
        }

    result = evaluate_configuration("fake", [case], runner)

    assert result["retrieval_evaluated_cases"] == 0
    assert result["hit_rate"] is None
    assert result["mrr"] is None
    assert result["results"][0]["recall_at_k"] is None


def test_evaluate_configuration_scores_safe_fallbacks():
    case = {
        "id": "unsupported-001",
        "category": "unsupported",
        "question": "What is the company's policy for Mars colonization?",
        "expected_behavior": "safe_fallback",
        "must_have_sources": False,
        "expected_evidence_sufficient": False,
    }

    def runner(question):
        return {
            "answer": (
                "I couldn't find enough information in the provided "
                "documents to answer this question."
            ),
            "citations": [],
            "evidence_sufficient": False,
        }

    result = evaluate_configuration("fake", [case], runner)

    assert result["safe_fallback_accuracy"] == 1.0
    assert result["source_expectation_accuracy"] == 1.0
    assert result["evidence_sufficiency_accuracy"] == 1.0
