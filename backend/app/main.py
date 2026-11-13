import logging

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.ml import router as ml_router
from app.api.rag import router as rag_router
from app.api.streaming import router as streaming_router
from app.api.workspaces import router as workspaces_router
from app.config import settings
from app.database import check_database
from app.logging_config import configure_logging
from app.metrics import metrics
from app.middleware import ApiKeyMiddleware, RequestContextMiddleware
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from qdrant_client import QdrantClient

configure_logging()

app = FastAPI(
    title=settings.app_name,
    description="AI Unified Reasoning & Analytics Platform",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "X-Workspace-ID",
    ],
)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(ApiKeyMiddleware)

app.include_router(rag_router)
app.include_router(ml_router)
app.include_router(documents_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(streaming_router)
app.include_router(workspaces_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Request validation failed",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID", "unknown")
    logging.getLogger("aura.api").exception(
        "request_failed",
        extra={"request_id": request_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.get("/", tags=["System"])
def root():
    return {
        "project": "AURA",
        "message": "AI Platform is running",
    }


@app.get("/health/live", tags=["System"])
def liveness():
    return {
        "status": "healthy",
    }


@app.get("/health/ready", tags=["System"])
def readiness():
    """Report whether required runtime dependencies are reachable."""
    dependencies = {}

    try:
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=2,
        )
        client.get_collections()
    except Exception as exc:
        return {
            "status": "not_ready",
            "dependencies": {"qdrant": "unavailable"},
            "detail": str(exc),
        }

    dependencies["qdrant"] = "available"

    try:
        check_database()
        dependencies["database"] = "available"
    except Exception as exc:
        return {
            "status": "not_ready",
            "dependencies": {**dependencies, "database": "unavailable"},
            "detail": str(exc),
        }

    return {
        "status": "ready",
        "dependencies": dependencies,
    }


@app.get("/health", tags=["System"], include_in_schema=False)
def health():
    return liveness()


@app.get("/metrics", tags=["System"], include_in_schema=False)
def metrics_endpoint():
    return PlainTextResponse(
        metrics.render(),
        media_type="text/plain; version=0.0.4",
    )