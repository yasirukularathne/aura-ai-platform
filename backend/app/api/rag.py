
from app.agents.rag_agent import rag_graph
from app.config import settings
from app.workspace_store import WorkspaceStore
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"],
)

workspace_store = WorkspaceStore(settings.database_path)


class QuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=10_000)


def _get_workspace_id(request: Request) -> str | None:
    workspace_id = request.headers.get("X-Workspace-ID")

    if workspace_id is None:
        return None

    workspace_id = workspace_id.strip()

    if not workspace_id:
        return None

    if not workspace_store.belongs_to_tenant(
        request.state.tenant_id,
        workspace_id,
    ):
        raise HTTPException(
            status_code=404,
            detail="Workspace not found",
        )

    return workspace_id


@router.post("/ask")
def ask(request: Request, payload: QuestionRequest):
    workspace_id = _get_workspace_id(request)

    result = rag_graph.invoke({
        "question": payload.question,
        "tenant_id": request.state.tenant_id,
        "workspace_id": workspace_id,
    })

    return result
