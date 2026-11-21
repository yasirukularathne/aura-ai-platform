
from app.config import QDRANT_API_KEY, QDRANT_COLLECTION_NAME, QDRANT_URL
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import FieldCondition, Filter, MatchValue


def _client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def _collection_dimension(info: models.CollectionInfo) -> int:
    vectors = info.config.params.vectors
    if isinstance(vectors, models.VectorParams):
        return vectors.size
    if isinstance(vectors, dict) and "" in vectors:
        return vectors[""].size
    raise RuntimeError(
        "Qdrant collection must use one unnamed dense vector configuration"
    )


def ensure_collection(
    embeddings,
    client: QdrantClient | None = None,
) -> None:
    """Create the configured collection and indexes without replacing data."""
    client = client or _client()
    dimension = len(embeddings.embed_query("AURA collection dimension check"))

    try:
        info = client.get_collection(QDRANT_COLLECTION_NAME)
    except UnexpectedResponse as exc:
        if exc.status_code != 404:
            raise RuntimeError("Could not inspect the Qdrant collection") from exc

        client.create_collection(
            collection_name=QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=dimension,
                distance=models.Distance.COSINE,
            ),
        )
        info = client.get_collection(QDRANT_COLLECTION_NAME)

    existing_dimension = _collection_dimension(info)

    if existing_dimension != dimension:
        raise RuntimeError(
            "Qdrant collection dimension does not match the embedding model"
        )

    payload_schema = info.payload_schema or {}

    for field_name in (
        "metadata.aura_tenant_id",
        "metadata.aura_workspace_id",
        "metadata.aura_job_id",
        "metadata.aura_document_id",
    ):
        if field_name not in payload_schema:
            client.create_payload_index(
                collection_name=QDRANT_COLLECTION_NAME,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )


def create_vector_store(chunks):
    from app.rag.embeddings.embedding_model import get_embedding_model

    embeddings = get_embedding_model()
    client = _client()

    ensure_collection(embeddings, client)

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=embeddings,
    )

    vector_store.add_documents(chunks)

    return vector_store


def delete_document_vectors(
    job_id: str,
    tenant_id: str,
    source_path: str,
) -> None:
    """Delete vectors owned by one tenant-scoped ingestion job."""
    client = _client()

    try:
        # Do nothing if the collection does not exist yet.
        if not client.collection_exists(QDRANT_COLLECTION_NAME):
            return

        tenant_filter = FieldCondition(
            key="metadata.aura_tenant_id",
            match=MatchValue(value=tenant_id),
        )

        job_filter = Filter(
            must=[
                tenant_filter,
                FieldCondition(
                    key="metadata.aura_job_id",
                    match=MatchValue(value=job_id),
                ),
            ]
        )

        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=job_filter,
            wait=True,
        )

        # Delete legacy vectors by source, scoped to the same tenant.
        source_filter = Filter(
            must=[
                tenant_filter,
                FieldCondition(
                    key="metadata.source",
                    match=MatchValue(value=source_path),
                ),
            ]
        )

        client.delete(
            collection_name=QDRANT_COLLECTION_NAME,
            points_selector=source_filter,
            wait=True,
        )

    except UnexpectedResponse as exc:
        if exc.status_code == 404:
            # The collection may have disappeared after the existence check.
            return

        raise RuntimeError(
            "Could not remove document vectors"
        ) from exc

    except Exception as exc:
        raise RuntimeError(
            "Could not remove document vectors"
        ) from exc
