from pathlib import Path

from app.rag.ingestion.pdf_loader import load_pdf
from app.rag.ingestion.chunker import split_documents
from app.rag.vectorstore.qdrant_store import create_vector_store


PDF_PATH = Path(__file__).resolve().parents[1] / "data" / "documents" / "company_policy.pdf"


print("Loading PDF...")

documents = load_pdf(PDF_PATH)

print(f"Loaded {len(documents)} pages")


print("Splitting documents...")

chunks = split_documents(documents)

print(f"Created {len(chunks)} chunks")


print("Creating embeddings and storing in Qdrant...")

vector_store = create_vector_store(chunks)

print("Documents successfully indexed!")
