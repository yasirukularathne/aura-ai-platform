"""Application security guards for the RAG API."""

from .input_guard import detect_prompt_injection

__all__ = [
    "detect_prompt_injection",
]