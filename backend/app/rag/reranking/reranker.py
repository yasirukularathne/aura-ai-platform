from functools import lru_cache

from sentence_transformers import CrossEncoder


@lru_cache(maxsize=1)
def get_reranker_model():
    return CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


class Reranker:

    def __init__(self):

        self.model = get_reranker_model()

    def rerank(
        self,
        query: str,
        documents,
        top_k: int = 5
    ):

        pairs = [
            [query, document.page_content]
            for document in documents
        ]

        scores = self.model.predict(pairs)

        ranked = sorted(
            zip(documents, scores),
            key=lambda item: item[1],
            reverse=True
        )

        return [
            {
                "document": document,
                "score": float(score)
            }
            for document, score in ranked[:top_k]
        ]