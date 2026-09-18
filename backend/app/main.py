from fastapi import FastAPI

app = FastAPI(
    title="AURA AI Platform",
    description="AI Unified Reasoning & Analytics Platform",
    version="0.1.0"
)


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