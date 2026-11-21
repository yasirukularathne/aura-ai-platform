from app.auth import require_role
from app.config import settings
from app.workspace_store import WorkspaceStore
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])

workspace_store = WorkspaceStore(settings.database_path)


class WorkspaceCreateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)


@router.post("", status_code=201)
def create_workspace(
    request: Request,
    payload: WorkspaceCreateRequest,
):
    require_role(request, "admin")

    workspace = workspace_store.create(
        tenant_id=request.state.tenant_id,
        name=payload.name,
    )

    return {
        "workspace": workspace,
    }


@router.get("")
def list_workspaces(request: Request):
    require_role(request, "viewer", "editor", "admin")

    workspaces = workspace_store.list(
        tenant_id=request.state.tenant_id,
    )

    return {
        "workspaces": workspaces,
        "total": len(workspaces),
    }