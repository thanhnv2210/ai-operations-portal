# AI Operations Portal — Project Proposal

## Vision

An AI-assisted operational intelligence platform for enterprise transactional systems. Bridges existing operational data with natural language analytics and decision support — targeting fintech, remittance, and BPM domains.

Positioning: "Senior backend/platform engineer integrating AI into enterprise operational systems." Not a pure AI product — a practical operational platform that embeds AI where it delivers real value.

## MVP Scope

| Module | Description |
|---|---|
| Operational Dashboard | Transaction counts, failure rates, processing time, alert metrics |
| AI Assistant | Natural language queries: "Why did failures spike today?" |
| Transaction Explorer | Filter, search, audit timeline, status tracking |
| AI Insights Engine | Auto-generated summaries, anomaly explanations, trend observations |
| Admin Configuration | AI prompts, alert thresholds, rule management |

## Architecture

```
frontend/       React 19 + Vite 8 + TailwindCSS v4 + shadcn/ui
ai-service/     Python FastAPI — REST API + LLM integration
docs/           Architecture decisions, API contracts, prompt library
infrastructure/ Docker Compose, deployment configs
```

The backend is a Python FastAPI service (not a Java monolith). This matches the working pattern established in job-evolution and enables faster AI iteration.

**No new database schema needed for MVP.** The portal reads directly from two existing production PostgreSQL databases.

## Data Sources

Full schema documented in `docs/database-design.md`.

**`ml_db`** — product/config data (host: localhost:54320, user: admin)
- `ml_schema` — master reference data: countries, mobile operators, FX rates, issuers
- `service_management` — remittance corridor config: services, fees, partners, field mappings

**`keycloak`** — transactional/secure data (same host)
- `remittance.transaction` — **primary dashboard source**: 65+ columns, 50+ status values, full lifecycle audit
- `customer.beneficiary` — recipient profiles per sender
- `payment.ml_m_sof_payment` — source-of-funds payment records (NETS, PayNow)
- `portal.*` — internal users, RBAC, maker-checker workflows
- `ekyc.ekyc_data` — customer KYC/identity verification

**Key facts for dashboard design:**
- Transaction amounts: `remittance_amount` (sender), `recipient_amount` (destination), `retail_fee` (fee charged)
- Payment hubs: TELEPIN, WU, THUNES, TRANGLO (stored in `service_management.external_partner`)
- Failure signals: `error_code`, `hub_error_code`, `fraud_status`, `hub_status`/`hub_sub_status`
- Full history: `remittance.transaction_aud` (Hibernate Envers, `rev`+`revtype` per change)
- PII fields (MSISDN, names, DOB, account numbers) must be masked in AI prompts and logs

## Evolution Roadmap

- **Phase 1 (MVP):** Prompt-based AI, REST APIs, dashboard + insights
- **Phase 2:** RAG with operational documents, AI-generated alerts, workflow recommendations
- **Phase 3:** Event streaming (Kafka), vector DB, AI agents, multi-tenant

---

## Standard Notes: Building New Applications in This Workspace

These are the confirmed conventions from existing projects (`job-evolution`). Follow them when building new services.

### Python Backend (FastAPI)

- Use **FastAPI** with `lifespan` context manager for startup/shutdown logic (not deprecated `@app.on_event`).
- Use **Pydantic v2** for all request/response models and data validation.
- Use **SQLAlchemy 2 async** (`AsyncSession`, `async_sessionmaker`, `create_async_engine`) with **asyncpg** driver. Never use sync SQLAlchemy in async FastAPI routes.
- Database URL format: `postgresql+asyncpg://user:pass@host:port/db`
- Use **Alembic** for all schema migrations.
- Run `load_dotenv()` before any local imports that read env vars at module level.
- Use a module-level logger: `log = logging.getLogger(__name__)`.
- Manage concurrency for LLM calls with `asyncio.Semaphore`; respect Anthropic rate limits (default concurrency: 5, override via `SCORER_CONCURRENCY` env var pattern).

### AI / LLM Integration

- **Primary model:** `claude-opus-4-6` via `anthropic.AsyncAnthropic` with streaming (`client.messages.stream`).
- Enable **adaptive thinking**: `thinking={"type": "adaptive"}`.
- Always set generous timeouts: `connect=30s, read=600s, write=30s` — streaming with thinking can take minutes.
- **Fallback pattern:** catch `anthropic.BadRequestError` for credit exhaustion, fall back to local Ollama (OpenAI-compatible endpoint at `/v1/chat/completions`).
- Prompts must request plain JSON output — no markdown fences. Strip fences defensively on Ollama responses.
- Lazy-initialize the Anthropic client (singleton) to avoid creating it at import time.

### Frontend (React)

- **React 19**, **Vite 8**, **TailwindCSS v4** (use `@tailwindcss/vite` plugin, not the legacy PostCSS plugin).
- **shadcn/ui** + **@base-ui/react** for components. Use `lucide-react` for icons, `recharts` for data viz.
- Path alias `@/` maps to `src/`. Use it consistently.
- **Vitest** + `@testing-library/react` + `jsdom` for all component tests. Run with `vitest run` for CI.
- Dev server runs on port 3001 (`vite --port 3001`). Backend CORS must whitelist `localhost:3001`.
- Use **React Context** for shared selection/filter state across components.
- No React Query in job-evolution — evaluate whether to add it based on data-fetching complexity.

### Multi-Environment Configuration

The application supports `local`, `ci`, and `uat` environments. Environment is set via `APP_ENV`.

**Environment variable files:**
```
.env.local    # local developer machine — committed as .env.local.example (no secrets)
.env.ci       # CI pipeline — env vars injected by CI system, no file needed
.env.uat      # UAT — env vars injected by deployment, no file needed
```

**Required variables per environment:**

| Variable | local | ci | uat |
|---|---|---|---|
| `APP_ENV` | `local` | `ci` | `uat` |
| `ML_DB_URL` | localhost:54320/ml_db | CI DB endpoint | UAT DB endpoint |
| `KEYCLOAK_DB_URL` | localhost:54320/keycloak | CI DB endpoint | UAT DB endpoint |
| `ANTHROPIC_API_KEY` | personal key | CI secret | UAT secret |

**Config loading pattern** (pydantic-settings `BaseSettings`):
- Local: reads from `.env.local`
- CI/UAT: reads directly from injected environment variables (no file)
- `APP_ENV` is always required; startup fails fast if missing

**`.gitignore` must exclude:** `.env.local`, `.env.ci`, `.env.uat`, `.env`

### Database Access (Two Existing DBs)

- Connect to **two separate async engines**: `ML_DB_URL` (ml_db) and `KEYCLOAK_DB_URL` (keycloak).
- Both use `postgresql+asyncpg://` driver. SQLAlchemy models are **read-only** — this portal never writes to the source DBs.
- Cross-DB joins are not possible at DB level; resolve in application code by querying each DB and joining in Python.
- Use `schema=` parameter in SQLAlchemy `Table`/`mapped_class` definitions (e.g. `schema="remittance"`, `schema="service_management"`).
- Local non-prod values: `postgresql+asyncpg://admin:admin@localhost:54320/{ml_db|keycloak}`

### Project Structure

- Keep `requirements.txt` pinned to exact versions (no `>=` ranges) for reproducibility.
- `.env` file for local secrets; never commit. Load via `python-dotenv`.
- In-memory caching on top of DB: load at startup, write-through on updates. Pre-populate cache on startup by querying DB for latest records.
