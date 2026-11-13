import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from app.rag.ingestion.chunker import split_documents
from app.rag.ingestion.jobs import IngestionJobStore
from app.rag.ingestion.loaders import load_document
from app.rag.vectorstore.qdrant_store import (
    create_vector_store,
    delete_document_vectors,
)

logger = logging.getLogger("aura.ingestion")


def index_document(
    file_path: Path,
    job_id: str,
    tenant_id: str,
    document_id: str,
    workspace_id: str | None = None,
    filename: str | None = None,
    checksum: str | None = None,
    content_type: str | None = None,
) -> None:
    """Load, annotate, chunk, and index one document."""
    documents = load_document(file_path)
    checksum = checksum or hashlib.sha256(file_path.read_bytes()).hexdigest()
    for document in documents:
        document.metadata["aura_job_id"] = job_id
        document.metadata["aura_document_id"] = document_id
        document.metadata["aura_tenant_id"] = tenant_id
        document.metadata["aura_workspace_id"] = workspace_id
        document.metadata["filename"] = filename or file_path.name
        document.metadata["content_type"] = content_type
        document.metadata["checksum"] = checksum
        document.metadata["document_version"] = 1
    chunks = split_documents(documents)
    if not chunks:
        raise ValueError("The document did not contain indexable text")
    for index, chunk in enumerate(chunks):
        chunk.metadata["aura_chunk_id"] = f"{document_id}:{index}"
        chunk.metadata["chunk_index"] = index

    create_vector_store(chunks)
    logger.info(
        "document_indexed",
        extra={"path": str(file_path), "chunks": len(chunks)},
    )


def process_ingestion_job(
    store: IngestionJobStore,
    job_id: str,
    file_path: Path,
    *,
    raise_on_failure: bool = False,
) -> bool:
    job = store.get_by_id(job_id)
    if job is None:
        return False
    store.begin_attempt(job_id)
    try:
        index_document(
            file_path,
            job_id,
            job["tenant_id"],
            job["document_id"],
            job.get("workspace_id"),
            job["filename"],
            job["checksum"],
            job.get("content_type"),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        store.update(job_id, "failed", str(exc))
        logger.exception("document_indexing_failed", extra={"job_id": job_id})
        if raise_on_failure and isinstance(exc, (OSError, RuntimeError)):
            raise
        return False
    store.update(job_id, "completed")
    return True


def reindex_document(
    store: IngestionJobStore,
    job_id: str,
    file_path: Path,
    *,
    raise_on_failure: bool = False,
) -> bool:
    job = store.get_by_id(job_id)
    if job is None:
        return False
    try:
        delete_document_vectors(job_id, job["tenant_id"], str(file_path))
    except RuntimeError as exc:
        store.update(job_id, "failed", str(exc))
        logger.exception("document_reindex_cleanup_failed", extra={"job_id": job_id})
        if raise_on_failure:
            raise
        return False
    return process_ingestion_job(
        store,
        job_id,
        file_path,
        raise_on_failure=raise_on_failure,
    )


def create_document_path(upload_dir: Path, original_filename: str) -> Path:
    """Create a unique, sanitized destination path preserving the extension."""
    safe_name = Path(original_filename).name
    stem = Path(safe_name).stem or "document"
    normalized_stem = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in stem
    )[:80]
    return upload_dir / f"{uuid4()}-{normalized_stem}{Path(safe_name).suffix.lower()}"
