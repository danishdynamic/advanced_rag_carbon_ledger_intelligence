# Carbon Ledger Analytics & Compliance Intelligence Platform

A high-performance, event-driven compliance intelligence platform designed to ingest regulatory documents, ESG disclosures, climate reports, and operational filings using Gemini Multimodal Vision, transform them into structured knowledge assets, and provide enterprise-grade Retrieval-Augmented Generation (RAG) capabilities for compliance auditing and regulatory intelligence.

 ![Screenshot](frontend/public/ScreenshotRag.png)

---

# 🏗️ Architecture Overview

The platform is built around a decoupled architecture that separates ingestion, retrieval, generation, and evaluation workflows into independent services.

```text
┌─────────────────────────────────────────────┐
│            React Frontend Dashboard         │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              FastAPI API Layer              │
└─────────────────────────────────────────────┘
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
  Document       Compliance        Chat Engine
  Services         APIs             APIs
      │
      ▼
┌─────────────────────────────────────────────┐
│         Advanced RAG Intelligence Layer     │
└─────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────┐
│      PostgreSQL + pgvector + Graph Data     │
└─────────────────────────────────────────────┘
```

---

# 🚀 Core Features

### Multimodal Document Intelligence

* PDF ingestion
* ESG report parsing
* Compliance document analysis
* Table extraction
* Chart interpretation
* Layout-aware text extraction

### Enterprise Retrieval-Augmented Generation

* Parent-child chunking
* Graph-RAG
* HYDE retrieval
* Query decomposition
* Reciprocal Rank Fusion
* Cross-encoder reranking
* Corrective RAG validation
* RAGAS quality scoring

### Compliance Intelligence

* Regulatory document analysis
* Climate disclosure auditing
* ESG metric extraction
* Entity relationship mapping
* Audit trail generation

---

# 📂 Project Structure

```text
backend/
│
├── app/
│   │
│   ├── advanced_rag/
│   │   ├── hyde.py
│   │   └── query_processor.py
│   │
│   ├── api/
│   │   ├── endpoints.py
│   │   │
│   │   └── routers/
│   │       ├── chat.py
│   │       ├── compliance.py
│   │       ├── documents.py
│   │       └── ledger.py
│   │
│   └── services/
│       ├── evaluator.py
│       ├── ingestion_worker.py
│       ├── quota_manager.py
│       ├── reranker.py
│       ├── rewriter.py
│       └── search.py
│
├── config/
│
├── database/
│
├── migrations/
│   ├── 001_create_ingestion.sql
│   ├── 002_gemini_daily_quota.sql
│   └── 003_gemini_rag_base.sql
│
├── main.py
│
└── Dockerfile


frontend/
│
├── components/
│
├── ui/
│   ├── Button.tsx
│   ├── Card.tsx
│   ├── DashboardStats.tsx
│   ├── ComplianceChat.tsx
│   └── Sonner.tsx
│
├── lib/
│   └── api.ts
│
└── App.tsx
```

---

# 🧠 Advanced RAG Intelligence Layer

The platform implements a production-grade retrieval architecture combining semantic search, graph reasoning, reranking, hallucination prevention, and automated answer evaluation.

---

## Multi-Format Visual Ingestion Layer

The ingestion subsystem uses Gemini Multimodal Vision to extract structured information from:

* PDF files
* Regulatory filings
* ESG reports
* Climate disclosures
* Plain-text submissions

The extraction process preserves:

* Layout structure
* Tables
* Charts
* Semantic sections
* Metadata relationships

```text
PDF
 │
 ▼
Gemini Vision
 │
 ▼
Structured Markdown
 │
 ▼
Knowledge Processing Pipeline
```

---

## Parent-Child Hierarchical Chunking

Documents are transformed into hierarchical retrieval structures.

### Parent Chunks

Large contextual blocks preserving:

* Narrative continuity
* Compliance context
* Cross-reference information

### Child Chunks

Fine-grained retrieval units optimized for semantic search.

Examples:

* Sentences
* Claims
* Metrics
* Regulatory statements

```text
Document
    │
    ▼
Parent Node
    │
 ┌──┼──┐
 ▼  ▼  ▼
C1 C2 C3
```

This architecture improves retrieval accuracy while maintaining contextual integrity.

---

## Graph-RAG Topology Engine

The system automatically extracts entities and constructs relationship graphs.

Entity Examples:

* Facilities
* Companies
* Regulatory Bodies
* Emissions
* Penalties
* Financial Obligations

```text
Company
   │
   ├──── owns ─────► Facility
   │
   ├──── emits ────► Carbon Source
   │
   └──── fined ────► Regulatory Agency
```

Graph edges are stored alongside vector embeddings within PostgreSQL.

---

## HYDE Retrieval Layer

Hypothetical Document Embeddings (HYDE) are generated before retrieval.

Benefits:

* Better semantic recall
* Improved retrieval coverage
* Enhanced response quality for sparse queries

```text
User Query
      │
      ▼
HYDE Generator
      │
      ▼
Synthetic Ideal Answer
      │
      ▼
Embedding Search
```

---

## Cognitive Query Decomposition

Incoming prompts are converted into structured retrieval plans.

Example:

```json
{
  "intent": "compliance_audit",
  "entities": ["Facility-17"],
  "targets": [
    "emissions",
    "violations",
    "penalties"
  ]
}
```

Benefits:

* Complex reasoning support
* Multi-hop retrieval
* Targeted context discovery

---

## Multi-Branch Reciprocal Rank Fusion (RRF)

Multiple retrieval engines execute concurrently.

### Vector Search

Semantic similarity using pgvector.

### Keyword Search

PostgreSQL full-text retrieval.

### Graph Search

Entity relationship traversal.

Results are merged through Reciprocal Rank Fusion.

```text
Vector Search
      │
Keyword Search
      │
Graph Search
      │
      ▼
Reciprocal Rank Fusion
      │
      ▼
Unified Retrieval Set
```

---

## Cross-Encoder Reranking

Retrieved contexts are evaluated using FlashRank.

Responsibilities:

* Relevance scoring
* Context ordering
* Noise reduction
* Evidence prioritization

```text
Candidate Contexts
        │
        ▼
FlashRank
        │
        ▼
Top Evidence
```

---

## Corrective RAG (CRAG)

A confidence gate validates retrieved evidence before generation.

Functions:

* Confidence scoring
* Retrieval quality checks
* Hallucination prevention
* Retrieval correction

```text
Retrieved Context
        │
        ▼
CRAG Validator
        │
   ┌────┴────┐
   ▼         ▼
Pass      Reject
```

Only validated context reaches the LLM.

---

## Real-Time RAGAS Evaluation

Every response is evaluated automatically.

Metrics:

### Faithfulness

Measures evidence grounding.

### Answer Relevance

Measures query alignment.

### Context Precision

Measures retrieval quality.

### Context Recall

Measures retrieval completeness.

```text
Generated Response
        │
        ▼
RAGAS Evaluator
        │
        ├── Faithfulness
        ├── Relevance
        ├── Precision
        └── Recall
```

Evaluation results are logged for observability and continuous improvement.

---

# 🔄 End-to-End Retrieval Flow

```text
User Query
      │
      ▼
Query Processor
      │
      ▼
HYDE Generator
      │
      ▼
Query Decomposition
      │
      ▼
─────────────────────────────
│  Vector Search            │
│  Keyword Search           │
│  Graph Search             │
─────────────────────────────
      │
      ▼
RRF Fusion
      │
      ▼
FlashRank Reranker
      │
      ▼
CRAG Validation
      │
      ▼
LLM Generation
      │
      ▼
RAGAS Evaluation
      │
      ▼
Final Response
```

---

# 🗄️ Database Architecture

The platform uses PostgreSQL as a unified operational and retrieval datastore.

### Core Technologies

* PostgreSQL
* pgvector
* Full-text search
* Graph relationship tables
* HNSW vector indexing

### Benefits

* Single datastore architecture
* Low operational complexity
* Fast vector retrieval
* Native transactional consistency
* Scalable compliance intelligence workloads

---

# 🛠️ Docker Deployment

## Launch Entire Platform

```bash
docker compose up --build -d
```

---

## Monitor Runtime Logs

```bash
docker compose logs -f
```

Backend:

```bash
docker compose logs -f backend
```

Frontend:

```bash
docker compose logs -f frontend
```

---

# 💻 Local Development

## Start Database Services

```bash
docker compose up -d postgres
```

---

## Run Backend

```bash
uvicorn main:app --reload --port 8000
```

---

## Run Frontend

```bash
npm install
npm run dev
```

---

# 📊 Observability & Evaluation

The platform continuously tracks:

* Retrieval latency
* Vector search performance
* Graph search performance
* RAGAS scores
* Faithfulness metrics
* Answer relevance metrics
* Gemini quota utilization
* Document ingestion throughput

---

# ✨ Technical Highlights

* FastAPI asynchronous architecture
* Gemini Multimodal Vision
* PostgreSQL + pgvector
* Parent-child chunking
* Graph-RAG
* HYDE retrieval
* Query decomposition
* Reciprocal Rank Fusion
* FlashRank reranking
* Corrective RAG (CRAG)
* Real-time RAGAS evaluation
* Enterprise compliance intelligence
* Dockerized deployment
* Hallucination-resistant generation

---

# 📜 License

This project serves as a reference implementation for enterprise compliance intelligence, multimodal document processing, advanced Retrieval-Augmented Generation, and regulatory knowledge systems.
