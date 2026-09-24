from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.rag_agent import rag_graph


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"]
)


class QuestionRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(request: QuestionRequest):

    result = rag_graph.invoke({"question": request.question})

    return result
