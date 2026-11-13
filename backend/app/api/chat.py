
import json

from app.agents.rag_agent import rag_graph
from app.auth import require_role
from app.config import settings
from app.conversations import ConversationStore
from app.observability import trace
from app.workspace_store import WorkspaceStore
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/chat", tags=["Chat"])

conversation_store = ConversationStore(settings.database_path)
workspace_store = WorkspaceStore(settings.database_path)


class ConversationCreateRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=120)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10_000)
    conversation_id: str | None = None


class ConversationRenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


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


@router.post("/conversations", status_code=201)
def create_conversation(request: Request, payload: ConversationCreateRequest):
    workspace_id = _get_workspace_id(request)

    return conversation_store.create(
        request.state.tenant_id,
        payload.title,
        workspace_id=workspace_id,
    )


@router.get("/conversations")
def list_conversations(request: Request, limit: int = 50, offset: int = 0):
    workspace_id = _get_workspace_id(request)

    return {
        "conversations": conversation_store.list_conversations(
            request.state.tenant_id,
            limit,
            offset,
            workspace_id=workspace_id,
        )
    }


@router.patch("/conversations/{conversation_id}")
def rename_conversation(
    request: Request,
    conversation_id: str,
    payload: ConversationRenameRequest,
):
    workspace_id = _get_workspace_id(request)

    conversation = conversation_store.get(
        request.state.tenant_id,
        conversation_id,
        workspace_id=workspace_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    updated = conversation_store.rename(
        request.state.tenant_id,
        conversation_id,
        payload.title,
        workspace_id=workspace_id,
    )

    if not updated:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation_store.get(
        request.state.tenant_id,
        conversation_id,
        workspace_id=workspace_id,
    )


@router.delete("/conversations/{conversation_id}")
def delete_conversation(request: Request, conversation_id: str):
    require_role(request, "editor", "admin")

    workspace_id = _get_workspace_id(request)

    deleted = conversation_store.delete(
        request.state.tenant_id,
        conversation_id,
        workspace_id=workspace_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {
        "status": "deleted",
        "conversation_id": conversation_id,
    }


@router.get("/conversations/{conversation_id}")
def get_conversation(request: Request, conversation_id: str):
    workspace_id = _get_workspace_id(request)

    conversation = conversation_store.get(
        request.state.tenant_id,
        conversation_id,
        workspace_id=workspace_id,
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return {
        **conversation,
        "messages": conversation_store.list_messages(
            request.state.tenant_id,
            conversation_id,
            workspace_id=workspace_id,
        ),
    }


@router.post("/ask")
def ask(request: Request, payload: ChatRequest):
    workspace_id = _get_workspace_id(request)
    conversation_id = payload.conversation_id

    if conversation_id is None:
        conversation = conversation_store.create(
            request.state.tenant_id,
            payload.question,
            workspace_id=workspace_id,
        )
        conversation_id = conversation["conversation_id"]

    elif conversation_store.get(
        request.state.tenant_id,
        conversation_id,
        workspace_id=workspace_id,
    ) is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    with trace("chat.ask", {"tenant_id": request.state.tenant_id}):
        result = rag_graph.invoke({
            "question": payload.question,
            "tenant_id": request.state.tenant_id,
            "workspace_id": workspace_id,
        })

    citations = result.get("citations", [])
    answer = result.get("answer", "")

    conversation_store.add_message(
        request.state.tenant_id,
        conversation_id,
        "user",
        payload.question,
    )

    conversation_store.add_message(
        request.state.tenant_id,
        conversation_id,
        "assistant",
        answer,
        json.dumps(citations),
    )

    return {
        "conversation_id": conversation_id,
        "answer": answer,
        "citations": citations,
    }
