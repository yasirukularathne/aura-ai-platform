"""Utilities for splitting loaded documents into retrieval chunks."""

from collections.abc import Sequence

from langchain_core.documents import Document


def split_documents(
    documents: Sequence[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> list[Document]:
    """Split documents into overlapping chunks for embedding and retrieval."""
    if chunk_size <= chunk_overlap:
        raise ValueError("chunk_size must be greater than chunk_overlap")
    chunks: list[Document] = []
    step = chunk_size - chunk_overlap
    for document in documents:
        text = document.page_content
        for start in range(0, len(text), step):
            content = text[start : start + chunk_size]
            if content.strip():
                chunks.append(
                    Document(page_content=content, metadata=dict(document.metadata))
                )
            if start + chunk_size >= len(text):
                break
    return chunks
