from langchain_core.prompts import ChatPromptTemplate

from app.rag.generation.llm import get_llm


REWRITE_PROMPT = ChatPromptTemplate.from_template("""
Rewrite the user's question into a clear search query.

Rules:
- Preserve important technical terms.
- Preserve IDs, codes, names and numbers exactly.
- Do not add information that is not present.
- Return only the rewritten query.

User question:
{question}
""")


def rewrite_query(question: str):

    llm = get_llm()

    prompt = REWRITE_PROMPT.format(
        question=question
    )

    response = llm.invoke(prompt)

    return response.content.strip()