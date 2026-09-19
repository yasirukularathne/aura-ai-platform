from app.rag.ingestion.pdf_loader import load_pdf
from app.rag.ingestion.chunker import split_documents


documents = load_pdf("../data/documents/company_policy.pdf")

chunks = split_documents(documents)

print(f"Pages: {len(documents)}")
print(f"Chunks: {len(chunks)}")

for i, chunk in enumerate(chunks[:5]):
    print(f"\n--- CHUNK {i} ---")
    print(chunk.page_content[:300])
    print(chunk.metadata)