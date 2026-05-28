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
aiops-start          # start Langfuse infra + frontend + backend
aiops-stop           # stop everything (including Langfuse)
aiops-stop-app       # stop frontend + backend only (keep Langfuse/DB running)
aiops-restart        # restart frontend + backend (keeps Langfuse running)
aiops-status         # show status of all components
aiops-logs-fe        # tail frontend logs
aiops-logs-be        # tail backend logs
aiops-infra-start    # start Langfuse only
aiops-infra-stop     # stop Langfuse only
aiops-infra-status   # show docker compose ps for Langfuse
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
| `LANGFUSE_PUBLIC_KEY` | No | Enables LLM tracing (see below) |
| `LANGFUSE_SECRET_KEY` | No | Enables LLM tracing |
| `LANGFUSE_HOST` | No | Default `https://cloud.langfuse.com`; set to `http://localhost:3000` for self-hosted |

### LLM Observability (Langfuse)

Both AI pipelines are instrumented with [Langfuse](https://langfuse.com) traces. When `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set, every query produces a structured trace:

```
text_to_sql trace
├── generate_sql      (Claude — SQL generation)
├── validate_sql      (local regex check)
├── explain_dry_run   (PostgreSQL EXPLAIN)
├── execute_sql       (DB round-trip, row_count)
└── stream_explanation (Claude — streaming tokens)

rag_query trace
├── embed_question    (nomic-embed-text / text-embedding-3-small)
├── hybrid_retrieve   (BM25 + ChromaDB + RRF, best_score, sections)
├── grounding_guard   (similarity threshold check)
└── claude_answer     (Claude — grounded answer)
```

**Self-hosted (free, local):**
```bash
docker run -p 3020:3000 langfuse/langfuse   # port 3020 — see workspace-local-ports.md
# Add to .env.local:
# LANGFUSE_HOST=http://localhost:3020
# LANGFUSE_PUBLIC_KEY=pk-lf-...   # from http://localhost:3020
# LANGFUSE_SECRET_KEY=sk-lf-...
```

Tracing is **opt-in and zero-impact** — all pipelines run normally without any degradation when keys are not set.

## Multi-Environment Config

| Variable | Description |
|---|---|
| `APP_ENV` | `local` / `ci` / `uat` |
| `ML_DB_URL` | asyncpg connection string for ml_db |
| `KEYCLOAK_DB_URL` | asyncpg connection string for keycloak DB |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OLLAMA_BASE_URL` | Ollama base URL (default: `http://localhost:11434`) |

CI and UAT inject environment variables directly — no `.env` file needed in those environments.

## Deployment

### Frontend → Vercel

1. Push the repo to GitHub.
2. In the [Vercel dashboard](https://vercel.com), import the repository.
3. Set **Root Directory** to `frontend`.
4. Add the environment variable:
   ```
   VITE_API_URL=https://<your-railway-app>.up.railway.app
   ```
5. Deploy. Vercel uses `npm run build` automatically and serves `dist/`.

`vercel.json` handles SPA routing (all paths fall back to `index.html`).

> **Order matters:** deploy the ai-service to Railway first to get the URL, then set `VITE_API_URL` in Vercel before deploying the frontend.

---

### AI Service → Railway

1. In the [Railway dashboard](https://railway.app), create a new project → **Deploy from GitHub repo**.
2. Set **Root Directory** to `ai-service`.
3. Railway auto-detects the `Dockerfile`. Set the required environment variables:

   | Variable | Value |
   |---|---|
   | `APP_ENV` | `uat` |
   | `ML_DB_URL` | `postgresql+asyncpg://<user>:<pass>@<host>:<port>/ml_db` |
   | `KEYCLOAK_DB_URL` | `postgresql+asyncpg://<user>:<pass>@<host>:<port>/keycloak` |
   | `ANTHROPIC_API_KEY` | `sk-ant-...` |
   | `CORS_ORIGINS` | `["https://<your-vercel-app>.vercel.app"]` |
   | `OPENAI_API_KEY` | *(optional)* better embeddings for RAG |
   | `LANGFUSE_PUBLIC_KEY` | *(optional)* LLM tracing |
   | `LANGFUSE_SECRET_KEY` | *(optional)* LLM tracing |

4. After the first deploy, **run the RAG ingest** as a one-off Railway job:
   ```bash
   python -m app.rag.ingest
   ```
   This populates the ChromaDB vector store (`rag_data/`) needed for Knowledge Base queries.
   > Note: `rag_data/` and query history (`portal_data.db`) are ephemeral on Railway — they reset on each deploy. For persistence, mount a Railway volume at `/app/rag_data` and `/app/portal_data.db`.

---

### Docker (local or self-hosted)

Both services have production Dockerfiles.

**AI Service:**
```bash
docker build -t aiops-api ./ai-service
docker run -p 8007:8000 \
  -e APP_ENV=uat \
  -e ML_DB_URL=... \
  -e KEYCLOAK_DB_URL=... \
  -e ANTHROPIC_API_KEY=... \
  -e CORS_ORIGINS='["http://localhost:3007"]' \
  aiops-api
```

**Frontend** (multi-stage nginx build):
```bash
docker build --build-arg VITE_API_URL=http://localhost:8007 -t aiops-fe ./frontend
docker run -p 3007:80 aiops-fe
```

Or use Docker Compose (starts both services together):
```bash
ANTHROPIC_API_KEY=sk-ant-... docker compose -f infrastructure/docker-compose.yml up -d
```

---

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
