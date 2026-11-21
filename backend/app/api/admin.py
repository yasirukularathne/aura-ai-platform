from datetime import UTC, datetime, timedelta
from typing import Literal

from app.auth import ApiKeyStore, require_role
from app.config import settings
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/admin", tags=["Administration"])
key_store = ApiKeyStore(settings.database_path)


class ApiKeyCreateRequest(BaseModel):
    role: Literal["viewer", "editor", "admin"] = "viewer"
    expires_in_days: int = Field(default=90, ge=1, le=3650)


@router.post("/api-keys", status_code=201)
def create_api_key(request: Request, payload: ApiKeyCreateRequest):
    require_role(request, "admin")

    expires_at = (
        datetime.now(UTC) + timedelta(days=payload.expires_in_days)
    ).isoformat()
    key_id, raw_key = key_store.create(
        request.state.tenant_id,
        payload.role,
        expires_at,
    )
    key_store.audit(
        request.state.tenant_id,
        request.state.key_id,
        "api_key.create",
        key_id,
        payload.role,
    )
    return {
        "key_id": key_id,
        "api_key": raw_key,
        "tenant_id": request.state.tenant_id,
        "role": payload.role,
        "expires_at": expires_at,
        "warning": "Store this API key securely; it cannot be retrieved later.",
    }


@router.delete("/api-keys/{key_id}")
def revoke_api_key(request: Request, key_id: str):
    require_role(request, "admin")

    if not key_store.revoke(request.state.tenant_id, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    key_store.audit(
        request.state.tenant_id,
        request.state.key_id,
        "api_key.revoke",
        key_id,
    )
    return {"status": "revoked", "key_id": key_id}


@router.post("/api-keys/{key_id}/rotate")
def rotate_api_key(request: Request, key_id: str):
    require_role(request, "admin")
    rotated = key_store.rotate(request.state.tenant_id, key_id)
    if rotated is None:
        raise HTTPException(status_code=404, detail="API key not found")
    _, raw_key = rotated
    key_store.audit(
        request.state.tenant_id,
        request.state.key_id,
        "api_key.rotate",
        key_id,
    )
    return {
        "key_id": key_id,
        "api_key": raw_key,
        "warning": "Store this API key securely; it cannot be retrieved later.",
    }


@router.get("/audit")
def list_audit_events(request: Request):
    require_role(request, "admin")
    return {"events": key_store.list_audit_events(request.state.tenant_id)}