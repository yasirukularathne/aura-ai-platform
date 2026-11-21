from functools import lru_cache

from app.config import settings
from langchain_huggingface import HuggingFaceEmbeddings


@lru_cache(maxsize=1)
def get_embedding_model():
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model_name
    )