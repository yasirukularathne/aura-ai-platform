# AURA Phase 2 External-Service Integration Report

## Scope and safety

Audit scope: Groq, embeddings, Qdrant, S3, the worker/RAG flow, and Docker Compose integration.

The audit was read-only with respect to application source code and dependency manifests. Test data used unique audit identifiers. No existing Qdrant collection or document was deleted. Credentials and secret values were not printed. The one isolated failed ingestion job and its isolated file/database rows were removed after testing.

## Environment evidence

- Docker daemon: available.
- Python: 3.11.8.
- Node.js: v20.10.0.
- `docker compose config --quiet`: PASS.
- Compose services started successfully: backend, worker, PostgreSQL, Redis, Qdrant, Prometheus, and Grafana.
- Backend liveness: `GET /health/live` returned HTTP 200.
- Backend readiness: `GET /health/ready` returned HTTP 200 with Qdrant and database available.
- Worker connected to Redis and reported `celery... ready`.
- S3 configuration: not configured (`STORAGE_BACKEND`, `S3_BUCKET`, and S3 credentials absent).
- The host `.env` contained Groq and Qdrant credentials, but their values were not recorded.

## Test matrix

| Area | Test | Result | Evidence |
|---|---|---|---|
| Groq | Real API connectivity and inference | PASS | `ChatGroq` invoked `openai/gpt-oss-20b`; response contained the requested `AURA_LIVE_OK` marker; HTTP call completed in approximately 1.1 seconds. |
| Groq | Invalid API key | PASS | An isolated request with a deliberately invalid key returned `AuthenticationError`, HTTP 401, and `invalid_api_key`. |
| Groq | Timeout handling | PASS | A request with a 1 ms timeout raised `APITimeoutError` and did not hang. |
| Embeddings | Host model loading | FAIL | `BAAI/bge-small-en-v1.5` could not load because installed NumPy 2.4.6 was incompatible with compiled NumPy 1.x dependencies (`pyarrow`/`scikit-learn`). |
| Embeddings | Container model loading and generation | PASS | Worker image loaded `BAAI/bge-small-en-v1.5` and generated an embedding of dimension 384. |
| Embeddings | Batch generation | PARTIAL | The host batch test was blocked by the same NumPy import failure. The container successfully generated a single vector, but a separate batch result was not captured. |
| Qdrant | Configured remote collection connectivity | PARTIAL | Authenticated Qdrant request reached the configured service, but the configured `aura_documents` collection returned HTTP 404 because it does not exist in that service. |
| Qdrant | Isolated insertion and retrieval | PASS | A unique temporary collection accepted three points and returned the expected point after vector search. The temporary collection was deleted after the test. |
| Qdrant | Tenant/workspace metadata filtering | PASS | Payload keyword indexes plus a filter for `audit-tenant-a` and `audit-workspace-a` returned only point `1`; points for another tenant/workspace were excluded. |
| Qdrant | Docker-local service connectivity | PASS | `GET http://localhost:6333/collections` returned HTTP 200 with an empty collection list. |
| S3 | Upload, download, retrieval, deletion | BLOCKED | S3 backend and bucket were not configured, so no external object-storage operation could be safely executed. |
| S3 | Failed upload handling | PASS | With `STORAGE_BACKEND=s3` and no bucket, `put_file` raised `RuntimeError: S3_BUCKET is required when STORAGE_BACKEND=s3`. |
| S3 | Credential failure handling | BLOCKED | No isolated bucket/endpoint was available for a credential-negative test. |
| RAG | Upload isolated document | PASS | API accepted an isolated TXT upload with HTTP 202 and returned a job ID and Celery task ID. |
| RAG | Worker indexing | FAIL | Job ended `failed` after four attempts. Worker logs showed `FileNotFoundError` for the uploaded path. The backend had the file, while the worker container had no `/app/data/documents/uploads` mount. |
| RAG | Real LLM answer and citation | BLOCKED | No indexed test document was available after the worker failure, so a valid retrieval-to-generation test could not be performed without bypassing the broken integration. |
| RAG | Unsupported-question safe fallback | BLOCKED | The prerequisite isolated document could not be indexed and the Docker-local Qdrant collection was empty. |
| Docker | Backend/worker required configuration parity | FAIL | Both services received database and Celery settings, but only backend received the upload volume, Qdrant URL override, and `STORAGE_BACKEND` override. The worker therefore cannot access backend-local uploaded files. |
| Docker | External-service connectivity | PARTIAL | Backend readiness, Redis worker connection, PostgreSQL, and Docker-local Qdrant passed. Remote Qdrant collection setup and S3 were not available. |
| Docker | Restart recovery | PASS | A uniquely titled conversation was created, backend and worker were restarted, and the same conversation was read successfully afterward. The isolated conversation was then deleted. |

## Key findings

### 1. Worker cannot consume backend-local uploads

The backend service mounts `document_uploads` at `/app/data/documents/uploads`. The worker service does not mount that volume. The upload endpoint therefore accepts the request, but the Celery task cannot open the path recorded in PostgreSQL.

Observed evidence:

```text
worker_upload_mount=missing
FileNotFoundError: [Errno 2] No such file or directory:
data/documents/uploads/<isolated-audit-file>.txt
Task aura.ingestion.process[...] retry
```

This is the primary Phase 2 integration blocker.

### 2. Qdrant configuration is split between remote and Docker-local services

The host configuration points to a configured remote Qdrant service, where the expected `aura_documents` collection was absent. Compose overrides the backend Qdrant URL to `http://qdrant:6333`, while the worker does not receive the same override. The local Docker Qdrant service was reachable but had no collections.

### 3. Host and container Python environments differ

The host embedding environment is broken by a NumPy ABI mismatch. The container image loads the model and produces 384-dimensional vectors successfully. This means the application image is healthier than the current host test environment, but local validation is not reproducible until the host environment is aligned.

### 4. S3 remains unverified

No S3-compatible endpoint, bucket, or credentials were configured. Upload/download/deletion and invalid-credential behavior remain untested.

## Remaining issues and recommended order

1. Mount the same `document_uploads` volume into the worker, or make ingestion fully object-storage based so worker file access does not depend on a local shared volume.
2. Provide the worker the same Qdrant URL and storage configuration as the backend, and ensure the target collection is created in the selected Qdrant service.
3. Pin or repair the host NumPy/scikit-learn/pyarrow environment without changing production dependencies during this audit.
4. Configure an isolated S3-compatible test bucket and repeat upload, download, deletion, and invalid-credential tests.
5. Re-run the complete RAG flow: upload, worker completion, supported question with citations, and unsupported question safe fallback.

## Overall verdict

**PARTIAL — external integrations are not yet Phase 2 complete.**

Groq, container embeddings, isolated Qdrant filtering, service readiness, and restart persistence work. The production-like worker ingestion path fails because of storage-volume mismatch; S3 is unconfigured; and the full RAG answer/citation and safe-fallback flows could not be validated.
