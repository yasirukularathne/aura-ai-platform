from app.security.input_guard import detect_prompt_injection


def scan_document_chunks(documents):

    safe_documents = []
    suspicious_documents = []

    for document in documents:

        result = detect_prompt_injection(
            document.page_content
        )

        if result["blocked"]:

            suspicious_documents.append({
                "document": document,
                "matches": result["matches"]
            })

        else:

            safe_documents.append(document)

    return {
        "safe_documents": safe_documents,
        "suspicious_documents": suspicious_documents
    }