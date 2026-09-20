from app.rag.retrieval.retriever import get_retriever
from app.rag.retrieval.bm25_retriever import BM25Retriever


class HybridRetriever:

    def __init__(self, documents):

        self.vector_retriever = get_retriever()

        self.bm25_retriever = BM25Retriever(
            documents
        )

    def retrieve(self, query: str, k: int = 5):

        vector_results = self.vector_retriever.invoke(query)

        keyword_results = self.bm25_retriever.retrieve(
            query,
            k=k
        )

        combined = []

        seen = set()

        for document in vector_results + keyword_results:

            document_id = (
                document.metadata.get("source"),
                document.metadata.get("page"),
                document.page_content
            )

            if document_id not in seen:

                combined.append(document)

                seen.add(document_id)

        return combined[:k]