from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.config import QDRANT_URL, QDRANT_COLLECTION_NAME
from app.rag.embeddings.embedding_model import get_embedding_model


def get_retriever():
    embeddings = get_embedding_model()

    client = QdrantClient(
        url=QDRANT_URL
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=QDRANT_COLLECTION_NAME,
        embedding=embeddings,
    )

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 5
        }
    )

    return retriever