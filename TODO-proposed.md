# TODO — AI Operations Portal (Proposed)

> Last updated: 2026-05-28
> **Learning goal:** Text-to-SQL (Phase 2) → RAG Pipeline (Phase 3). Both skills target AI Engineer / Solution Architect roles per the workspace roadmap.

## Status Overview

| Area | Status |
|---|---|
| Project scaffolding (dirs, React, Docker) | Done |
| ai-service foundation (FastAPI + async DB) | Done |
| SQLAlchemy read models | Done |
| Reference data cache | Done |
| Operational Dashboard (APIs + frontend) | Done |
| Transaction Explorer (APIs + frontend) | Done |
| AI chat + Insights Engine (basic context-injection) | Done |
| Schema context layer (for Text-to-SQL) | Not started |
| Text-to-SQL pipeline | Not started |
| RAG pipeline | Not started |
| Deployment | Not started |

---

## Already Implemented — Reference for Reuse

> These are complete and working. Do not rebuild them. Extend only if needed.

### ai-service Foundation
- `app/main.py` — FastAPI with `lifespan`, CORS for `localhost:3001`
- `app/config.py` — pydantic-settings `BaseSettings`, multi-env `.env.local` / CI / UAT
- `app/database.py` — two `create_async_engine` instances: `ML_DB_URL` + `KEYCLOAK_DB_URL`; async sessionmakers as FastAPI `Depends`
- `app/cache.py` — in-memory reference data (countries, services, partners) loaded at startup
- `GET /health` — pings both DB connections; returns cache stats

### SQLAlchemy Read Models
- `app/models/remittance.py` — `remittance.transaction` (65 cols), `transaction_aud`, `TransactionStatus` enum, `FAILED_STATUSES`, `TERMINAL_STATUSES`
- `app/models/service_management.py` — `remit_service`, `external_partner`
- `app/models/ml_schema.py` — `country`, `mobile_operator`, `issuer_ml`, `ml_fx_rates`
- `app/models/customer.py` — `beneficiary`, `beneficiary_service`
- `app/models/payment.py` — `ml_m_sof_payment`
- `app/cross_db.py` — Python-level join helpers for cross-engine queries

### Operational Dashboard (routers/dashboard.py)
- `GET /api/v1/dashboard/overview` — totals, failure rate, volume
- `GET /api/v1/dashboard/volume-trend` — hourly/daily trend (Recharts line)
- `GET /api/v1/dashboard/status-distribution` — all statuses grouped
- `GET /api/v1/dashboard/processing-time` — p50/p95 in seconds
- `GET /api/v1/dashboard/hub-breakdown` — per-hub failure rate + volume

### Transaction Explorer (routers/transactions.py)
- `GET /api/v1/transactions` — paginated, filterable by status / hub / service / date
- `GET /api/v1/transactions/{id}` — single transaction detail
- `GET /api/v1/transactions/{id}/history` — audit timeline from `transaction_aud`

### AI Chat + Insights Engine (routers/ai.py)
- `POST /api/v1/ai/chat` — context-injection approach: fetches live aggregate stats, streams them to Claude for narrative answers
- `POST /api/v1/ai/insights` — structured JSON response (summary, health, anomalies, recommendations)
- `app/prompts.py` — `build_context()`, `nl_query_messages()`, `insights_messages()`
- `app/llm.py` — Anthropic streaming + non-streaming client; `asyncio.Semaphore(5)` concurrency guard; Ollama fallback on `BadRequestError` / `AuthenticationError`

### Frontend (src/)
- `pages/Dashboard.tsx` — metric cards + Recharts charts
- `pages/TransactionExplorer.tsx` — filter bar + results table + detail drawer
- `pages/AiAssistant.tsx` — chat panel consuming SSE
- `components/` — `FilterBar`, `MetricCard`, `VolumeChart`, `StatusDistributionChart`, `HubBreakdownTable`, `TransactionDrawer`, `StatusBadge`

---

## Phase 2 — Text-to-SQL (Core Skill #1)

> **Skill target:** Schema-aware NL→SQL, LLM output validation, hallucinated column detection, cross-DB query routing.
> Differentiator: real enterprise fintech schema (`remittance.transaction` 65 columns, corridor config, FX rates) — not toy data.
>
> **This is additive.** The existing `/api/v1/ai/chat` (context-injection) stays untouched. Text-to-SQL is a new endpoint for arbitrary data questions.

### Schema Context Layer
> The quality of Text-to-SQL is entirely determined by what schema context the LLM receives.

- [ ] `app/schema_context/loader.py` — build compact schema string for LLM prompts from existing models:
  - **Whitelist** query-safe tables only: `remittance.transaction`, `service_management.remit_service`, `service_management.external_partner`, `ml_schema.country`, `ml_schema.ml_fx_rates`
  - **Strip PII columns**: `sender_msisdn`, `sender_fullname`, `sender_dob`, `sender_email`, `recipient_msisdn`, `recipient_fullname`, `recipient_dob`
  - Format: `table_name(col: type — note, ...)` — one table per line
- [ ] `app/schema_context/status_ref.py` — `TransactionStatus` enum values grouped by phase (Payment, SOF, Remittance, Refund, Fraud) as a lookup string injected into every prompt; reuse `TransactionStatus` from existing `app/models/remittance.py`
- [ ] `app/schema_context/relationships.py` — cross-schema join hints: e.g. `remittance.transaction.service_id → service_management.remit_service.remit_service_id`

### Text-to-SQL Pipeline
- [ ] `app/services/text_to_sql.py` — full NL→SQL→result→explanation flow:
  - **Step 1:** Build schema context (whitelisted tables, PII-stripped, status enum, join hints)
  - **Step 2:** Send to `claude-opus-4-6`; prompt specifies SELECT-only, PostgreSQL dialect, schema-qualified table names, few-shot examples. Use standard (non-thinking) mode by default — extended thinking is too slow for interactive use.
  - **Step 3:** Validate SQL — reject if contains `INSERT`, `UPDATE`, `DELETE`, `DROP`, `CREATE`, `TRUNCATE`; run `EXPLAIN` dry-run before executing to catch syntax/column errors
  - **Step 4:** Route DB — `remittance.*` / `customer.*` / `payment.*` → keycloak engine; `ml_schema.*` / `service_management.*` → ml_db engine; cross-DB → query both engines, join in Python (reuse `app/cross_db.py`)
  - **Step 5:** Send raw result rows + original question back to Claude for a plain-English 2–4 sentence explanation
- [ ] Streaming — `client.messages.stream` + FastAPI `StreamingResponse` with `text/event-stream`; emit typed SSE events:
  ```
  data: {"type": "status", "text": "Generating SQL..."}
  data: {"type": "sql", "sql": "SELECT ..."}
  data: {"type": "status", "text": "Executing query..."}
  data: {"type": "token", "text": "There were..."}   ← streamed explanation tokens
  data: [DONE]
  ```
- [ ] Structured error types: `sql_generation_failed` / `sql_validation_rejected` / `db_execution_error` / `no_results`; emit as `{"type": "error", "code": "...", "message": "..."}`
- [ ] `app/routers/assistant.py` — `POST /api/v1/assistant/query` body: `{ "question": str }`, streamed SSE response
- [ ] Few-shot SQL examples in prompt:
  - "How many transactions failed today?" → `SELECT COUNT(*) FROM remittance.transaction WHERE status LIKE '%FAILED%' AND created_date::date = CURRENT_DATE`
  - "Failure rate by hub this month?" → group by `hub_name`, count success vs failed
  - "Top 5 corridors by volume this week?" → join `remittance.transaction` + `service_management.remit_service` on `service_id`
  - "Most common error codes last 7 days?" → group by `error_code` on `remittance.transaction`

### Frontend — AI Assistant (Text-to-SQL tab)
- [ ] `src/pages/AiAssistant.tsx` — add a "Text-to-SQL" tab alongside the existing chat; keep existing chat untouched
- [ ] Streaming render — consume SSE by `type`:
  - `status` → show a spinner with the status text
  - `sql` → render collapsible `<code>` block with generated SQL
  - `token` → stream explanation text in real time
  - `error` → show friendly message per code (`sql_validation_rejected`: "I can only run read queries")
- [ ] Example question chips: "How many failures today?", "Top corridors this week", "Failure rate by hub"

---

## Phase 3 — RAG Pipeline (Core Skill #2)

> **Skill target:** Technical doc chunking, embedding models (local + cloud), hybrid search (BM25 + vector + RRF), RAG eval with RAGAS.
> Corpus: `docs/database-design.md` + operational runbooks. Real fintech schema docs — not Wikipedia or PDFs.

### Vector Store Setup
- [ ] Add to `requirements.txt`: `chromadb`, `rank-bm25`, `ragas`; add `openai` as **optional** — only needed if `OPENAI_API_KEY` is set (embeddings); full Ollama fallback when unset
- [ ] `app/rag/store.py` — ChromaDB client; persist to `./rag_data/`; collection: `ai_ops_portal_docs`
- [ ] `app/rag/embedder.py` — `text-embedding-3-small` (OpenAI) when `OPENAI_API_KEY` present; batch up to 100 chunks per call
  - Local fallback: Ollama `nomic-embed-text` at `localhost:11434/v1` when `OPENAI_API_KEY` unset
- [ ] Add `OPENAI_API_KEY` (optional) to `.env.local.example`

### Document Ingestion
- [ ] `app/rag/ingestion/chunker.py` — Markdown chunking strategy:
  - Split on `##` / `###` headers — section title becomes chunk metadata
  - Max chunk: 500 tokens, 50-token overlap between adjacent chunks
  - Metadata per chunk: `{ source_file, section_title, table_name }` — extract `table_name` when header matches `schema.table` pattern
- [ ] `app/rag/ingestion/loader.py` — load: `docs/database-design.md` (primary), future runbooks/ADRs
- [ ] `app/rag/ingestion/ingest.py` — CLI: `python -m app.rag.ingest` — load → chunk → embed → upsert; print chunk count
- [ ] `GET /api/v1/rag/status` — return `{ doc_count, last_ingested_at, collection_name }`

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
- [ ] `POST /api/v1/rag/query` — body: `{ "question": str }`, response: `{ answer, sources }`

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
- [ ] `src/pages/KnowledgeBase.tsx` — separate page from AI Assistant (shows source citations)
- [ ] Answer panel + source cards — each retrieved chunk as collapsible card with `section_title` + snippet
- [ ] Example questions: "What tables contain transaction data?", "How does the payment flow work?"

---

## Phase 4 — Deployment & Portfolio Polish

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
| Cross-DB query routing in application code | Phase 2 — `text_to_sql.py` DB router + `cross_db.py` | [ ] |
| Chunking strategies for technical docs | Phase 3 — `chunker.py` (header-based + overlap) | [ ] |
| Embedding models (cloud vs local fallback) | Phase 3 — `embedder.py` (OpenAI / Ollama) | [ ] |
| Hybrid search — BM25 + vector + RRF | Phase 3 — `retriever.py` | [ ] |
| RAG evaluation (RAGAS faithfulness / context recall) | Phase 3 — `eval_rag.py` + golden QA dataset | [ ] |
| LLM tracing / observability | Phase 4 — Langfuse integration | [ ] |
