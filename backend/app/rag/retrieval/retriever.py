from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.rag.embeddings.embedding_model import get_embedding_model
from app.rag.vectorstore.qdrant_store import COLLECTION_NAME


def get_retriever():

    embeddings = get_embedding_model()

    client = QdrantClient(
        url="http://localhost:6333"
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 5
        }
    )

    return retriever