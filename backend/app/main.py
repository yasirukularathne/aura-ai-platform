from fastapi import FastAPI

from app.api.rag import router as rag_router


app = FastAPI(
    title="AURA AI Platform",
    description="AI Unified Reasoning & Analytics Platform",
    version="0.1.0"
)


app.include_router(rag_router)


@app.get("/")
def root():
    return {
        "project": "AURA",
        "message": "AI Platform is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }