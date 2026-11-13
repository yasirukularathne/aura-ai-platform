
import importlib

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.workspace_store import WorkspaceStore


client = TestClient(app)


def create_other_tenant_workspace(tmp_path):
    """Create a workspace owned by a tenant other than the API key tenant."""
    store = WorkspaceStore(str(tmp_path / "workspaces.db"))
    workspace = store.create(
        tenant_id="other-tenant",
        name="Private Workspace",
    )
    return store, workspace["workspace_id"]


@pytest.mark.parametrize(
    "module_name",
    [
        "app.api.rag",
        "app.api.documents",
        "app.api.chat",
        "app.api.streaming",
    ],
)
def test_api_rejects_workspace_owned_by_another_tenant(
    configured_api_key,
    monkeypatch,
    tmp_path,
    module_name,
):
    store, workspace_id = create_other_tenant_workspace(tmp_path)

    module = importlib.import_module(module_name)
    monkeypatch.setattr(module, "workspace_store", store)

    headers = {
        "X-API-Key": configured_api_key,
        "X-Workspace-ID": workspace_id,
    }

    if module_name == "app.api.rag":
        response = client.post(
            "/api/rag/ask",
            headers=headers,
            json={"question": "What does this document say?"},
        )

    elif module_name == "app.api.documents":
        response = client.post(
            "/api/documents/upload",
            headers=headers,
            files={
                "file": (
                    "policy.pdf",
                    b"%PDF-1.7 test document",
                    "application/pdf",
                )
            },
        )

    elif module_name == "app.api.chat":
        response = client.post(
            "/api/chat/ask",
            headers=headers,
            json={"question": "What does this document say?"},
        )

    else:
        response = client.post(
            "/api/chat/stream",
            headers=headers,
            json={"question": "What does this document say?"},
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workspace not found"


def test_workspace_list_does_not_expose_other_tenant_workspaces(
    configured_api_key,
    monkeypatch,
    tmp_path,
):
    store, _ = create_other_tenant_workspace(tmp_path)

    monkeypatch.setattr(
        "app.api.workspaces.workspace_store",
        store,
    )

    response = client.get(
        "/api/workspaces",
        headers={"X-API-Key": configured_api_key},
    )

    assert response.status_code == 200
    assert response.json()["workspaces"] == []
    assert response.json()["total"] == 0
