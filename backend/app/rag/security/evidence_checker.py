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