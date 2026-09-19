from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.rag.embeddings.embedding_model import get_embedding_model


COLLECTION_NAME = "aura_documents"


def create_vector_store(chunks):

    embeddings = get_embedding_model()

    client = QdrantClient(
        url="http://localhost:6333"
    )

    vector_store = QdrantVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        url="http://localhost:6333",
        collection_name=COLLECTION_NAME,
    )

    return vector_store