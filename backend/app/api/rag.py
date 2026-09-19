from fastapi import APIRouter
from pydantic import BaseModel

from app.rag.generation.rag_chain import ask_question


router = APIRouter(
    prefix="/api/rag",
    tags=["RAG"]
)


class QuestionRequest(BaseModel):
    question: str


@router.post("/ask")
def ask(request: QuestionRequest):

    result = ask_question(request.question)

    return result