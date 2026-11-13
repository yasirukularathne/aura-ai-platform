
import json

from app.agents.rag_agent import rag_graph
from app.auth import require_role
from app.config import settings
from app.observability import trace
from app.workspace_store import WorkspaceStore
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .chat import ChatRequest

router = APIRouter(prefix="/api/chat", tags=["Chat"])

workspace_store = WorkspaceStore(settings.database_path)


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


@router.post("/stream")
def stream_chat(request: Request, payload: ChatRequest):
    require_role(request, "viewer", "editor", "admin")

    # Validate workspace before creating the streaming response.
    workspace_id = _get_workspace_id(request)

    def events():
        with trace(
            "chat.stream",
            {"tenant_id": request.state.tenant_id},
        ):
            result = rag_graph.invoke({
                "question": payload.question,
                "tenant_id": request.state.tenant_id,
                "workspace_id": workspace_id,
            })

        yield (
            f"event: answer\n"
            f"data: {json.dumps(result.get('answer', ''))}\n\n"
        )

        yield (
            f"event: citations\n"
            f"data: {json.dumps(result.get('citations', []))}\n\n"
        )

        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
