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
