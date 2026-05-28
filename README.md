# AI Operations Portal

An AI-assisted operational intelligence platform for enterprise transactional systems. Provides natural language analytics, real-time dashboards, and AI-generated insights over remittance and fintech operational data — without requiring any new database schema.

## Features

| Module | Description |
|---|---|
| **Operational Dashboard** | Transaction counts, failure rates, processing time (p50/p95), hub breakdown |
| **Transaction Explorer** | Paginated search with filters, detail view, full audit timeline |
| **AI Assistant — Chat** | Natural language queries grounded in live aggregate stats (streaming SSE) |
| **AI Assistant — Text-to-SQL** | NL → validated SQL → execute → streaming plain-English explanation |
| **AI Insights Engine** | Auto-generated summaries, anomaly explanations, trend observations |
| **Knowledge Base** | RAG-powered Q&A over system docs; hybrid BM25 + vector search; source citations |

## Architecture

```
frontend/       React 19 + Vite 8 + TailwindCSS v4 — port 3007
ai-service/     Python FastAPI + SQLAlchemy async — port 8007
docs/           Database design, API contracts, RAG eval results
infrastructure/ Docker Compose
```

The frontend proxies all `/api` requests to the ai-service. No separate backend — the FastAPI service handles both operational queries and AI pipelines.

### Text-to-SQL Pipeline

```
User question
  → Schema context (5 whitelisted tables, PII-stripped, status enum, FK hints)
  → Claude claude-opus-4-6 generates SELECT-only SQL
  → Validate (reject writes) + EXPLAIN dry-run
  → Route: remittance.* → keycloak DB | ml_schema.* → ml_db
  → Execute + stream plain-English explanation back via SSE
```

Typed SSE events: `{type: status}` → `{type: sql}` → `{type: token}×N` or `{type: error}`

### RAG Pipeline

```
Ingest:  database-design.md → header-based chunker (51 chunks, 2000 char max)
           → nomic-embed-text (Ollama) or text-embedding-3-small (OpenAI)
           → ChromaDB PersistentClient + in-memory BM25Okapi index

Query:   Question → embed → vector top-8 + BM25 top-8
           → Reciprocal Rank Fusion (k=60) → top-6 chunks
           → Grounding guard (similarity < 0.40 → refuse to answer)
           → Claude answers citing numbered context blocks
           → {answer, sources: [{chunk_text, section_title, score}]}
```

**RAG eval results** (RAGAS 0.2.15, 15 golden Q&A pairs, Ollama evaluator):

| Metric | Score | Target |
|---|---|---|
| context_recall | **0.865** | > 0.80 ✅ |
| faithfulness | 1.000 (partial) | > 0.85 |

Full results in [`docs/rag-eval-results.md`](docs/rag-eval-results.md).

## Data Sources

Reads from two existing PostgreSQL databases (never writes).

| Database | Schema | Key Tables |
|---|---|---|
| `ml_db` | `ml_schema` | `country`, `mobile_operator`, `ml_fx_rates` |
| `ml_db` | `service_management` | `remit_service`, `external_partner` |
| `keycloak` | `remittance` | `transaction`, `transaction_aud` |
| `keycloak` | `customer` | `beneficiary` |
| `keycloak` | `payment` | `ml_m_sof_payment` |

Payment hubs: **TELEPIN, WU (Western Union), THUNES, TRANGLO**

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.12
- Access to local databases on `localhost:54320`
- Anthropic API key

### Environment Setup

```bash
cp ai-service/.env.local.example ai-service/.env.local
# Edit ai-service/.env.local and fill in your ANTHROPIC_API_KEY
```

Required variables in `.env.local`:

```
APP_ENV=local
ML_DB_URL=postgresql+asyncpg://admin:admin@localhost:54320/ml_db
KEYCLOAK_DB_URL=postgresql+asyncpg://admin:admin@localhost:54320/keycloak
ANTHROPIC_API_KEY=sk-ant-...
```

### Running Locally

**Frontend**
```bash
cd frontend
npm install
npm run dev        # http://localhost:3007
```

**AI Service**
```bash
cd ai-service
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8007
```

**Ingest knowledge base docs** (required for Knowledge Base / RAG queries)
```bash
cd ai-service
# Requires Ollama running with nomic-embed-text, OR OPENAI_API_KEY set
python -m app.rag.ingest
# → embeds docs/database-design.md into ChromaDB (rag_data/ — gitignored)
# → rebuilds BM25 index in memory
# Re-run after any edits to docs/database-design.md
```

**Run eval** (optional — measures RAG retrieval quality)
```bash
cd ai-service
pip install -r requirements-eval.txt
python scripts/eval_rag.py
# Results written to docs/rag-eval-results.md
```

**Or with the shell CLI** (after `source ~/.zshrc`):
```bash
aiops-start        # start both services
aiops-stop         # stop both
aiops-restart      # restart both
aiops-status       # show running PIDs and URLs
aiops-logs-fe      # tail frontend logs
aiops-logs-be      # tail backend logs
```

### Other Commands

```bash
# Frontend
npm run build      # production build
npm run lint
npm test           # Vitest (29 tests)

# AI Service
pytest             # all tests (101 tests — text_to_sql, schema_context, chunker, retriever)
pytest tests/path/test_file.py::test_name      # single test
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/dashboard/overview` | Key metrics (volume, failure rate, processing time) |
| GET | `/api/v1/dashboard/volume-trend` | Volume over time (hour/day interval) |
| GET | `/api/v1/dashboard/hub-breakdown` | Per-hub failure and volume stats |
| GET | `/api/v1/transactions` | Paginated transaction search |
| GET | `/api/v1/transactions/{id}` | Transaction detail |
| GET | `/api/v1/transactions/{id}/audit` | Audit history timeline |
| POST | `/api/v1/ai/chat` | Streaming NL query grounded in live stats (SSE) |
| POST | `/api/v1/ai/insights` | Generate AI operational insights |
| POST | `/api/v1/assistant/query` | **Text-to-SQL**: NL → SQL → execute → stream explanation (SSE) |
| GET | `/api/v1/rag/status` | Knowledge base status (chunk count, last ingested) |
| POST | `/api/v1/rag/query` | **RAG**: Q&A over system docs with source citations |
| GET/PUT | `/api/v1/admin/thresholds` | Alert threshold configuration |
| GET/POST | `/api/v1/admin/prompts` | Prompt template management |

Interactive API docs: `http://localhost:8007/docs` (local only).

## AI Integration

- **Primary LLM:** `claude-opus-4-6` via Anthropic SDK — used for SQL generation, result explanation, and RAG answering
- **Embeddings:** `text-embedding-3-small` (OpenAI) when `OPENAI_API_KEY` is set; `nomic-embed-text` via Ollama otherwise
- **Fallback LLM:** Ollama (`llama3.1:8b`) via OpenAI-compatible endpoint for local/offline use
- Prompt templates are user-configurable via the Admin panel
- PII fields (MSISDN, names, DOB, account numbers) are stripped from all AI prompts at the schema context layer

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Claude claude-opus-4-6 for SQL + RAG chain |
| `OPENAI_API_KEY` | No | Better embeddings (`text-embedding-3-small`); falls back to Ollama |
| `OLLAMA_BASE_URL` | No | Default `http://localhost:11434` |

## Multi-Environment Config

| Variable | Description |
|---|---|
| `APP_ENV` | `local` / `ci` / `uat` |
| `ML_DB_URL` | asyncpg connection string for ml_db |
| `KEYCLOAK_DB_URL` | asyncpg connection string for keycloak DB |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OLLAMA_BASE_URL` | Ollama base URL (default: `http://localhost:11434`) |

CI and UAT inject environment variables directly — no `.env` file needed in those environments.

## Connecting to Production

1. **Set `APP_ENV=uat`** in your `.env` — this disables SQL echo logging and hides `/docs`/`/redoc`.

2. **Use a read-only DB user** — the portal never writes to either database, so grant `SELECT` only on the required schemas.

3. **Production DB load guards** (already enforced in code):
   - Connection pool capped at **2–3 connections** per DB (vs 10 locally)
   - All dashboard and transaction queries are **capped at a 90-day date window** — requests for wider ranges are silently trimmed
   - Transaction search `page_size` is hard-limited to **100 rows**
   - AI context queries run **aggregates only** (no full table scans)

4. **Recommended `.env` for prod use:**
   ```
   APP_ENV=uat
   ML_DB_URL=postgresql+asyncpg://<readonly_user>:<pass>@<prod-host>:<port>/ml_db
   KEYCLOAK_DB_URL=postgresql+asyncpg://<readonly_user>:<pass>@<prod-host>:<port>/keycloak
   ANTHROPIC_API_KEY=sk-ant-...
   CORS_ORIGINS=["http://localhost:3007"]
   ```

> **Note:** After updating any `.env` or `.env.local` file, restart the backend for changes to take effect:
> ```bash
> aiops-restart
> ```
