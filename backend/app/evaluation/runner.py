"""Evaluation runner for comparing RAG configurations and latency."""

import csv
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from .answer_metrics import evaluate_answer
from .dataset import load_evaluation_dataset
from .retrieval_metrics import (
	hit_rate,
	mean_reciprocal_rank,
	recall_at_k,
	reciprocal_rank,
)


RAGConfiguration = Callable[[str], dict[str, Any]]


def _average(values: Sequence[float | int | bool | None]) -> float | None:
	values = [float(value) for value in values if value is not None]
	if not values:
		return None
	return sum(values) / len(values)


def _as_list(value: Any) -> list[Any]:
	if value is None:
		return []
	if isinstance(value, (str, bytes)):
		return [value]
	if isinstance(value, Mapping):
		return [value]
	if isinstance(value, Sequence):
		return list(value)
	return [value]


def _unwrap_document(document: Any) -> Any:
	if isinstance(document, Mapping):
		for key in ("document", "doc"):
			if key in document:
				return document[key]
	return document


def _documents_from_result(result: Mapping[str, Any]) -> list[Any]:
	for key in ("documents", "reranked_documents", "retrieved_documents"):
		documents = _as_list(result.get(key))
		if documents:
			return documents
	return []


def _document_text(document: Any) -> str:
	document = _unwrap_document(document)

	if isinstance(document, Mapping):
		for key in ("page_content", "content", "text"):
			if document.get(key):
				return str(document[key])
		return ""

	for attribute in ("page_content", "content", "text"):
		value = getattr(document, attribute, "")
		if value:
			return str(value)

	return ""


def _context_from_result(
	result: Mapping[str, Any],
	documents: Sequence[Any],
) -> str:
	context = result.get("context")
	if context:
		return str(context)

	return "\n\n".join(
		text
		for text in (_document_text(document) for document in documents)
		if text
	)


def _normalise_text(text: Any) -> str:
	return " ".join(str(text).lower().split())


def _contains_phrase(text: str, phrase: str) -> bool:
	return _normalise_text(phrase) in text


def _source_items(result: Mapping[str, Any]) -> list[Any]:
	for key in ("sources", "citations"):
		sources = _as_list(result.get(key))
		if sources:
			return sources
	return []


def _expected_case_metrics(
	case: Mapping[str, Any],
	result: Mapping[str, Any],
	answer: str,
) -> dict[str, Any]:
	metrics: dict[str, Any] = {}
	normalised_answer = _normalise_text(answer)

	required_terms = _as_list(case.get("required_terms"))
	if required_terms:
		matched_terms = [
			term
			for term in required_terms
			if _contains_phrase(normalised_answer, str(term))
		]
		metrics["required_term_coverage"] = len(matched_terms) / len(required_terms)
		metrics["matched_required_terms"] = matched_terms
		metrics["missing_required_terms"] = [
			term for term in required_terms if term not in matched_terms
		]

	if "must_have_sources" in case:
		has_sources = bool(_source_items(result))
		metrics["has_sources"] = has_sources
		metrics["source_expectation_met"] = (
			has_sources == bool(case["must_have_sources"])
		)

	expected_topics = _as_list(case.get("expected_search_query_topics"))
	if expected_topics:
		search_query = str(
			result.get("search_query")
			or result.get("rewritten_query")
			or result.get("query")
			or ""
		)
		topic_text = _normalise_text(f"{search_query} {answer}")
		matched_topics = [
			topic
			for topic in expected_topics
			if _contains_phrase(topic_text, str(topic))
		]
		metrics["search_query_topic_coverage"] = (
			len(matched_topics) / len(expected_topics)
		)
		metrics["matched_search_query_topics"] = matched_topics
		metrics["missing_search_query_topics"] = [
			topic for topic in expected_topics if topic not in matched_topics
		]

	if "expected_evidence_sufficient" in case and "evidence_sufficient" in result:
		metrics["evidence_sufficiency_met"] = (
			bool(result["evidence_sufficient"])
			== bool(case["expected_evidence_sufficient"])
		)

	if (
		case.get("expected_behavior") == "safe_fallback"
		or case.get("expected_evidence_sufficient") is False
	):
		fallback_patterns = (
			r"\bcouldn'?t find enough information\b",
			r"\bcould not find enough information\b",
			r"\bnot enough information\b",
			r"\bprovided documents\b",
			r"\bdon'?t have enough information\b",
			r"\bdo not have enough information\b",
			r"\bcannot answer\b",
			r"\bi don'?t know\b",
			r"\bi do not know\b",
		)
		metrics["safe_fallback_met"] = any(
			re.search(pattern, normalised_answer)
			for pattern in fallback_patterns
		)

	return metrics


def _fieldnames(rows: Sequence[Mapping[str, Any]]) -> list[str]:
	fieldnames: list[str] = []
	for row in rows:
		for key in row:
			if key not in fieldnames:
				fieldnames.append(key)
	return fieldnames


def evaluate_configuration(
	name: str,
	cases: Sequence[dict[str, Any]],
	run_query: RAGConfiguration,
	k: int = 5,
) -> dict[str, Any]:
	"""Evaluate one vector, hybrid, reranked, or full RAG configuration."""
	results = []
	hits = []
	ranks = []

	for case in cases:
		started = time.perf_counter()
		result = run_query(case["question"])
		total_latency_ms = (time.perf_counter() - started) * 1000
		documents = _documents_from_result(result)
		expected_document = case.get("expected_document")
		expected_page = case.get("expected_page")

		if expected_document is not None:
			recall = recall_at_k(documents, expected_document, expected_page, k)
			rank = reciprocal_rank(documents, expected_document, expected_page)
			hits.append(recall)
			ranks.append(rank)
		else:
			recall = None
			rank = None

		answer = str(result.get("answer", ""))
		context = _context_from_result(result, documents)
		answer_scores = evaluate_answer(
			case["question"],
			context,
			answer,
		)
		case_scores = _expected_case_metrics(case, result, answer)
		recall_key = f"recall_at_{k}"
		results.append(
			{
				"id": case.get("id"),
				"category": case.get("category"),
				"question": case["question"],
				"retrieval_method": name,
				"recall_at_k": recall,
				recall_key: recall,
				"reciprocal_rank": rank,
				"retrieval_latency_ms": result.get("retrieval_latency_ms"),
				"reranking_latency_ms": result.get("reranking_latency_ms"),
				"llm_latency_ms": result.get("llm_latency_ms"),
				"total_latency_ms": round(total_latency_ms, 3),
				**answer_scores,
				**case_scores,
			}
		)

	recall_key = f"recall_at_{k}"
	hit_rate_score = hit_rate(hits) if hits else None
	return {
		"retrieval_method": name,
		"evaluated_cases": len(results),
		"retrieval_evaluated_cases": len(hits),
		"recall_at_k": hit_rate_score,
		recall_key: hit_rate_score,
		"hit_rate": hit_rate_score,
		"mrr": mean_reciprocal_rank(ranks) if ranks else None,
		"faithfulness": _average(
			[result.get("faithfulness") for result in results]
		),
		"answer_relevance": _average(
			[result.get("answer_relevance") for result in results]
		),
		"required_term_coverage": _average(
			[result.get("required_term_coverage") for result in results]
		),
		"source_expectation_accuracy": _average(
			[result.get("source_expectation_met") for result in results]
		),
		"search_query_topic_coverage": _average(
			[result.get("search_query_topic_coverage") for result in results]
		),
		"evidence_sufficiency_accuracy": _average(
			[result.get("evidence_sufficiency_met") for result in results]
		),
		"safe_fallback_accuracy": _average(
			[result.get("safe_fallback_met") for result in results]
		),
		"results": results,
	}


def run_evaluation(
	configurations: dict[str, RAGConfiguration],
	dataset_path: str | Path,
	output_json: str | Path | None = None,
	output_csv: str | Path | None = None,
	k: int = 5,
) -> dict[str, Any]:
	"""Run all supplied configurations and optionally write JSON/CSV results."""
	dataset = load_evaluation_dataset(dataset_path)
	evaluation = {
		"dataset": dataset.get("dataset"),
		"configurations": [
			evaluate_configuration(name, dataset["cases"], runner, k)
			for name, runner in configurations.items()
		],
	}

	if output_json:
		Path(output_json).write_text(
			json.dumps(evaluation, indent=2),
			encoding="utf-8",
		)
	if output_csv:
		rows = [
			row
			for configuration in evaluation["configurations"]
			for row in configuration["results"]
		]
		if rows:
			with Path(output_csv).open("w", newline="", encoding="utf-8") as file:
				writer = csv.DictWriter(file, fieldnames=_fieldnames(rows))
				writer.writeheader()
				writer.writerows(rows)

	return evaluation
