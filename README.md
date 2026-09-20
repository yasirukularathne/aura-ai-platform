# AURA AI Platform

AURA is an evidence-grounded Retrieval-Augmented Generation (RAG) platform for asking questions over an organization's documents. The system parses source files, splits them into retrieval chunks, creates vector embeddings, stores them in Qdrant, retrieves relevant evidence, and sends that context to an LLM for answer generation.

The API returns both the generated answer and source metadata so responses can be traced back to the retrieved documents.

## Core Capabilities

- PDF document ingestion with page metadata
- Recursive document chunking with configurable size and overlap
- Hugging Face embeddings using `BAAI/bge-small-en-v1.5`
- Qdrant vector storage and semantic retrieval
- BM25 keyword retrieval and hybrid retrieval support
- Query analysis and optional query rewriting
- Evidence checks and safe fallback responses
- FastAPI endpoint for document-grounded questions
- LangGraph-based RAG agent orchestration

## Architecture

```text
Documents
		|
		v
PDF Loader -> Chunker -> Embeddings -> Qdrant
																			|
User Question -> Query Analysis ------+
										|
										v
						 Semantic / BM25 Retrieval
										|
										v
						 Evidence Validation
										|
										v
							LLM Answer Generation
										|
										v
					Answer + Source Metadata (API)
```

## Repository Layout

```text
backend/
	app/
		api/                 FastAPI route modules
		agents/              LangGraph RAG agent
		rag/
			embeddings/        Embedding model configuration
			generation/        Prompt and LLM integration
			ingestion/         PDF loading and chunking
			query/             Query analysis and rewriting
			retrieval/         Dense, BM25, hybrid, and index helpers
			security/          Evidence validation
			vectorstore/       Qdrant integration
	test_*.py              Pipeline and component checks
data/
	documents/             Source documents for ingestion
	datasets/              Evaluation datasets
	evaluation/            Evaluation outputs and assets
docs/                    Project documentation
frontend/                Frontend application
notebooks/               Experiments and analysis
scripts/                 Operational utilities
```

## Requirements

- Python 3.11 or newer
- A virtual environment for the backend
- A running Qdrant instance at `http://localhost:6333`
- A Groq API key for answer generation

## Local Setup

From the repository root on Windows PowerShell:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the backend dependencies used by the application:

```powershell
pip install fastapi uvicorn python-dotenv pypdf `
	langchain langchain-core langchain-community langchain-text-splitters `
	langchain-huggingface langchain-groq langchain-qdrant qdrant-client `
	sentence-transformers rank-bm25 langgraph
```

Create a `.env` file in the repository root:

```dotenv
GROQ_API_KEY=your_groq_api_key
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=aura_documents
```

Start Qdrant separately, then verify that it is reachable before indexing documents.

## Ingest Documents

Place PDFs in `data/documents/`. The current example document is:

```text
data/documents/company_policy.pdf
```

The ingestion flow is:

```python
from app.rag.ingestion.chunker import split_documents
from app.rag.ingestion.pdf_loader import load_pdf
from app.rag.vectorstore.qdrant_store import create_vector_store

documents = load_pdf("data/documents/company_policy.pdf")
chunks = split_documents(documents)
create_vector_store(chunks)
```

Run scripts from `backend` so the `app` package is importable:

```powershell
cd backend
python test_ingestion.py
```

## Run the API

From the `backend` directory:

```powershell
uvicorn app.main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

Health check:

```http
GET /health
```

Ask a question:

```http
POST /api/rag/ask
Content-Type: application/json

{
	"question": "What is the refund policy?"
}
```

Example response:

```json
{
  "answer": "...",
  "sources": [
    {
      "source": "data/documents/company_policy.pdf",
      "page": 2
    }
  ]
}
```

Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

## Testing

Install the test runner in the active virtual environment:

```powershell
pip install pytest
```

Run the backend tests:

```powershell
cd backend
python -m pytest -q
```

Tests are designed to cover ingestion, retrieval, generation, evidence checks, and agent orchestration. Tests that exercise external services should use mocks or a local service configuration.

## Development Notes

- Run Python commands from `backend` or use the backend interpreter explicitly.
- Do not commit `.env` files or API keys.
- Keep source metadata attached to every document chunk so answers remain traceable.
- Validate retrieved evidence before allowing an answer to be generated.
- Use dependency injection in tests to avoid requiring Qdrant or an LLM provider.

## Status

The core RAG backend and API foundation are implemented. Frontend integration, production deployment configuration, automated evaluation, and observability remain areas for continued development.
