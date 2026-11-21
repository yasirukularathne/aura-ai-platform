import logging
import time
import uuid

from app.auth import ApiKeyStore
from app.config import settings
from app.metrics import metrics
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("aura.api")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        started = time.perf_counter()

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        metrics.record_request(
            request.method,
            request.url.path,
            response.status_code,
            duration_ms / 1000,
        )

        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.key_store = ApiKeyStore(settings.database_path)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        if not settings.api_key and not request.headers.get("X-API-Key"):
            return JSONResponse(
                status_code=503,
                content={"detail": "API authentication is not configured"},
            )

        supplied_key = request.headers.get("X-API-Key", "")
        identity = self.key_store.authenticate(supplied_key)
        if identity is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )

        request.state.tenant_id = identity["tenant_id"]
        request.state.role = identity["role"]
        request.state.key_id = identity["key_id"]

        bucket = "api"
        limit = settings.api_rate_limit_per_minute
        if request.url.path.startswith("/api/documents/upload"):
            bucket = "uploads"
            limit = settings.upload_rate_limit_per_minute
        elif request.url.path.startswith(("/api/rag", "/api/ml")):
            bucket = "ai"
            limit = settings.ai_rate_limit_per_minute

        allowed, retry_after = self.key_store.consume_rate_limit(
            identity["key_id"],
            bucket,
            limit,
        )
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded", "bucket": bucket},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
