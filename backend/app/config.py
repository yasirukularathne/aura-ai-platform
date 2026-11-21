from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AURA AI Platform"
    environment: str = "development"
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection_name: str = "aura_documents"
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    llm_api_key: str | None = Field(default=None, repr=False)
    api_key: str | None = Field(default=None, repr=False)
    tenant_id: str = "default"
    upload_dir: str = "data/documents/uploads"
    max_upload_bytes: int = 10 * 1024 * 1024
    database_path: str = "data/aura.db"
    database_url: str | None = None
    storage_backend: str = "local"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = Field(default=None, repr=False)
    s3_secret_access_key: str | None = Field(default=None, repr=False)
    celery_broker_url: str | None = None
    celery_result_backend: str | None = None
    langfuse_public_key: str | None = Field(default=None, repr=False)
    langfuse_secret_key: str | None = Field(default=None, repr=False)
    langfuse_host: str = "https://cloud.langfuse.com"
    api_rate_limit_per_minute: int = 60
    upload_rate_limit_per_minute: int = 10
    ai_rate_limit_per_minute: int = 30
    redis_url: str | None = None
    api_key_ttl_days: int = 90
    retention_days: int = 365
    cors_origins: str = "http://localhost:5500,http://127.0.0.1:5500"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Keep these names temporarily for existing modules during the configuration
# migration.
QDRANT_URL = settings.qdrant_url
QDRANT_API_KEY = settings.qdrant_api_key
QDRANT_COLLECTION_NAME = settings.qdrant_collection_name
