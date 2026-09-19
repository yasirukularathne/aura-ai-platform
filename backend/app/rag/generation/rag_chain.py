from app.rag.retrieval.retriever import get_retriever
from app.rag.generation.llm import get_llm
from app.rag.generation.prompt import RAG_PROMPT


def format_documents(documents):

    formatted = []

    for document in documents:

        source = document.metadata.get("source", "unknown")
        page = document.metadata.get("page", None)

        formatted.append(
            f"""
Source: {source}
Page: {page}

Content:
{document.page_content}
"""
        )

    return "\n\n".join(formatted)


def ask_question(question: str):

    retriever = get_retriever()

    llm = get_llm()

    documents = retriever.invoke(question)

    context = format_documents(documents)

    prompt = RAG_PROMPT.format(
        context=context,
        question=question
    )

    response = llm.invoke(prompt)

    return {
        "answer": response.content,
        "sources": [
            {
                "source": doc.metadata.get("source"),
                "page": (
                    doc.metadata.get("page", 0) + 1
                    if isinstance(doc.metadata.get("page"), int)
                    else None
                ),
            }
            for doc in documents
        ]
    }