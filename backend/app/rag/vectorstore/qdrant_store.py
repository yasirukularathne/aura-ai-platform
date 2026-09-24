from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.config import QDRANT_URL, QDRANT_COLLECTION_NAME
from app.rag.embeddings.embedding_model import get_embedding_model


def create_vector_store(chunks):
    embeddings = get_embedding_model()

    client = QdrantClient(url=QDRANT_URL)

    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url=QDRANT_URL,
        collection_name=QDRANT_COLLECTION_NAME,
    )

    return vector_store