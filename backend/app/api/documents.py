from hashlib import sha256
from pathlib import Path
from typing import Annotated

from app.auth import ApiKeyStore, require_role
from app.config import settings
from app.rag.ingestion.jobs import IngestionJobStore
from app.rag.ingestion.loaders import SUPPORTED_EXTENSIONS
from app.rag.ingestion.service import (
    create_document_path,
    process_ingestion_job,
)
from app.rag.ingestion.service import (
    reindex_document as run_reindex_document,
)
from app.rag.vectorstore.qdrant_store import delete_document_vectors
from app.storage import delete_file, put_file
from app.worker import enqueue_ingestion, enqueue_reindex
from app.workspace_store import WorkspaceStore
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

router = APIRouter(prefix="/api/documents", tags=["Documents"])

job_store = IngestionJobStore(settings.database_path)
audit_store = ApiKeyStore(settings.database_path)
workspace_store = WorkspaceStore(settings.database_path)


def _get_workspace_id(request: Request) -> str | None:
    workspace_id = request.headers.get("X-Workspace-ID")

    if workspace_id is None:
        return None

    workspace_id = workspace_id.strip()

    if not workspace_id:
        return None

    belongs_to_tenant = workspace_store.belongs_to_tenant(
        request.state.tenant_id,
        workspace_id,
    )

    if not belongs_to_tenant:
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return workspace_id


def _get_scoped_document(
    request: Request,
    job_id: str,
    workspace_id: str | None,
):
    document = job_store.get(request.state.tenant_id, job_id)

    if document is None:
        return None

    if (
        workspace_id is not None
        and document.get("workspace_id") != workspace_id
    ):
        return None

    return document


@router.post("/upload", status_code=202)
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(...)],
):
    require_role(request, "editor", "admin")

    # Validate workspace ownership before accepting or storing the file.
    workspace_id = _get_workspace_id(request)

    filename = file.filename or ""
    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported document type",
        )

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    destination = create_document_path(upload_dir, filename)
    total_bytes = 0

    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)

                if total_bytes > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail="Uploaded file exceeds the size limit",
                    )

                output.write(chunk)

        with destination.open("rb") as stored_file:
            if extension == ".pdf" and stored_file.read(4) != b"%PDF":
                raise HTTPException(
                    status_code=415,
                    detail="Uploaded file is not a valid PDF",
                )

    except HTTPException:
        destination.unlink(missing_ok=True)
        raise

    except OSError as exc:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=500,
            detail="Could not store the uploaded document",
        ) from exc

    finally:
        await file.close()

    checksum = sha256(destination.read_bytes()).hexdigest()

    duplicate = job_store.find_by_checksum(
        request.state.tenant_id,
        checksum,
    )

    if duplicate is not None:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=409,
            detail={
                "message": "A document with the same content already exists",
                "job_id": duplicate["job_id"],
            },
        )

    job_id = job_store.create(
        request.state.tenant_id,
        filename,
        destination,
        checksum=checksum,
        content_type=file.content_type,
        workspace_id=workspace_id,
    )

    try:
        put_file(
            destination,
            f"{request.state.tenant_id}/{job_id}/{filename}",
        )

    except RuntimeError as exc:
        job_store.update(job_id, "failed", str(exc))
        destination.unlink(missing_ok=True)

        raise HTTPException(
            status_code=503,
            detail="Could not store the uploaded document",
        ) from exc

    audit_store.audit(
        request.state.tenant_id,
        request.state.key_id,
        "document.upload",
        job_id,
        filename,
    )

    task_id = enqueue_ingestion(
        settings.database_path,
        job_id,
        str(destination),
    )

    if task_id is None:
        background_tasks.add_task(
            process_ingestion_job,
            job_store,
            job_id,
            destination,
        )

    return {
        "status": "accepted",
        "job_id": job_id,
        "filename": filename,
        "bytes": total_bytes,
        "message": "Document queued for indexing",
        "task_id": task_id,
    }


@router.post("/{job_id}/reindex", status_code=202)
def reindex_document(
    request: Request,
    background_tasks: BackgroundTasks,
    job_id: str,
):
    require_role(request, "editor", "admin")

    workspace_id = _get_workspace_id(request)

    document = _get_scoped_document(
        request,
        job_id,
        workspace_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document["status"] == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document is already processing",
        )

    job_store.requeue(
        request.state.tenant_id,
        job_id,
    )

    task_id = enqueue_reindex(
        settings.database_path,
        job_id,
        document["file_path"],
    )

    if task_id is None:
        background_tasks.add_task(
            run_reindex_document,
            job_store,
            job_id,
            Path(document["file_path"]),
        )

    return {
        "status": "accepted",
        "job_id": job_id,
        "task_id": task_id,
    }


@router.get("/{job_id}")
def get_document_status(
    request: Request,
    job_id: str,
):
    workspace_id = _get_workspace_id(request)

    job = _get_scoped_document(
        request,
        job_id,
        workspace_id,
    )

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="Ingestion job not found",
        )

    return job


@router.get("")
def list_documents(
    request: Request,
    limit: int = 100,
):
    workspace_id = _get_workspace_id(request)

    documents = job_store.list_jobs(
        request.state.tenant_id,
        limit,
    )

    if workspace_id is not None:
        documents = [
            document
            for document in documents
            if document.get("workspace_id") == workspace_id
        ]

    return {
        "documents": [
            {
                key: value
                for key, value in document.items()
                if key != "file_path"
            }
            for document in documents
        ]
    }


@router.delete("/{job_id}")
def delete_document(
    request: Request,
    job_id: str,
):
    require_role(request, "editor", "admin")

    workspace_id = _get_workspace_id(request)

    document = _get_scoped_document(
        request,
        job_id,
        workspace_id,
    )

    if document is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if document["status"] == "processing":
        raise HTTPException(
            status_code=409,
            detail="Document cannot be deleted while it is being indexed",
        )

    try:
        delete_document_vectors(
            job_id,
            request.state.tenant_id,
            document["file_path"],
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Document vectors could not be removed",
        ) from exc

    object_key = (
        f"{request.state.tenant_id}/{job_id}/{document['filename']}"
    )

    delete_file(
        Path(document["file_path"]),
        object_key,
    )

    job_store.delete(
        request.state.tenant_id,
        job_id,
    )

    audit_store.audit(
        request.state.tenant_id,
        request.state.key_id,
        "document.delete",
        job_id,
        document["filename"],
    )

    return {
        "status": "deleted",
        "job_id": job_id,
    }