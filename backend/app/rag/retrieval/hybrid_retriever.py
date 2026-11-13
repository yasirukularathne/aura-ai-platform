
from langchain_core.documents import Document

from app.rag.retrieval.bm25_retriever import BM25Retriever
from app.rag.retrieval.retriever import (
    _normalize_scope_id,
    _scope_filter,
    get_retriever,
    load_indexed_documents,
)


class HybridRetriever:
    """Tenant-scoped hybrid retrieval using dense and BM25 search."""

    def __init__(
        self,
        documents: list[Document] | None = None,
        tenant_id: str | None = None,
        workspace_id: str | None = None,
    ):
        # Require a valid tenant before initializing retrieval.
        _scope_filter(tenant_id, workspace_id)

        self.tenant_id = _normalize_scope_id(
            tenant_id,
            "tenant_id",
            required=True,
        )

        self.workspace_id = _normalize_scope_id(
            workspace_id,
            "workspace_id",
        )

        self.vector_retriever = get_retriever(
            tenant_id=self.tenant_id,
            workspace_id=self.workspace_id,
        )

        source_documents = (
            documents
            if documents is not None
            else load_indexed_documents(
                tenant_id=self.tenant_id,
                workspace_id=self.workspace_id,
            )
        )

        # Explicitly supplied BM25 documents must obey the same scope.
        scoped_documents = [
            document
            for document in source_documents
            if self._is_document_in_scope(document)
        ]

        self.bm25_retriever = BM25Retriever(scoped_documents)

    def _is_document_in_scope(self, document: Document) -> bool:
        """Check whether a document belongs to the active tenant/workspace."""

        metadata = document.metadata or {}

        if metadata.get("aura_tenant_id") != self.tenant_id:
            return False

        if self.workspace_id is not None:
            if metadata.get("aura_workspace_id") != self.workspace_id:
                return False

        return True

    @staticmethod
    def _document_key(document: Document) -> tuple:
        """Create a stable key for merging dense and sparse results."""

        return (
            document.metadata.get("aura_job_id"),
            document.metadata.get("source"),
            document.metadata.get("page"),
            document.page_content,
        )

    def retrieve(self, query: str, k: int = 5) -> list[Document]:
        """Retrieve scoped documents using Reciprocal Rank Fusion."""

        if k <= 0:
            return []

        dense_results = self.vector_retriever.invoke(query)

        # Defense in depth: validate dense results before merging.
        dense_results = [
            document
            for document in dense_results
            if self._is_document_in_scope(document)
        ]

        sparse_results = self.bm25_retriever.retrieve(
            query,
            k=max(k * 2, 10),
        )

        scores: dict[tuple, float] = {}
        documents_by_key: dict[tuple, Document] = {}

        for ranked_results in (dense_results, sparse_results):
            for rank, document in enumerate(ranked_results, start=1):
                key = self._document_key(document)

                documents_by_key[key] = document
                scores[key] = (
                    scores.get(key, 0.0) + 1 / (60 + rank)
                )

        ranked_keys = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )

        return [
            documents_by_key[key]
            for key in ranked_keys[:k]
        ]
