
from app.config import QDRANT_API_KEY, QDRANT_COLLECTION_NAME, QDRANT_URL
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue


def _normalize_scope_id(
    value: str | None,
    field_name: str,
    required: bool = False,
) -> str | None:
    """Normalize a tenant/workspace identifier and validate required scope."""
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required for scoped retrieval.")
        return None

    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string.")

    normalized = value.strip()

    if not normalized:
        if required:
            raise ValueError(f"{field_name} is required for scoped retrieval.")
        return None

    return normalized


def _scope_filter(
    tenant_id: str | None = None,
    workspace_id: str | None = None,
) -> Filter:
    """
    Build a mandatory tenant-scoped Qdrant filter.

    Tenant isolation is always enforced. Workspace isolation is additionally
    enforced when a workspace ID is supplied.
    """
    normalized_tenant_id = _normalize_scope_id(
        tenant_id,
        "tenant_id",
        required=True,
    )

    normalized_workspace_id = _normalize_scope_id(
        workspace_id,
        "workspace_id",
    )

    conditions = [
        FieldCondition(
            key="metadata.aura_tenant_id",
            match=MatchValue(value=normalized_tenant_id),
        )
    ]

    if normalized_workspace_id is not None:
        conditions.append(
            FieldCondition(
                key="metadata.aura_workspace_id",
                match=MatchValue(value=normalized_workspace_id),
            )
        )

    return Filter(must=conditions)


def get_retriever(
    tenant_id: str | None = None,
    workspace_id: str | None = None,
):
    """Create a Qdrant retriever restricted to the requested tenant/workspace."""
    from app.rag.embeddings.embedding_model import get_embedding_model
    from app.rag.vectorstore.qdrant_store import ensure_collection

    # Validate scope before connecting to Qdrant.
    scope_filter = _scope_filter(tenant_id, workspace_id)

    embeddings = get_embedding_model()

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    ensure_collection(embeddings, client)

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=embeddings,
    )

    search_kwargs: dict[str, object] = {
        "k": 10,
        "filter": scope_filter,
    }

    retriever = vector_store.as_retriever(
        search_kwargs=search_kwargs
    )

    return retriever


def load_indexed_documents(
    tenant_id: str | None = None,
    workspace_id: str | None = None,
) -> list[Document]:
    """Load Qdrant payloads restricted to the requested tenant/workspace."""

    # Never perform an unscoped scroll.
    scope_filter = _scope_filter(tenant_id, workspace_id)

    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
    )

    # Return an empty result if the collection has not been created.
    if not client.collection_exists(QDRANT_COLLECTION_NAME):
        return []

    records, _ = client.scroll(
        collection_name=QDRANT_COLLECTION_NAME,
        scroll_filter=scope_filter,
        limit=10_000,
        with_payload=True,
        with_vectors=False,
    )

    documents = []

    for record in records:
        payload = record.payload or {}
        metadata = payload.get("metadata", {})
        page_content = payload.get("page_content")

        if isinstance(page_content, str) and page_content.strip():
            documents.append(
                Document(
                    page_content=page_content,
                    metadata=metadata,
                )
            )

    return documents
