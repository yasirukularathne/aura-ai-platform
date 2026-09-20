from app.rag.ingestion.pdf_loader import load_pdf
from app.rag.ingestion.chunker import split_documents


def load_and_chunk_document(file_path: str):

    documents = load_pdf(file_path)

    chunks = split_documents(documents)

    return chunks