# TODO — AI Operations Portal (Proposed)

> Last updated: 2026-05-28
> **Learning goal:** Text-to-SQL (Phase 2) → RAG Pipeline (Phase 3). Both skills target AI Engineer / Solution Architect roles per the workspace roadmap.

## Status Overview

| Area | Status |
|---|---|
| Project scaffolding (dirs, React, Docker) | Done |
| ai-service foundation (FastAPI + async DB) | Not started |
| Schema context layer | Not started |
| Text-to-SQL pipeline | Not started |
| RAG pipeline | Not started |
| Operational Dashboard | Not started |
| Transaction Explorer | Not started |
| AI Insights Engine | Not started |
| Deployment | Not started |

---

## Phase 1 — Foundation (Scaffolding Done)

- [x] Project dirs + `.gitignore`
- [x] React frontend bootstrap — Vite + React 19 + TypeScript, TailwindCSS v4, path alias `@/`, dev port 3001, Vitest
- [x] `ai-service/app/__init__.py`
- [x] `ai-service/.env.local.example`
- [ ] `ai-service/app/main.py` — FastAPI app with `lifespan` context manager; CORS for `localhost:3001`
- [ ] `ai-service/app/config.py` — pydantic-settings `BaseSettings`; load `.env.local` when `APP_ENV=local`, read injected env vars in CI/UAT
- [ ] `ai-service/app/db/engines.py` — two `create_async_engine` instances: `ML_DB_URL` (ml_db) + `KEYCLOAK_DB_URL` (keycloak); both read-only
- [ ] `ai-service/app/db/session.py` — `async_sessionmaker` for each engine; expose as FastAPI `Depends` dependencies
- [ ] `GET /health` — ping both DB connections; return `{ ml_db: "ok"|"error", keycloak: "ok"|"error" }`
- [ ] `requirements.txt` — pin exact versions: `fastapi`, `uvicorn[standard]`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic-settings`, `anthropic`, `python-dotenv`
- [ ] `docker-compose.yml` (root) — ai-service container; `host.docker.internal` for existing DBs at `localhost:54320`

---

## Phase 2 — Text-to-SQL (Core Skill #1)

> **Skill target:** Schema-aware NL→SQL, LLM output validation, hallucinated column detection, cross-DB query routing.
> Differentiator: real enterprise fintech schema (`remittance.transaction` 65 columns, corridor config, FX rates) — not toy data.

### SQLAlchemy Read Models
- [ ] `app/models/remittance.py` — `remittance.transaction` (key columns: id, status, hub_name, service_id, remittance_amount, recipient_amount, retail_fee, error_code, hub_error_code, fraud_status, created_date)
- [ ] `app/models/service_management.py` — `remit_service` (id, system_name, local_currency, foreign_currency, external_partner_id, status), `external_partner` (id, external_partner_name)
- [ ] `app/models/ml_schema.py` — `country` (id, country_name, country_iso_code), `ml_fx_rates` (from_currency, to_currency, fx_rate, created_date)
- [ ] `app/models/audit.py` — `remittance.transaction_aud` (same columns + rev, revtype, audit_date)
- [ ] `app/db/cross_db.py` — Python-level join helpers: query each DB separately, merge on shared key

### Schema Context Layer
> The quality of Text-to-SQL is entirely determined by what schema context the LLM receives.

- [ ] `app/schema_context/loader.py` — build compact schema string for LLM prompts:
  - **Whitelist** query-safe tables only: `remittance.transaction`, `service_management.remit_service`, `service_management.external_partner`, `ml_schema.country`, `ml_schema.ml_fx_rates`
  - **Strip PII columns**: `sender_msisdn`, `sender_fullname`, `sender_dob`, `sender_email`, `recipient_msisdn`, `recipient_fullname`, `recipient_dob`
  - Format: `table_name(col: type — note, ...)` — one table per line
- [ ] `app/schema_context/status_ref.py` — TransactionStatus enum values grouped by phase (Payment, SOF, Remittance, Refund, Fraud) as a lookup string injected into every prompt
- [ ] `app/schema_context/relationships.py` — cross-schema join hints: e.g. `remittance.transaction.service_id → service_management.remit_service.remit_service_id`

### Text-to-SQL Pipeline
- [ ] `app/services/text_to_sql.py` — full NL→SQL→result→explanation flow:
  - **Step 1:** Build schema context (whitelisted tables, stripped PII, status enum, join hints)
  - **Step 2:** Send to `claude-opus-4-6` with adaptive thinking; prompt specifies SELECT-only, PostgreSQL dialect, schema-qualified table names, few-shot examples
  - **Step 3:** Validate SQL — reject if contains `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `TRUNCATE`; run `EXPLAIN` dry-run before executing
  - **Step 4:** Route DB — `remittance.*` / `customer.*` / `payment.*` → keycloak engine; `ml_schema.*` / `service_management.*` → ml_db engine; cross-DB → query both, join in Python
  - **Step 5:** Send raw result rows + original question back to Claude for a plain-English 2–4 sentence explanation
- [ ] Streaming — `client.messages.stream` + FastAPI `StreamingResponse` with `text/event-stream`
- [ ] Concurrency guard — `asyncio.Semaphore(5)`; Ollama fallback on `anthropic.BadRequestError`
- [ ] Structured error types: `sql_generation_failed` / `sql_validation_rejected` / `db_execution_error` / `no_results`
- [ ] `app/api/assistant.py` — `POST /api/assistant/query` body: `{ "question": str }`, streamed response
- [ ] Few-shot SQL examples in prompt:
  - "How many transactions failed today?" → `SELECT COUNT(*) FROM remittance.transaction WHERE status LIKE '%FAILED%' AND created_date::date = CURRENT_DATE`
  - "Failure rate by hub this month?" → group by `hub_name`, count success vs failed
  - "Top 5 corridors by volume this week?" → join `remittance.transaction` + `service_management.remit_service` on `service_id`
  - "Most common error codes last 7 days?" → group by `error_code` on `remittance.transaction`

### Frontend — AI Assistant
- [ ] `src/features/ai-assistant/AssistantChat.tsx` — message thread; user question → streaming assistant response
- [ ] Streaming render — consume SSE, append tokens in real time
- [ ] Response format — generated SQL in collapsible `<code>` block above plain-English explanation
- [ ] Error states — friendly message per type (`sql_validation_rejected`: "I can only run read queries")
- [ ] Example question chips: "How many failures today?", "Top corridors this week", "Failure rate by hub"

---

## Phase 3 — RAG Pipeline (Core Skill #2)

> **Skill target:** Technical doc chunking, embedding models (local + cloud), hybrid search (BM25 + vector + RRF), RAG eval with RAGAS.
> Corpus: `docs/database-design.md` + operational runbooks. Real fintech schema docs — not Wikipedia or PDFs.

### Vector Store Setup
- [ ] Add to `requirements.txt`: `chromadb`, `rank-bm25`, `openai`, `ragas`
- [ ] `app/rag/store.py` — ChromaDB client; persist to `./rag_data/`; collection: `ai_ops_portal_docs`
- [ ] `app/rag/embedder.py` — `text-embedding-3-small` (OpenAI); batch up to 100 chunks per call
  - Local fallback: if `OPENAI_API_KEY` unset, use Ollama `nomic-embed-text` at `localhost:11434/v1`
- [ ] Add `OPENAI_API_KEY` (optional) to `.env.local.example`

### Document Ingestion
- [ ] `app/rag/ingestion/chunker.py` — Markdown chunking strategy:
  - Split on `##` / `###` headers — section title becomes chunk metadata
  - Max chunk: 500 tokens, 50-token overlap between adjacent chunks
  - Metadata per chunk: `{ source_file, section_title, table_name }` — extract `table_name` when header matches `schema.table` pattern
- [ ] `app/rag/ingestion/loader.py` — load: `docs/database-design.md` (primary), future runbooks/ADRs
- [ ] `app/rag/ingestion/ingest.py` — CLI: `python -m app.rag.ingest` — load → chunk → embed → upsert; print chunk count
- [ ] `GET /api/rag/status` — return `{ doc_count, last_ingested_at, collection_name }`

### Hybrid Search (BM25 + Vector)
- [ ] `app/rag/retriever.py`:
  - **Vector search:** top-8 semantic matches from Chroma (cosine similarity)
  - **BM25 search:** top-8 keyword matches using `rank_bm25.BM25Okapi` over all chunk texts
  - **Merge:** Reciprocal Rank Fusion (RRF, k=60) — `score = 1/(rank + k)` summed across both lists; return top-6 unique chunks
- [ ] Cache BM25 index in memory at startup; rebuild on new ingest

### RAG Chain
- [ ] `app/rag/chain.py` — pipeline:
  - Step 1: Hybrid retrieval → top-6 chunks with metadata
  - Step 2: Augmented prompt — inject chunks as numbered context blocks; instruct Claude to cite context block per claim
  - Step 3: Claude answers grounded strictly in retrieved context
  - Step 4: Return `{ answer, sources: [{ chunk_text, section_title, source_file, score }] }`
- [ ] Grounding guard — if max retrieval score < 0.4, respond "Not enough relevant context found" — do not hallucinate
- [ ] `POST /api/rag/query` — body: `{ "question": str }`, response: `{ answer, sources }`

### RAG Evaluation
> Most engineers can build RAG — few can measure it. This is the interview differentiator.
- [ ] `tests/rag/golden_qa.json` — 15 Q&A pairs grounded in `docs/database-design.md`:
  - "What columns carry PII in remittance.transaction?"
  - "What does hub_id in remittance.transaction reference?"
  - "How do you find all status changes for a transaction?"
  - "What payment methods does the system support?"
  - "Difference between remittance_amount and recipient_amount?"
  - (10 more covering other schemas/sections)
- [ ] `scripts/eval_rag.py` — RAGAS metrics: `faithfulness`, `answer_relevance`, `context_recall`; print per-question + aggregate scores
- [ ] **Target:** faithfulness > 0.85, context_recall > 0.80
- [ ] `docs/rag-eval-results.md` — document score iterations when chunking/retrieval strategy changes

### Frontend — Knowledge Base Query
- [ ] `src/features/knowledge-base/KnowledgeQuery.tsx` — separate from AI Assistant (shows source citations)
- [ ] Answer panel + source cards — each retrieved chunk as collapsible card with `section_title` + snippet
- [ ] Example questions: "What tables contain transaction data?", "How does the payment flow work?"

---

## Phase 4 — Operational Dashboard & Transaction Explorer

> Build after Text-to-SQL works — reuses the same DB layer with pre-built (non-LLM) queries.

### Backend — Dashboard & Transactions
- [ ] `app/services/dashboard.py` — pre-built queries on `remittance.transaction`:
  - `GET /api/dashboard/summary` — today's totals: transactions, success count, failure count, avg processing time
  - `GET /api/dashboard/by-hub` — breakdown by `hub_name` (TELEPIN, WU, THUNES, TRANGLO)
  - `GET /api/dashboard/status-categories` — group 30+ statuses into: Success, Failed, In Progress, Refunded, Fraud
  - `GET /api/dashboard/failure-trend` — hourly failure count for last 24h
- [ ] `app/services/transaction.py` — `GET /api/transactions` — paginated, filterable by `status`, `hub_name`, `service_id`, date range
- [ ] `GET /api/transactions/{id}/history` — audit timeline from `remittance.transaction_aud` ordered by `rev`

### AI Insights Engine
- [ ] `app/prompts/daily_summary.txt` + `app/prompts/anomaly_explain.txt` — externalized prompt templates
- [ ] `POST /api/insights/daily-summary` — pass yesterday's aggregates to Claude; return 3–5 sentence operational summary
- [ ] `POST /api/insights/explain-anomaly` — pass anomaly datapoint + 1h context; Claude hypothesizes root cause

### Frontend — Dashboard & Transaction Explorer
- [ ] Stat cards: total transactions, failure rate %, avg processing time, active hubs
- [ ] Recharts: hourly failure trend (line), by-hub breakdown (bar), status distribution (pie)
- [ ] AI Insights panel — "Yesterday's summary" auto-loaded + "Explain spike" button on anomaly data points
- [ ] Transaction table — paginated, filter bar (status, hub, date range)
- [ ] Row expand — audit timeline from `transaction_aud`
- [ ] PII masking — never render `sender_msisdn`, `sender_fullname`, `recipient_msisdn`, `recipient_fullname`

---

## Phase 5 — Deployment & Portfolio Polish

- [ ] Deploy frontend to Vercel; set `VITE_API_URL` env var
- [ ] Deploy ai-service to Railway — `ai-service/Dockerfile`; inject all env vars
- [ ] Cloud DB — confirm non-prod DB reachable from Railway, or seed a demo Neon DB with anonymized data
- [ ] `README.md` — architecture diagram, Text-to-SQL demo (question → SQL → answer), RAG eval scores table
- [ ] Add project card to `portfolio` — stack, live URL, RAG eval scores as concrete quality signal
- [ ] LLM observability — integrate **Langfuse** for tracing Text-to-SQL + RAG calls; measure latency + token cost per query type

---

## Skill Checkpoints (workspace roadmap)

| Skill | Where practiced | Done? |
|---|---|---|
| Schema-aware prompting (Text-to-SQL) | Phase 2 — `schema_context/` + few-shot prompt | [ ] |
| LLM output validation / SQL safety guard | Phase 2 — `text_to_sql.py` validate + `EXPLAIN` dry-run | [ ] |
| Cross-DB query routing in application code | Phase 2 — `text_to_sql.py` DB router | [ ] |
| Chunking strategies for technical docs | Phase 3 — `chunker.py` (header-based + overlap) | [ ] |
| Embedding models (cloud vs local fallback) | Phase 3 — `embedder.py` (OpenAI / Ollama) | [ ] |
| Hybrid search — BM25 + vector + RRF | Phase 3 — `retriever.py` | [ ] |
| RAG evaluation (RAGAS faithfulness / context recall) | Phase 3 — `eval_rag.py` + golden QA dataset | [ ] |
| LLM tracing / observability | Phase 5 — Langfuse integration | [ ] |
