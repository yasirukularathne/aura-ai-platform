import hashlib
import logging
from pathlib import Path
from uuid import NAMESPACE_URL, uuid4, uuid5

from app.rag.ingestion.chunker import split_documents
from app.rag.ingestion.jobs import IngestionJobStore
from app.rag.ingestion.loaders import load_document
from app.rag.vectorstore.qdrant_store import (
    create_vector_store,
    delete_obsolete_document_versions,
)

logger = logging.getLogger("aura.ingestion")


def _build_point_ids(document_id: str, document_version: int, chunk_count: int) -> list[str]:
    """Return stable Qdrant point IDs for every chunk in a document version."""
    return [
        str(uuid5(
            NAMESPACE_URL,
            f"aura:{document_id}:v{document_version}:chunk:{index}",
        ))
        for index in range(chunk_count)
    ]


def _version_from_checksum(checksum: str) -> int:
    """Map content to a positive, deterministic version identifier."""
    return int.from_bytes(hashlib.sha256(checksum.encode("utf-8")).digest()[:8], "big") or 1


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
    """Load, annotate, chunk, and index one immutable content version."""
    documents = load_document(file_path)
    checksum = checksum or hashlib.sha256(file_path.read_bytes()).hexdigest()
    document_version = _version_from_checksum(checksum)
    for document in documents:
        document.metadata["aura_job_id"] = job_id
        document.metadata["aura_document_id"] = document_id
        document.metadata["aura_tenant_id"] = tenant_id
        document.metadata["aura_workspace_id"] = workspace_id
        document.metadata["filename"] = filename or file_path.name
        document.metadata["content_type"] = content_type
        document.metadata["checksum"] = checksum
        document.metadata["document_version"] = document_version
    chunks = split_documents(documents)
    if not chunks:
        raise ValueError("The document did not contain indexable text")
    point_ids = _build_point_ids(document_id, document_version, len(chunks))
    for index, chunk in enumerate(chunks):
        chunk.metadata["aura_chunk_id"] = point_ids[index]
        chunk.metadata["chunk_index"] = index

    # Content-derived IDs make retries idempotent while isolating new versions.
    create_vector_store(chunks, ids=point_ids)
    logger.info(
        "document_indexed",
        extra={"path": str(file_path), "chunks": len(chunks), "version": document_version},
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
    """Build the new version first; only then remove older vectors."""
    job = store.get_by_id(job_id)
    if job is None:
        return False

    if not process_ingestion_job(
        store,
        job_id,
        file_path,
        raise_on_failure=raise_on_failure,
    ):
        return False

    try:
        checksum = job.get("checksum") or hashlib.sha256(file_path.read_bytes()).hexdigest()
        version = _version_from_checksum(checksum)
        delete_obsolete_document_versions(
            document_id=job["document_id"],
            tenant_id=job["tenant_id"],
            keep_version=version,
        )
    except (OSError, RuntimeError) as exc:
        # New version is already indexed. Keep it and report cleanup failure;
        # old vectors remain available and can be cleaned up on a later retry.
        store.update(job_id, "failed", f"Indexed; obsolete-version cleanup pending: {exc}")
        logger.exception("document_reindex_cleanup_pending", extra={"job_id": job_id})
        if raise_on_failure:
            raise
        return False

    return True


def create_document_path(upload_dir: Path, original_filename: str) -> Path:
    """Create a unique, sanitized destination path preserving the extension."""
    safe_name = Path(original_filename).name
    stem = Path(safe_name).stem or "document"
    normalized_stem = "".join(
        character if character.isalnum() or character in "-_" else "_"
        for character in stem
    )[:80]
    return upload_dir / f"{uuid4()}-{normalized_stem}{Path(safe_name).suffix.lower()}"
