from pydantic import BaseModel, Field


class RAGResponse(BaseModel):

    answer: str = Field(
        min_length=1
    )

    citations: list[dict] = []

    confidence: float = Field(
        ge=0.0,
        le=1.0
    )


def validate_output(
    answer: str,
    citations: list[dict],
    confidence: float = 0.0
):

    return RAGResponse(
        answer=answer,
        citations=citations,
        confidence=confidence
    )