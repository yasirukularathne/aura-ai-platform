def check_evidence(documents):

    if not documents:
        return {
            "sufficient": False,
            "reason": "No relevant documents were retrieved."
        }

    valid_documents = [
        document
        for document in documents
        if document.page_content.strip()
    ]

    if not valid_documents:
        return {
            "sufficient": False,
            "reason": "Retrieved documents contain no usable text."
        }

    return {
        "sufficient": True,
        "reason": "Relevant evidence was retrieved."
    }

def check_reranked_evidence(
    reranked_documents,
    minimum_score=0.20
):

    if not reranked_documents:

        return {
            "sufficient": False,
            "score": 0.0,
            "reason": "No relevant evidence was retrieved."
        }

    best_score = max(
        item["score"]
        for item in reranked_documents
    )

    sufficient = best_score >= minimum_score

    return {
        "sufficient": sufficient,
        "score": float(best_score),
        "reason": (
            "Relevant evidence found."
            if sufficient
            else "Retrieved evidence is not sufficiently relevant."
        )
    }