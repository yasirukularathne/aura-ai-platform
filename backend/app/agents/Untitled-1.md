AURA AI — Complete Final-Year / Portfolio Project Specification
AURA (Advanced Unified Retrieval & AI Assistant) should be developed as a production-oriented AI platform that can ingest private knowledge, retrieve relevant evidence, answer questions with citations, perform specialized AI tasks, and expose everything through secure APIs and a web interface.

The goal is not simply to build a chatbot. It is to demonstrate that you can engineer a complete AI system: data pipelines, embeddings, vector databases, retrieval, LLM orchestration, evaluation, security, monitoring, and deployment.







ibrahimstouri.com


AURA AI
Evidence-grounded AI platform with RAG, intelligent agents, and ML analytics
Core: RAG
LangGraph agents
FastAPI
Qdrant
LLMOps


1. Project vision
AURA should allow an organization or individual to upload knowledge sources and interact with them through an AI assistant.

For example, a user uploads:
- Company policies and procedures.
- Technical documentation.
- Research papers and reports.
- PDF, DOCX, TXT, Markdown and CSV files.
- Approved web pages and knowledge sources.
AURA processes those documents, indexes them, and allows users to ask questions such as:
- "What is our employee leave policy?"
- "Summarize the security requirements in these documents."
- "Compare the two uploaded technical reports."
- "Where does the documentation explain authentication?"
- "What evidence supports this answer?"
AURA should answer using retrieved evidence, show document citations, and abstain when the available information is insufficient.
2. Complete feature set
I recommend organizing AURA into ten major modules.
AURA platform architecture
Frontend — Next.js

Chat · Documents · Analytics · Admin · Settings


API Gateway — FastAPI

Authentication · Validation · Rate limits · API routing


RAG Engine

Ingestion · Chunking · Embeddings · Retrieval · Reranking · Generation


Agent Engine

Supervisor · RAG · ML · Verification · Response


ML Engine

Prediction · Classification · Explainability


Security & Evaluation

Guardrails · Testing · Metrics · Monitoring




Data & Infrastructure Layer

Qdrant · PostgreSQL · Redis · Object Storage · Docker


Module 1 — Document ingestion and knowledge management
This is the entry point of the RAG system.

Functions
Function	What it does
Upload documents	Accept PDF, DOCX, TXT, MD and CSV
Batch upload	Upload multiple files together
Document validation	Check file type, size and integrity
Text extraction	Extract text and metadata
OCR support	Extract text from scanned PDFs and images
URL ingestion	Import content from permitted web pages
Document preview	Show extracted content before indexing
Metadata extraction	Store title, source, author, date and page
Document versioning	Track updated versions
Duplicate detection	Avoid indexing identical content twice
Delete documents	Remove source and its indexed chunks
Re-index documents	Reprocess after changing extraction or chunking settings
Ingestion status	Show uploaded, processing, indexed or failed

Important: Document processing should run as a background job. Large uploads should not keep the user's HTTP request waiting.
Module 2 — Text processing and chunking
After extraction, AURA prepares text for retrieval.

Functions
- Text cleaning and normalization.
- Remove unnecessary whitespace and repeated headers.
- Split content into chunks.
- Support fixed-size and recursive chunking.
- Support token-aware chunking.
- Configure chunk size and overlap.
- Preserve page numbers and source metadata.
- Preserve document and section relationships.
- Handle tables and structured content where possible.
- Track chunk IDs and document IDs.
Suggested initial settings:
Setting	Starting value
Chunk size	700 tokens
Chunk overlap	100 tokens
Retrieval top-K	10
Reranking top-K	5

These are starting values, not universal optimums. Tune them using an evaluation dataset.
Module 3 — Embedding and vector database
This module converts document chunks into numerical representations and stores them.

Embedding model

BAAI/bge-small-en-v1.5

Functions:
- Generate embeddings for document chunks.
- Generate query embeddings.
- Batch embedding generation.
- Normalize embeddings where appropriate.
- Store embedding model and version information.
- Re-embed documents when the model changes.
Vector database

Qdrant should be AURA's primary vector store.







qdrant.tech


Functions:
- Create and manage collections.
- Insert and update vectors.
- Perform semantic similarity searches.
- Filter by document, user, workspace and metadata.
- Delete vectors when documents are removed.
- Support collection configuration and indexing.
- Configure local development and secured production connections.
Do not hard-code Qdrant credentials or URLs. Use environment variables and secure configuration.
Module 4 — Advanced retrieval engine
This should be one of AURA's strongest technical components.

AURA should not rely only on basic vector similarity.
Retrieval method	Purpose
Dense retrieval	Finds semantically similar content
Sparse retrieval	Finds keyword and exact-term matches
BM25	Traditional lexical ranking
Hybrid retrieval	Combines dense and sparse results
Metadata filtering	Restricts results to relevant sources
RRF	Combines rankings from different retrievers
Query rewriting	Improves ambiguous or short questions
Multi-query retrieval	Generates alternative search queries
Context compression	Reduces irrelevant retrieved text

Recommended retrieval pipeline:
User question

Query transformation

Dense search

Qdrant


Sparse search

BM25



Hybrid fusion — RRF

Cross-encoder reranking

Evidence selection


Module 5 — RAG generation and answer verification
This is where AURA uses an LLM to generate answers based on retrieved content.

Functions
- Construct prompts using retrieved evidence.
- Generate answers through Groq-hosted LLMs.
- Include source references and page numbers.
- Provide inline citations.
- Distinguish supported facts from unsupported assumptions.
- Detect insufficient evidence.
- Abstain rather than invent answers.
- Support configurable response length.
- Support conversation context.
- Stream generated responses.
- Return the evidence used for the answer.
Critical rule: The LLM must treat uploaded documents as untrusted data, not as instructions. Retrieved text must not be allowed to override AURA's system instructions.

Example response:
AURA Assistant
Evidence supported

The employee leave policy provides 14 days of annual leave for eligible employees.

Sources
Employee_Handbook.pdf

Page 12 · Relevant passage

"Eligible employees are entitled to 14 days of annual leave..."

Answer grounded in retrieved evidence


Module 6 — LangGraph multi-agent system
Use LangGraph for orchestration.

Do not create many agents simply to make the project look advanced. Each agent should have a clear responsibility and measurable purpose.
Agent	Responsibility
Supervisor agent	Understands the request and chooses a workflow
RAG agent	Searches knowledge and answers from documents
ML agent	Runs supported prediction and classification tasks
Analytics agent	Summarizes usage and system analytics
Verification agent	Checks whether answers are supported by evidence
Response agent	Formats the final response and citations

Example workflow
1. User asks a question.
2. Supervisor classifies the request.
3. Supervisor routes it to the appropriate agent.
4. RAG agent retrieves relevant evidence, or ML agent runs a supported model.
5. Verification agent checks the result.
6. Response agent returns a structured response.
Use LangGraph state, conditional routing, retries, timeouts, and explicit error handling. Avoid uncontrolled autonomous loops.
Module 7 — Machine learning intelligence
AURA can include an ML module to demonstrate that it is more than a document chatbot.

I recommend one well-developed, explainable ML use case rather than several unfinished models.

Recommended demonstration: Customer churn prediction

Functions:
- Upload structured CSV datasets.
- Validate columns and data types.
- Handle missing values.
- Perform preprocessing.
- Train a classification model.
- Evaluate model performance.
- Generate predictions.
- Explain predictions with SHAP.
- Show feature importance.
- Store model versions and evaluation results.
Suggested technologies:
- scikit-learn
- XGBoost
- pandas
- SHAP
This is a demonstration module, not a claim that AURA already has a trained production churn model. Clearly separate ML predictions from facts retrieved through RAG.
Module 8 — Conversation and memory management
Functions:
- Create conversations.
- Retrieve conversation history.
- Rename and delete conversations.
- Maintain context across turns.
- Support conversation-specific document context.
- Store conversation metadata.
- Provide configurable conversation memory.
- Allow users to clear conversation memory.
- Prevent one user's private conversation or documents from leaking to another.
Use PostgreSQL for persistent conversation data. Avoid blindly sending the entire chat history to the LLM; use bounded context or summarization.
Module 9 — Security and responsible AI
This is essential for a production-oriented AI portfolio project.
Security feature	Requirement
Authentication	Secure login and token-based sessions
Authorization	Role-based access control
Workspace isolation	Separate tenant/user data
File validation	File size, MIME and extension checks
API protection	Rate limits and request validation
Secrets management	Environment variables and secret storage
Prompt injection defense	Treat retrieved content as untrusted
Output validation	Validate structured model responses
Audit logs	Record important user and admin actions
Data deletion	Remove original files and indexed content
Error handling	Avoid exposing secrets and stack traces

Add tests for cross-user document access, malicious document instructions, unauthorized API calls, and deletion consistency.
Module 10 — Evaluation, observability and LLMOps
This is one of the most important differentiators between a demo and an engineered AI system.

RAG evaluation

Use:
- RAGAS.
- Recall@K.
- Precision@K.
- Mean Reciprocal Rank (MRR).
- Faithfulness.
- Answer relevance.
- Context precision and recall.
- Citation correctness.
Observability
- Track request latency.
- Track retrieval latency.
- Track LLM response latency.
- Track token usage and model costs.
- Track failed ingestion jobs.
- Track API errors.
- Track retrieval quality.
- Log trace IDs across workflows.
Suggested tools:
- Langfuse.
- Prometheus.
- Grafana.
- Python structured logging.
Important: Build a fixed test dataset with questions, expected answers and supporting document passages. Compare your RAG versions against the same dataset.

3. Frontend — what the AURA application should look like
The frontend should be a complete AI workspace, not just a chat window.









1. AI Chat Workspace
- Chat interface and streaming responses.
- Source citations and evidence panel.
- Conversation history.
- Document/workspace selection.
- Copy, regenerate and provide feedback.












2. Knowledge Base
- Upload and manage documents.
- Document processing status.
- Preview extracted content.
- Search documents.
- Re-index, delete and view metadata.












3. Analytics Dashboard
- Total documents and indexed chunks.
- Questions and active users.
- Retrieval and response latency.
- Token consumption and estimated cost.
- Failed ingestion jobs and API errors.












4. Evaluation Dashboard
- RAG evaluation runs.
- Faithfulness and relevance.
- Recall@K and MRR.
- Model and prompt comparisons.
- Historical evaluation results.












5. Administration and Settings
- User and role management.
- Workspace settings.
- Model configuration.
- Embedding and retrieval settings.
- Security and audit logs.



Other screens to include
- Login and registration.
- Forgot/reset password.
- New workspace and workspace settings.
- ML prediction interface.
- Model details and explainability.
- Agent execution/trace view.
- Profile and preferences.
- API health/status page.
4. Backend API — complete endpoint specification
Use FastAPI with versioned endpoints under /api/v1.
Module	Endpoint	Purpose
Auth	POST /auth/register	Register
Auth	POST /auth/login	Authenticate
Auth	POST /auth/refresh	Refresh session
Users	GET /users/me	Current user
Documents	POST /documents/upload	Upload file
Documents	GET /documents	List documents
Documents	GET /documents/{id}	Document details
Documents	DELETE /documents/{id}	Delete document
Documents	POST /documents/{id}/reindex	Reprocess
Ingestion	GET /ingestion/jobs/{id}	Job status
Chat	POST /chat	Ask a question
Chat	POST /chat/stream	Stream a response
Chat	GET /conversations	List conversations
Chat	GET /conversations/{id}	Conversation history
Chat	DELETE /conversations/{id}	Delete conversation
Retrieval	POST /retrieval/search	Test retrieval
Agents	POST /agents/run	Run an agent workflow
ML	POST /ml/predict	Make predictions
ML	POST /ml/train	Start training job
Evaluation	POST /evaluation/run	Start evaluation
Evaluation	GET /evaluation/results	View results
Analytics	GET /analytics/overview	Dashboard metrics
System	GET /health	Health check
System	GET /ready	Readiness check

For the chat endpoint, return more than a plain string. A structured response should contain:
- Answer.
- Citations.
- Retrieved source passages.
- Conversation ID.
- Model and retrieval metadata.
- Latency and token usage where available.
- An indication of whether the evidence was sufficient.
For streaming, use Server-Sent Events or another clearly defined streaming protocol. Keep the ordinary request/response endpoint as well.
5. Recommended technology stack
This is the stack I would choose for AURA. It is ambitious enough to demonstrate AI engineering but still manageable for one developer.
Layer	Technology	Responsibility
Frontend	Next.js, TypeScript	Web application
UI	Tailwind CSS, component library	Interface
Backend	Python, FastAPI	API services
AI orchestration	LangChain, LangGraph	RAG and agents
LLM	Groq API	Language generation
Embeddings	Hugging Face, BGE	Text embeddings
Vector DB	Qdrant	Vector search
Sparse retrieval	BM25	Keyword search
Reranking	Cross-Encoder	Relevance ranking
Main database	PostgreSQL	Users, documents, chats
Cache	Redis	Cache and job coordination
Background jobs	Celery or RQ	Document processing
File storage	S3-compatible object storage	Original files
ML	scikit-learn, XGBoost	Prediction
Explainability	SHAP	Model interpretation
Evaluation	RAGAS, custom metrics	RAG quality
Observability	Langfuse	LLM traces
Metrics	Prometheus, Grafana	Infrastructure metrics
Testing	pytest, HTTPX	Backend tests
Containers	Docker, Docker Compose	Local and production services
CI/CD	GitHub Actions	Automated testing and deployment
Reverse proxy	Nginx	Routing and TLS termination
Cloud	AWS	Production hosting

Avoid adding every technology immediately. Kafka, Kubernetes, multiple databases, and complex microservices are not required for a strong first production version. Add them only when there is a demonstrated need.
6. Data model and database design
PostgreSQL should store the application data. Qdrant should store vectors and retrieval payloads. Original documents should live in object storage.
Table	Important fields
users	id, email, password_hash, role, created_at
workspaces	id, name, owner_id, created_at
workspace_members	workspace_id, user_id, role
documents	id, workspace_id, filename, storage_key, status, checksum
document_versions	id, document_id, version, created_at
document_chunks	id, document_id, chunk_index, page_number, content_hash
ingestion_jobs	id, document_id, status, error, started_at, completed_at
conversations	id, user_id, workspace_id, title
messages	id, conversation_id, role, content, created_at
message_citations	message_id, chunk_id, relevance_score
evaluation_runs	id, dataset_id, model, metrics, created_at
ml_models	id, model_name, version, artifact_key, metrics
audit_logs	id, user_id, action, resource_id, created_at

Qdrant payloads should include fields such as:
{
  "chunk_id": "chunk_001",
  "document_id": "doc_001",
  "workspace_id": "workspace_001",
  "page_number": 12,
  "source": "employee_handbook.pdf",
  "chunk_index": 4,
  "embedding_model": "BAAI/bge-small-en-v1.5"
}


The workspace and user access rules must be applied during retrieval, not just in the frontend.
7. Recommended backend project structure
This is a target structure. It should be reconciled with your existing AURA repository rather than imposed on top of it.
aura-ai-platform/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── logging.py
│   │   │
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── documents.py
│   │   │       ├── chat.py
│   │   │       ├── agents.py
│   │   │       ├── retrieval.py
│   │   │       ├── ml.py
│   │   │       ├── evaluation.py
│   │   │       └── analytics.py
│   │   │
│   │   ├── ingestion/
│   │   │   ├── loaders/
│   │   │   ├── extractors/
│   │   │   ├── chunking.py
│   │   │   ├── pipeline.py
│   │   │   └── jobs.py
│   │   │
│   │   ├── embeddings/
│   │   │   ├── model.py
│   │   │   └── service.py
│   │   │
│   │   ├── retrieval/
│   │   │   ├── dense.py
│   │   │   ├── sparse.py
│   │   │   ├── hybrid.py
│   │   │   ├── fusion.py
│   │   │   └── reranker.py
│   │   │
│   │   ├── rag/
│   │   │   ├── chain.py
│   │   │   ├── prompts.py
│   │   │   ├── citations.py
│   │   │   └── verification.py
│   │   │
│   │   ├── agents/
│   │   │   ├── graph.py
│   │   │   ├── supervisor.py
│   │   │   ├── rag_agent.py
│   │   │   ├── ml_agent.py
│   │   │   └── response_agent.py
│   │   │
│   │   ├── ml/
│   │   │   ├── preprocessing.py
│   │   │   ├── training.py
│   │   │   ├── prediction.py
│   │   │   └── explainability.py
│   │   │
│   │   ├── database/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── evaluation/
│   │
│   ├── tests/
│   ├── migrations/
│   ├── scripts/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── .env.example
│
├── frontend/
│   ├── app/
│   ├── components/
│   ├── hooks/
│   ├── lib/
│   ├── services/
│   └── types/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   ├── monitoring/
│   └── deployment/
│
├── evaluation/
│   ├── datasets/
│   ├── expected_answers/
│   └── reports/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   ├── setup.md
│   └── deployment.md
│
├── docker-compose.yml
├── .gitignore
└── README.md


8. Testing strategy
AURA needs tests at every layer. Do not rely only on manually asking questions in the chat interface.
Test category	What to verify
Unit tests	Chunking, metadata, embeddings, prompts
Integration tests	Qdrant, PostgreSQL, Redis
API tests	Upload, chat, authentication, deletion
Retrieval tests	Dense, BM25, hybrid, reranking
RAG quality tests	Faithfulness, relevance, citations
Agent tests	Routing, state transitions, failures
Security tests	Prompt injection, access isolation
Performance tests	Concurrent requests, latency
End-to-end tests	Upload → index → ask → cite

Important acceptance tests
1. Upload a PDF and verify that it is indexed.
2. Ask a question whose answer exists in the PDF.
3. Verify that the answer includes the correct source and page.
4. Ask something not covered by the documents.
5. Verify that AURA says the evidence is insufficient.
6. Upload a second version of the document and verify re-indexing.
7. Delete a document and verify that its chunks are no longer retrievable.
8. Attempt to access another user's document and verify access is denied.
9. Upload a document containing prompt-injection instructions and verify that the system does not follow them.
10. Simulate a failed LLM or Qdrant request and verify graceful error handling.
9. Deployment and DevOps
The project should be reproducible on another developer's computer and deployable to a cloud environment.

Local development

Use Docker Compose to run:
- FastAPI backend.
- Next.js frontend.
- PostgreSQL.
- Qdrant.
- Redis.
- Background worker.
- Optional Langfuse and monitoring services.
CI/CD pipeline
GitHub push / pull request

Linting and code quality

Unit and integration tests

Docker image build

Deploy to staging / production


Production deployment should include:
- HTTPS and Nginx reverse proxy.
- Secure environment configuration.
- Database migrations and backups.
- Persistent Qdrant storage.
- Object storage for uploaded documents.
- Application health and readiness checks.
- Logs, metrics and error monitoring.
- Deployment rollback strategy.
- Resource and API cost monitoring.
You can deploy the first version on AWS using a modest container-based setup. You do not need Kubernetes initially.
10. Final project scope and priorities
The full vision is large. I recommend implementing it in three levels so you finish a reliable product rather than leaving ten half-built modules.
Level 1 — Core AURA
Must complete

This is the minimum complete product.
- [ ] Document upload and ingestion.
- [ ] PDF, DOCX, TXT and Markdown support.
- [ ] Text extraction and configurable chunking.
- [ ] Hugging Face embeddings.
- [ ] Qdrant vector storage.
- [ ] Dense retrieval.
- [ ] BM25 sparse retrieval.
- [ ] Hybrid retrieval and RRF.
- [ ] Cross-encoder reranking.
- [ ] Evidence-grounded LLM generation.
- [ ] Source citations and abstention.
- [ ] FastAPI endpoints.
- [ ] Basic Next.js chat and document interface.
- [ ] Automated tests and Docker Compose.
  
  
  Level 2 — Advanced AURA
  Strong differentiators
- [ ] LangGraph supervisor and specialized agents.
- [ ] Query rewriting and multi-query retrieval.
- [ ] Document versioning and asynchronous ingestion.
- [ ] Conversation history and memory.
- [ ] User authentication and workspace isolation.
- [ ] RAGAS and custom retrieval evaluation.
- [ ] Langfuse tracing and token-cost tracking.
- [ ] Evaluation dashboard.
- [ ] Prompt-injection protection.
- [ ] Streaming responses.
  
  
  Level 3 — Production AURA
  Advanced extensions
- [ ] ML prediction and SHAP explainability.
- [ ] Admin and usage analytics.
- [ ] Redis caching and queue management.
- [ ] Monitoring with Prometheus and Grafana.
- [ ] Cloud deployment and CI/CD.
- [ ] Backups, recovery and audit logging.
- [ ] Load testing and performance optimization.
- [ ] Multi-tenant production architecture.

11. Suggested implementation timeline
For a solo developer working alongside a job, I would plan around 12–16 weeks. The actual duration depends on how much of your existing implementation can be reused.
Phase	Main work	Target
1	Audit existing AURA and stabilize it	Week 1
2	Document ingestion and chunking	Weeks 2–3
3	Embeddings and Qdrant	Week 4
4	Hybrid retrieval and reranking	Weeks 5–6
5	Generation, citations and verification	Week 7
6	RAG evaluation and improvements	Week 8
7	LangGraph agents	Weeks 9–10
8	Frontend and authentication	Weeks 11–12
9	ML module and observability	Weeks 13–14
10	Docker, CI/CD and deployment	Weeks 15–16

12. What makes AURA technically impressive?
The project should demonstrate the following competencies, with actual implementation and measurable results.
AI engineering skill	What AURA demonstrates
LLM integration	Model APIs, prompts and structured outputs
RAG engineering	End-to-end retrieval pipeline
Vector databases	Qdrant collections, payloads and filtering
Information retrieval	BM25, dense retrieval and hybrid search
Reranking	Cross-encoder relevance optimization
Agent engineering	LangGraph orchestration
AI safety	Prompt-injection defense and evidence verification
ML engineering	Model training and explainability
LLMOps	Evaluation, tracing and cost tracking
Backend engineering	FastAPI, async tasks and APIs
DevOps	Docker, CI/CD and cloud deployment

Do not claim a capability just because its library is installed. For example, saying AURA supports hybrid retrieval should mean that both dense and sparse retrieval are actually connected to the production query path and evaluated.
13. Final definition of done
AURA should be considered complete when a new user can:
1. Register and create a workspace.
2. Upload multiple documents.
3. See ingestion and indexing progress.
4. Ask questions about the uploaded documents.
5. Receive answers with verifiable citations.
6. Receive an insufficient-evidence response when appropriate.
7. Continue a conversation with relevant context.
8. Inspect the sources used for each answer.
9. See retrieval and answer-quality metrics.
10. Use the platform securely without accessing another workspace's data.
And as the developer, you should be able to:
- Run the complete application using documented setup instructions.
- Reproduce the ingestion and retrieval pipelines.
- Run automated tests.
- Compare retrieval configurations using a fixed evaluation dataset.
- Trace requests and diagnose failures.
- Deploy the application through a documented CI/CD process.

My final recommendation for your existing AURA project
Do not immediately build all ten modules. Your first milestone should be AURA RAG Engine V2.
AURA RAG Engine V2
First development milestone
The first working product should have:
1. Document ingestion.
2. Intelligent chunking.
3. Hugging Face embeddings.
4. Qdrant vector storage.
5. BM25 + dense hybrid retrieval.
6. RRF fusion.
7. Cross-encoder reranking.
8. Groq-based answer generation.
9. Evidence verification and citations.
10. RAG evaluation.
Deliverable: A working, tested RAG engine exposed through FastAPI, with a reproducible Docker setup.

Since your existing repository already has a RAG implementation, Qdrant integration and a LangGraph agent workflow, we should audit and improve those components rather than replace them unnecessarily.

The next practical step is to turn this specification into a development plan mapped against your actual AURA repository: what already exists, what is incomplete, what needs fixing, and what needs building. I can work through that implementation module by module, starting with the existing RAG pipeline.