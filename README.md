# AURA AI Platform

> An evidence-based, security-aware RAG platform for reliable document question answering using hybrid retrieval, cross-encoder reranking, LangGraph orchestration, and grounded response generation.

AURA is a modular AI platform designed to explore how modern Retrieval-Augmented Generation (RAG) systems can be built beyond a basic **"PDF → embeddings → LLM"** pipeline.

The platform combines semantic retrieval, keyword search, cross-encoder reranking, evidence validation, prompt-injection protection, and agentic orchestration to produce answers grounded in retrieved documents.

---

## Overview

Traditional RAG applications often follow a simple pipeline:

```text
Documents
    ↓
Embeddings
    ↓
Vector Database
    ↓
LLM
    ↓
Answer
```

AURA extends this architecture with multiple retrieval and validation stages:

```text
                         ┌──────────────────────┐
                         │      User Query      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      FastAPI API     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    LangGraph Agent   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Security Gate     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Query Analysis    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                  ┌───────────────────────────────┐
                  │       Hybrid Retrieval        │
                  │                               │
                  │       Vector Search           │
                  │              +                │
                  │          BM25 Search          │
                  └───────────────┬───────────────┘
                                  │
                                  ▼
                         ┌──────────────────────┐
                         │   Cross-Encoder      │
                         │     Reranking        │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Evidence Check    │
                         └──────────┬───────────┘
                                    │
                           ┌────────┴────────┐
                           │                 │
                           ▼                 ▼
                   ┌──────────────┐   ┌──────────────┐
                   │   Generate   │   │ Safe Response│
                   │    Answer    │   │              │
                   └──────┬───────┘   └──────┬───────┘
                          │                   │
                          └─────────┬─────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     Final Answer     │
                         └──────────────────────┘
```

## Key Features

### 🔎 Hybrid Retrieval

AURA combines two retrieval strategies:

#### Semantic Retrieval

Uses vector embeddings with Qdrant to retrieve semantically related content.

**Current embedding model:**

```text
BAAI/bge-small-en-v1.5
```

#### Keyword Retrieval

Uses BM25 to identify documents containing relevant lexical terms.

The two result sets are combined and deduplicated before reranking.

```text
User Query
    │
    ├──────────────► Vector Search
    │
    └──────────────► BM25 Search
                         │
                         ▼
                   Combined Results
                         │
                         ▼
                     Deduplication
```

This allows AURA to benefit from both semantic similarity and exact keyword matching.

---

## Cross-Encoder Reranking

Initial retrieval provides candidate documents, but vector similarity alone does not always produce the most relevant ordering.

AURA therefore performs a second-stage reranking process using a CrossEncoder.

**Current model:**

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

### Pipeline

```text
Query
  ↓
Hybrid Retrieval
  ↓
Candidate Documents
  ↓
CrossEncoder
  ↓
Relevance Scores
  ↓
Top-K Documents
```

The reranker scores query-document pairs and sorts the retrieved evidence according to relevance.

---

## Evidence-Based Generation

AURA does not directly send every retrieved result to the LLM.

Before generation, the system evaluates the reranked evidence.

**Current evidence threshold:**

```text
minimum score = 0.20
```

Conceptually:

```text
Retrieved Evidence
       │
       ▼
Best Relevance Score
       │
       ├── Score ≥ threshold
       │        │
       │        ▼
       │   Generate Answer
       │
       └── Score < threshold
                │
                ▼
           Safe Response
```

If sufficient evidence is not available, the system can return a safe fallback instead of generating an unsupported answer.

This provides an additional control against unsupported responses.

---

## AI Security

AURA includes an input security layer designed to detect prompt-injection patterns before the query continues through the RAG pipeline.

```text
User Query
    │
    ▼
Security Detection
    │
    ├── Safe
    │    ↓
    │  Continue RAG Pipeline
    │
    └── Suspicious
         ↓
      Safe Response
```

This prevents detected malicious instructions from being passed directly through the normal retrieval and generation workflow.

---

## LangGraph Agent Architecture

The RAG workflow is implemented using LangGraph.

### Current Graph

```text
START
  │
  ▼
Security
  │
  ├──────────────► Safe Response
  │
  ▼
Query Analysis
  │
  ▼
Hybrid Retrieval
  │
  ▼
Reranking
  │
  ▼
Evidence Check
  │
  ├──────────────► Safe Response
  │
  ▼
Generation
  │
  ▼
END
```

This makes each stage explicit and allows conditional routing based on security and evidence state.

---

## Model Lifecycle Optimization

Machine-learning models can be expensive to initialize.

AURA therefore caches the embedding and reranking models using Python's `lru_cache`.

### Embedding Model

```python
@lru_cache(maxsize=1)
def get_embedding_model():
    ...
```

### Reranker Model

```python
@lru_cache(maxsize=1)
def get_reranker_model():
    ...
```

This ensures repeated requests within the same Python process reuse the loaded models instead of repeatedly initializing them.

Both caching mechanisms have been verified using instance-identity tests.

---

## Technology Stack

### Backend

- Python
- FastAPI
- LangChain
- LangGraph

### Retrieval

- Qdrant
- BM25
- Hugging Face Embeddings
- Sentence Transformers
- CrossEncoder

### AI / ML

- Hugging Face
- Groq
- PyTorch
- scikit-learn

### Infrastructure

- Docker
- Docker Compose
- Qdrant

### Testing

- Pytest

## Local Development

Copy `.env.example` to `.env`, then start the application and Qdrant:

```powershell
docker compose up --build
```

Set `API_KEY` in `.env`. API requests must include it as an `X-API-Key`
header. Never commit `.env` or real credentials.

The API is available at `http://localhost:8000`. Check the service endpoints:

```powershell
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

`/health/live` confirms that the API process is running. `/health/ready` confirms
that Qdrant is reachable and, when configured, PostgreSQL is accepting
connections. Run backend tests from the `backend` directory:

```powershell
.\venv\Scripts\python.exe -m pytest -q
```

Run the CI checks from the repository root:

```powershell
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python.exe -m pytest -q --cov=backend/app --cov-report=term-missing
.\backend\venv\Scripts\python.exe -m ruff check backend/app/config.py backend/app/logging_config.py backend/app/main.py backend/app/middleware.py backend/app/api/rag.py backend/tests
```

GitHub Actions runs these checks automatically for pushes to `main` and pull
requests.

The CI test suite under `backend/tests` is deterministic and does not require
Qdrant or an LLM. The older `backend/test_*.py` files are manual integration
demos that require the local services and should be run only after
`docker compose up`.

### Document ingestion

Authenticated clients can upload PDF, DOCX, TXT, Markdown, and CSV documents
for asynchronous indexing:

```powershell
curl -X POST http://localhost:8000/api/documents/upload `
  -H "X-API-Key: use-a-long-random-secret-value" `
  -F "file=@data/documents/company_policy.pdf"
```

The endpoint validates the extension, PDF signature when applicable, and
configured size limit (`MAX_UPLOAD_BYTES`, 10 MiB by default). Accepted files
are stored in `UPLOAD_DIR` and queued for format-specific loading, chunking,
embedding, and Qdrant indexing. Each job has a checksum, document ID, and
tenant/workspace metadata; uploading identical content for the same tenant
returns `409` instead of creating duplicate vectors.

The upload response includes a `job_id`. Poll its status with:

```powershell
curl http://localhost:8000/api/documents/<job_id> `
  -H "X-API-Key: use-a-long-random-secret-value"
```

Jobs move through `queued`, `processing`, `completed`, or `failed`. Failed jobs
include an error message and attempt count. Celery workers retry transient
storage and indexing failures with exponential backoff. Editors and admins can
retry a failed or completed job, which removes its previous vectors before indexing:

```powershell
curl -X POST http://localhost:8000/api/documents/<job_id>/reindex `
  -H "X-API-Key: use-a-long-random-secret-value"
```

List documents for the authenticated tenant:

```powershell
curl http://localhost:8000/api/documents `
  -H "X-API-Key: use-a-long-random-secret-value"
```

Editors and admins can delete a document. Deletion removes its stored file and
the matching Qdrant vectors:

```powershell
curl -X DELETE http://localhost:8000/api/documents/<job_id> `
  -H "X-API-Key: use-a-long-random-secret-value"
```

### Tenant isolation

### RAG evaluation

A fixed regression dataset is stored at
`backend/data/evaluation/rag_eval.json`. It covers grounded answers,
retrieval targets, citation source/page correctness, and safe abstention.

Run the repeatable evaluation command from the repository root:

```powershell
Set-Location backend
py -3.11 -m app.evaluation.cli
```

Each run evaluates the live RAG graph and stores an immutable JSON report under
`backend/data/evaluation/results/`, while `latest.json` points to the newest
result. Reports include Recall@K, Precision@K, MRR, hit rate, lexical
faithfulness, answer relevance, required-term coverage, citation correctness,
and abstention accuracy.

### Production architecture

Local development keeps SQLite and local file storage as fallbacks. Production
services are enabled with environment variables:

- `DATABASE_URL` points to PostgreSQL. Run
  `py -3.11 backend/scripts/migrate_postgres.py` during deployment. When set,
  API keys, rate limits, audit events, conversations, messages, and ingestion
  jobs use PostgreSQL. SQLite remains the explicit fallback when it is empty.
- `STORAGE_BACKEND=s3` enables S3 or S3-compatible object storage using
  `S3_BUCKET`, `S3_REGION`, and credentials. Local temporary files remain
  available to the ingestion worker until indexing completes.
- `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` enable Redis/Celery
  ingestion workers; without them FastAPI background tasks remain the fallback.
- `POST /api/chat/stream` returns Server-Sent Events with `answer`,
  `citations`, and `done` events.
- `/metrics` is Prometheus-compatible. Compose includes Prometheus and Grafana
  with a provisioned Prometheus data source.
- Langfuse tracing is enabled when `LANGFUSE_PUBLIC_KEY` and
  `LANGFUSE_SECRET_KEY` are configured.

The local Compose stack includes PostgreSQL, Redis, a Celery worker, Qdrant,
Prometheus, and Grafana. AWS deployment uses the ECS task definition in
`infrastructure/aws/ecs-task-definition.json` and the
`.github/workflows/deploy-aws.yml` workflow. Configure the repository
variables `AWS_REGION`, `ECR_REPOSITORY`, `ECS_CLUSTER`, and `ECS_SERVICE`,
plus the `AWS_DEPLOY_ROLE_ARN` secret using GitHub OIDC.

The configured `API_KEY` is associated with `TENANT_ID`. Uploaded documents
and ingestion jobs are stored with that tenant ID, and job status requests only
return records belonging to the authenticated tenant. Clients cannot select a
tenant by sending a request header.

Conversation history is also tenant-scoped. The chat API supports listing,
renaming, and deleting conversations:

```powershell
curl http://localhost:8000/api/chat/conversations `
  -H "X-API-Key: use-a-long-random-secret-value"

curl -X PATCH http://localhost:8000/api/chat/conversations/<conversation_id> `
  -H "X-API-Key: use-a-long-random-secret-value" `
  -H "Content-Type: application/json" `
  -d '{"title":"Updated title"}'
```

### API key administration

The bootstrap `API_KEY` is inserted into SQLite as a hash. Raw API keys are
never stored; Argon2 is used for slow password-style hashing. Keys expire by
default after `API_KEY_TTL_DAYS` days and admins can rotate them. An admin can
create a scoped key and receives the raw value only once:

```powershell
curl -X POST http://localhost:8000/api/admin/api-keys `
  -H "X-API-Key: your-admin-key" `
  -H "Content-Type: application/json" `
  -d '{\"role\":\"viewer\"}'
```

Revoke a key with:

```powershell
curl -X DELETE http://localhost:8000/api/admin/api-keys/<key_id> `
  -H "X-API-Key: your-admin-key"
```

Role permissions are enforced: `viewer` can read job status, `editor` can
upload documents, and `admin` can upload, manage API keys, and read audit
events. Security-sensitive actions are stored in the `audit_events` table.

### Rate limits

Authenticated API keys have SQLite-backed fixed-window limits. Defaults are 60
requests per minute for general API calls, 30 for AI endpoints, and 10 for
uploads. Configure them with `API_RATE_LIMIT_PER_MINUTE`,
`AI_RATE_LIMIT_PER_MINUTE`, and `UPLOAD_RATE_LIMIT_PER_MINUTE`. Exceeded limits
return HTTP `429` with a `Retry-After` header.

When `REDIS_URL` is configured, rate-limit counters use Redis so multiple
backend instances share the same windows. Without Redis, the SQLite counter is
used as a local-development fallback.

### Observability

Prometheus-compatible request metrics are available at:

```powershell
curl http://localhost:8000/metrics
```

The endpoint reports process uptime, request counts by method/path/status, and
total request duration. Paths containing UUID resource IDs are normalized to
avoid unbounded metric label cardinality.

### Frontend dashboard

The dependency-free dashboard is in [frontend](./frontend). Serve it locally:

```powershell
python -m http.server 5500 --directory frontend
```

Open `http://localhost:5500`, enter the API URL and API key, then use the
upload, chat, job-status, and metrics panels. Configure `CORS_ORIGINS` when
hosting the dashboard on another origin. The dashboard keeps the API key only
in session storage and does not persist it across browser sessions.
Chat conversations and messages are persisted server-side per tenant; the
conversation ID is kept in session storage by the dashboard.

The churn prediction endpoint is optional. It requires
`models/churn_model.joblib` and `models/churn_preprocessor.joblib`; without
those trained artifacts, the backend starts normally and
`POST /api/ml/churn` returns `503`.

---

## Project Structure

```text
aura-ai-platform/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── agents/
│   │   │   └── rag_agent.py
│   │   │
│   │   ├── api/
│   │   │   └── rag.py
│   │   │
│   │   ├── rag/
│   │   │   │
│   │   │   ├── embeddings/
│   │   │   │   └── embedding_model.py
│   │   │   │
│   │   │   ├── ingestion/
│   │   │   │   └── pdf_loader.py
│   │   │   │
│   │   │   ├── retrieval/
│   │   │   │   ├── retriever.py
│   │   │   │   ├── bm25_retriever.py
│   │   │   │   └── hybrid.py
│   │   │   │
│   │   │   ├── reranking/
│   │   │   │   └── reranker.py
│   │   │   │
│   │   │   └── vectorstore/
│   │   │       └── qdrant_store.py
│   │   │
│   │   ├── security/
│   │   │   └── input_guard.py
│   │   │
│   │   └── config.py
│   │
│   ├── tests/
│   │   ├── test_rag.py
│   │   ├── test_security.py
│   │   └── test_evaluation.py
│   │
│   └── requirements.txt
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## RAG Pipeline

The complete request lifecycle is:

```text
POST /api/rag/ask
        │
        ▼
Input Validation
        │
        ▼
Security Detection
        │
        ▼
Query Analysis
        │
        ▼
   ┌────┴───────┐
   │            │
   ▼            ▼
Vector        BM25
Search        Search
   │            │
   └─────┬──────┘
         │
         ▼
    Result Fusion
         │
         ▼
   CrossEncoder
    Reranking
         │
         ▼
   Evidence Check
         │
      ┌──┴───┐
      │      │
      ▼      ▼
  Generate  Safe
   Answer   Response
```

---

## API

### Ask a Question

```text
POST /api/rag/ask
```

### Example Request

```json
{
  "question": "What is the notice period for managers and supervisors?"
}
```

### Example Response

```json
{
  "answer": "The notice period is ...",
  "sources": [
    {
      "source": "company_policy.pdf",
      "page": 30
    }
  ]
}
```

The exact response fields may evolve as the API continues to be hardened.

---

## Running Locally

### 1. Clone the Repository

```bash
git clone https://github.com/yasirukularathne/aura-ai-platform.git
cd aura-ai-platform
```

### 2. Create a Virtual Environment

#### Windows

```bash
python -m venv backend/venv
```

### Activate

```bash
backend\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create:

```text
.env
```

Example:

```env
GROQ_API_KEY=your_api_key

QDRANT_URL=http://localhost:6333

QDRANT_COLLECTION_NAME=aura_documents
```

Do not commit `.env` to version control.

### Start Qdrant

From the project root:

```bash
docker compose up -d
```

Qdrant will be available at:

```text
http://localhost:6333
```

### Start the Backend

From:

```text
backend/
```

Run:

```bash
uvicorn app.main:app --reload
```

The API will be available through the configured FastAPI server.

---

## Testing

AURA uses Pytest for automated testing.

Run:

```bash
pytest -q
```

### Current Verified Test Status

```text
9 passed
```

The test suite covers the implemented RAG, security, and evaluation functionality.

The current test run also reports a deprecation warning related to the `langchain-community` PDF loader dependency. This is tracked as technical debt rather than a test failure.

---

## Engineering Principles

AURA is being developed around several engineering principles.

### 1. Grounded Generation

The system should prefer retrieved evidence over unsupported model knowledge.

### 2. Defense in Depth

Security and evidence validation are separate controls.

```text
Input Security
      +
Retrieval
      +
Reranking
      +
Evidence Validation
      +
Grounded Generation
```

### 3. Modular Architecture

Major components are separated into independent modules so they can be tested and replaced independently.

### 4. Explicit Agent Workflow

LangGraph is used to represent the RAG workflow as explicit nodes and conditional transitions.

### 5. Performance Awareness

Expensive ML models are cached and reused within the application process.

### 6. Test Before Refactoring

Changes to the RAG architecture are validated using automated tests before being merged.

---

## Why AURA?

AURA is designed as an engineering-focused exploration of modern AI application architecture.

Rather than treating an LLM as the entire system, the platform separates:

```text
Retrieval
    +
Ranking
    +
Security
    +
Evidence Validation
    +
Generation
    +
Agent Orchestration
```

This architecture makes it possible to independently evaluate and improve different stages of an AI application.

---

## Project Goals

The main goals of AURA are to explore and demonstrate:

- Modern RAG architecture
- Hybrid information retrieval
- Neural reranking
- Agentic AI workflows
- AI application security
- Evidence-grounded generation
- Model lifecycle optimization
- Automated evaluation
- Production-oriented AI engineering

---

## Author

**Yasiru Kularathne**

Computer Engineering graduate
University of Ruhuna, Sri Lanka

### Areas of Interest

- Artificial Intelligence
- Machine Learning
- Generative AI
- Retrieval-Augmented Generation
- AI Agents
- Natural Language Processing
- Backend Engineering

### Links

**GitHub:**
https://github.com/yasirukularathne

**LinkedIn:**
https://www.linkedin.com/in/yasiru-kularathne-79a911213/

---

## License

This project is currently developed as a personal AI engineering and research project.
