"""Answer relevance and faithfulness metrics for RAG evaluation."""

import json
import re
from typing import Any


EVALUATION_PROMPT = """
Evaluate the following RAG answer.

Question:
{question}

Retrieved Context:
{context}

Generated Answer:
{answer}

Return JSON:

{{
	"faithfulness": 0.0,
	"answer_relevance": 0.0,
	"reason": "..."
}}

Scores must be between 0 and 1.
"""


def _tokens(text: str) -> set[str]:
	return set(re.findall(r"[a-z0-9]+", text.lower()))


def lexical_answer_metrics(
	question: str,
	context: str,
	answer: str,
) -> dict[str, float]:
	"""Provide a deterministic baseline when an LLM judge is unavailable."""
	question_tokens = _tokens(question)
	context_tokens = _tokens(context)
	answer_tokens = _tokens(answer)
	relevance = (
		len(question_tokens & answer_tokens) / len(question_tokens)
		if question_tokens
		else 0.0
	)
	faithfulness = (
		len(answer_tokens & context_tokens) / len(answer_tokens)
		if answer_tokens
		else 0.0
	)
	return {
		"faithfulness": faithfulness,
		"answer_relevance": relevance,
	}


def evaluate_answer(
	question: str,
	context: str,
	answer: str,
	llm: Any | None = None,
) -> dict[str, Any]:
	"""Evaluate faithfulness and relevance with an optional LLM judge.

	The deterministic lexical score is used when no judge is supplied.
	"""
	if llm is None:
		result = lexical_answer_metrics(question, context, answer)
		result["reason"] = "Deterministic lexical baseline."
		return result

	response = llm.invoke(
		EVALUATION_PROMPT.format(
			question=question,
			context=context,
			answer=answer,
		)
	)
	try:
		result = json.loads(response.content)
	except (AttributeError, json.JSONDecodeError) as error:
		raise ValueError("LLM evaluator must return valid JSON") from error

	for key in ("faithfulness", "answer_relevance"):
		score = float(result.get(key, 0.0))
		if not 0.0 <= score <= 1.0:
			raise ValueError(f"{key} must be between 0 and 1")
		result[key] = score
	return result
