
from app.config import settings
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_root_is_public():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["project"] == "AURA"


def test_liveness_is_public():
    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
    assert response.headers["X-Request-ID"]


def test_metrics_endpoint_reports_requests():
    client.get("/health/live")
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "aura_http_requests_total" in response.text
    assert 'path="/health/live"' in response.text


def test_api_requires_configuration(monkeypatch):
    monkeypatch.setattr(settings, "api_key", None)
    response = client.post("/api/rag/ask", json={"question": "hello"})

    assert response.status_code == 503
    assert response.json()["detail"] == "API authentication is not configured"


def test_api_rejects_invalid_key(configured_api_key):
    response = client.post(
        "/api/rag/ask",
        headers={"X-API-Key": "wrong-key"},
        json={"question": "hello"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or missing API key"


def test_api_validates_question(configured_api_key):
    response = client.post(
        "/api/rag/ask",
        headers={"X-API-Key": configured_api_key},
        json={"question": ""},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Request validation failed"
    assert response.headers["X-Request-ID"]


def test_conversation_creation_and_tenant_isolation(configured_api_key):
    created = client.post(
        "/api/chat/conversations",
        headers={"X-API-Key": configured_api_key},
        json={"title": "Policy chat"},
    )
    assert created.status_code == 201
    conversation_id = created.json()["conversation_id"]

    loaded = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers={"X-API-Key": configured_api_key},
    )
    assert loaded.status_code == 200
    assert loaded.json()["messages"] == []


def test_chat_ask_persists_messages(configured_api_key, monkeypatch):
    monkeypatch.setattr(
        "app.api.chat.rag_graph.invoke",
        lambda state: {
            "answer": f"Answer for: {state['question']}",
            "citations": [{"document": "policy.pdf", "page": 1}],
        },
    )
    response = client.post(
        "/api/chat/ask",
        headers={"X-API-Key": configured_api_key},
        json={"question": "What is covered?"},
    )
    assert response.status_code == 200
    conversation_id = response.json()["conversation_id"]

    history = client.get(
        f"/api/chat/conversations/{conversation_id}",
        headers={"X-API-Key": configured_api_key},
    )
    assert [message["role"] for message in history.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_chat_stream_returns_server_sent_events(configured_api_key, monkeypatch):
    monkeypatch.setattr(
        "app.api.streaming.rag_graph.invoke",
        lambda state: {
            "answer": "Grounded answer",
            "citations": [{"document": "policy.pdf", "page": 1}],
        },
    )
    response = client.post(
        "/api/chat/stream",
        headers={"X-API-Key": configured_api_key},
        json={"question": "What is covered?"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: answer" in response.text
    assert "event: citations" in response.text
    assert "event: done" in response.text


def test_document_upload_accepts_pdf(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    from app.rag.ingestion.jobs import IngestionJobStore

    processed = []
    monkeypatch.setattr(
        "app.api.documents.process_ingestion_job",
        lambda store, job_id, path: processed.append((job_id, path)),
    )
    monkeypatch.setattr("app.api.documents.settings.upload_dir", str(tmp_path))
    monkeypatch.setattr(
        "app.api.documents.job_store",
        IngestionJobStore(str(tmp_path / "jobs.db")),
    )

    response = client.post(
        "/api/documents/upload",
        headers={"X-API-Key": configured_api_key},
        files={"file": ("policy.pdf", b"%PDF-1.7 policy", "application/pdf")},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    job_id = response.json()["job_id"]
    assert len(processed) == 1
    assert processed[0][0] == job_id
    assert processed[0][1].exists()
    assert processed[0][1].read_bytes() == b"%PDF-1.7 policy"

    status = client.get(
        f"/api/documents/{job_id}",
        headers={"X-API-Key": configured_api_key},
    )
    assert status.status_code == 200
    assert status.json()["status"] == "queued"
    assert status.json()["tenant_id"] == "default"


def test_document_status_returns_not_found(configured_api_key):
    response = client.get(
        "/api/documents/missing-job",
        headers={"X-API-Key": configured_api_key},
    )

    assert response.status_code == 404


def test_document_status_is_tenant_scoped(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    from app.rag.ingestion.jobs import IngestionJobStore

    store = IngestionJobStore(str(tmp_path / "jobs.db"))
    document_path = tmp_path / "policy.pdf"
    document_path.write_bytes(b"%PDF")
    job_id = store.create("other-tenant", "policy.pdf", document_path)
    monkeypatch.setattr("app.api.documents.job_store", store)

    response = client.get(
        f"/api/documents/{job_id}",
        headers={"X-API-Key": configured_api_key},
    )

    assert response.status_code == 404


def test_documents_can_be_listed_and_deleted(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    from app.rag.ingestion.jobs import IngestionJobStore

    store = IngestionJobStore(str(tmp_path / "jobs.db"))
    document_path = tmp_path / "policy.pdf"
    document_path.write_bytes(b"%PDF")
    job_id = store.create("default", "policy.pdf", document_path)
    monkeypatch.setattr("app.api.documents.job_store", store)
    deleted = []
    monkeypatch.setattr(
        "app.api.documents.delete_document_vectors",
        lambda current_job_id, tenant_id, source_path: deleted.append(
            (current_job_id, tenant_id, source_path)
        ),
    )

    listed = client.get(
        "/api/documents",
        headers={"X-API-Key": configured_api_key},
    )
    assert listed.status_code == 200
    assert listed.json()["documents"][0]["job_id"] == job_id
    assert "file_path" not in listed.json()["documents"][0]

    response = client.delete(
        f"/api/documents/{job_id}",
        headers={"X-API-Key": configured_api_key},
    )
    assert response.status_code == 200
    assert deleted == [(job_id, "default", str(document_path))]
    assert not document_path.exists()
    assert store.get("default", job_id) is None


def test_viewer_cannot_delete_documents(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    from app.auth import ApiKeyStore
    from app.rag.ingestion.jobs import IngestionJobStore

    store = IngestionJobStore(str(tmp_path / "jobs.db"))
    document_path = tmp_path / "policy.pdf"
    document_path.write_bytes(b"%PDF")
    job_id = store.create("default", "policy.pdf", document_path)
    monkeypatch.setattr("app.api.documents.job_store", store)

    key_store = ApiKeyStore(settings.database_path)
    key_id, viewer_key = key_store.create("default", "viewer")
    try:
        response = client.delete(
            f"/api/documents/{job_id}",
            headers={"X-API-Key": viewer_key},
        )
    finally:
        key_store.revoke("default", key_id)

    assert response.status_code == 403


def test_admin_can_create_and_revoke_api_key(configured_api_key):
    response = client.post(
        "/api/admin/api-keys",
        headers={"X-API-Key": configured_api_key},
        json={"role": "viewer"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "viewer"
    assert body["api_key"]

    revoke = client.delete(
        f"/api/admin/api-keys/{body['key_id']}",
        headers={"X-API-Key": configured_api_key},
    )
    assert revoke.status_code == 200


def test_admin_can_read_audit_events(configured_api_key):
    response = client.get(
        "/api/admin/audit",
        headers={"X-API-Key": configured_api_key},
    )

    assert response.status_code == 200
    assert isinstance(response.json()["events"], list)


def test_viewer_cannot_upload_documents(configured_api_key):
    created = client.post(
        "/api/admin/api-keys",
        headers={"X-API-Key": configured_api_key},
        json={"role": "viewer"},
    )
    viewer_key = created.json()["api_key"]
    key_id = created.json()["key_id"]

    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-API-Key": viewer_key},
            files={"file": ("policy.pdf", b"%PDF-1.7 policy", "application/pdf")},
        )
    finally:
        client.delete(
            f"/api/admin/api-keys/{key_id}",
            headers={"X-API-Key": configured_api_key},
        )

    assert response.status_code == 403


def test_non_admin_key_cannot_create_api_key(configured_api_key):
    from app.api import admin
    from app.auth import ApiKeyStore

    key_store = ApiKeyStore(admin.settings.database_path)
    key_id, viewer_key = key_store.create("default", "viewer")

    try:
        response = client.post(
            "/api/admin/api-keys",
            headers={"X-API-Key": viewer_key},
            json={"role": "viewer"},
        )
    finally:
        key_store.revoke("default", key_id)

    assert response.status_code == 403


def test_document_upload_rejects_unsupported_type(configured_api_key, tmp_path):
    from app.api.documents import settings as document_settings

    original_upload_dir = document_settings.upload_dir
    document_settings.upload_dir = str(tmp_path)
    try:
        response = client.post(
            "/api/documents/upload",
            headers={"X-API-Key": configured_api_key},
            files={"file": ("notes.exe", b"not a document", "application/octet-stream")},
        )
    finally:
        document_settings.upload_dir = original_upload_dir

    assert response.status_code == 415


def test_document_upload_rejects_oversized_file(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr("app.api.documents.settings.upload_dir", str(tmp_path))
    monkeypatch.setattr("app.api.documents.settings.max_upload_bytes", 4)

    response = client.post(
        "/api/documents/upload",
        headers={"X-API-Key": configured_api_key},
        files={"file": ("policy.pdf", b"%PDF-too-large", "application/pdf")},
    )

    assert response.status_code == 413
    assert not list(tmp_path.iterdir())
