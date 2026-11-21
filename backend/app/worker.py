from pathlib import Path

from app.config import settings
from app.rag.ingestion.jobs import IngestionJobStore
from app.rag.ingestion.service import process_ingestion_job, reindex_document

try:
    from celery import Celery
except ImportError:
    Celery = None


celery_app = None
if Celery is not None and settings.celery_broker_url:
    celery_app = Celery(
        "aura",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend or settings.celery_broker_url,
    )


def enqueue_ingestion(database_path: str, job_id: str, file_path: str) -> str | None:
    if celery_app is None:
        return None
    result = process_ingestion_task.delay(database_path, job_id, file_path)
    return str(result.id)


def enqueue_reindex(database_path: str, job_id: str, file_path: str) -> str | None:
    if celery_app is None:
        return None
    result = process_reindex_task.delay(database_path, job_id, file_path)
    return str(result.id)


if celery_app is not None:

    @celery_app.task(
        bind=True,
        name="aura.ingestion.process",
        autoretry_for=(OSError, RuntimeError),
        retry_backoff=True,
        retry_kwargs={"max_retries": 3},
    )
    def process_ingestion_task(
        self,
        database_path: str,
        job_id: str,
        file_path: str,
    ) -> None:
        process_ingestion_job(
            IngestionJobStore(database_path),
            job_id,
            Path(file_path),
            raise_on_failure=True,
        )

    @celery_app.task(
        bind=True,
        name="aura.ingestion.reindex",
        autoretry_for=(OSError, RuntimeError),
        retry_backoff=True,
        retry_kwargs={"max_retries": 3},
    )
    def process_reindex_task(
        self,
        database_path: str,
        job_id: str,
        file_path: str,
    ) -> None:
        reindex_document(
            IngestionJobStore(database_path),
            job_id,
            Path(file_path),
            raise_on_failure=True,
        )
