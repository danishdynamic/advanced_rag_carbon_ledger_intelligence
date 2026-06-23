# Carbon Ledger Analytics & Ingestion Platform

A high-performance, decoupled platform for parsing unstructured corporate climate compliance documents, extracting environmental metrics via Multimodal AI, and executing deterministic financial risk analytics.

## 🏗️ Architectural Overview

The platform is designed around a strict separation of concerns, ensuring high throughput, data integrity, and sub-second analytical querying.

* **Frontend:** React / TypeScript / Vite UI featuring dynamic risk instrumentation widgets and threshold monitors.
* **API Layer (FastAPI):** Domain-segmented routing paths that separate system operational diagnostics from business logic analytics.
* **Service Layer (The Brain):** Isolated, deterministic execution engines that keep algorithmic computation decoupled from the HTTP transport layer.
* **Ingestion Pipeline (Async Task Worker):** Out-of-band file decoder utilizing `asyncpg` for low-latency batch writes and the `google-genai` SDK for visual document parsing.
* **Database Infrastructure:** Split-pool PostgreSQL configuration segmenting Write operations (Primary Node: `5433`) from Read operations (Replica Node: `5434`).

## 📂 Key Core Components

```text
backend/app/
├── api/
│   ├── endpoints.py           # ⚙️ System health diagnostics & operational metrics
│   └── routers/
│       └── analytics.py       # 📊 Climate & Green Finance routing endpoints
├── services/
│   └── risk_engine.py         # 🧮 Deterministic asset exposure & carbon tax liabilities
├── workers/
│   └── ingestion_worker.py    # 🧠 Polymorphic async Gemini vision ingestion & vectorization
└── db/
    └── session.py             # 🔌 Database engine write-pool and read-replica routing

```

---

## 🔄 The Data Lifecycle Loop

- Ingestion: Users upload compliance PDFs via the /api/documents/upload endpoint (documents.py).

- AI Visual Parsing: ingestion_worker.py routes the payload to gemini-2.5-flash to extract layout text, parse pixel-level charts, and transcribe tables into Markdown.

- Structured Extraction: A secondary structured pass forces Gemini to return a strict Pydantic JSON schema isolating facility_name and annual_co2_emissions_tons.

- Deterministic Math: Python handles the baseline calculations (emissions * carbon_rate) inside the safe, non-hallucinatory runtime environment.

- Persistence: The worker commits records to the primary database (5433), which synchronizes downstream to the read-replica (5434).

- Analytics Delivery: The React dashboard triggers a fetch to /api/analytics/climate-risk. The router hands execution to ClimateRiskService, which aggregates replica metrics instantly.

---

## 🛠️ Local Environment Management

- Spinning Up the DB Cluster
  
``` PowerShell
docker compose up -d
```

- Running the Async Worker / Backend API
  
- Ensure your virtual environment is active and run:

``` PowerShell
uvicorn app.main:app --reload --port 8000
```

- Running the Frontend Dashboard
  
``` Bash
npm run dev
```
