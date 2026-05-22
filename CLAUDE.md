# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI Operations Portal — an AI-assisted operational intelligence platform for enterprise transactional systems with natural language analytics and decision support. Targets fintech/remittance/BPM domains.

## Planned Architecture

This project is in the initial setup phase. The repository structure follows a monorepo with three main services:

```
frontend/       # React + Vite + TailwindCSS + shadcn/ui
backend/        # Spring Boot (Java 21) monolith with modular package structure
ai-service/     # Python FastAPI for AI/LLM integration
database/       # PostgreSQL schema, migrations, seeds
infrastructure/ # Docker Compose, deployment configs
docs/           # Architecture, API docs, prompt engineering
```

## Tech Stack

**Frontend:** React 19, Vite 8, TailwindCSS v4, shadcn/ui, @base-ui/react, Recharts, TypeScript 5.9

**Backend (AI Service):** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async + asyncpg), Alembic, Uvicorn

**AI:** Anthropic SDK (`anthropic`), Claude Opus 4.6 as primary LLM with adaptive thinking; Ollama/Mistral as local fallback

**Database:** PostgreSQL (asyncpg driver) — two existing production databases (see `docs/database-design.md`)

- `ml_db` (localhost:54320, admin/admin non-prod): `ml_schema` (reference data) + `service_management` (corridor config)
- `keycloak` (same host): `remittance`, `customer`, `payment`, `portal`, `ekyc` schemas

**Testing:** Vitest + @testing-library/react (frontend); pytest (backend)

**Infrastructure:** Docker Compose, Vercel (frontend), Render/Railway (backend), Neon (DB)

## Data Sources

This portal reads from two existing production databases. Full schema in `docs/database-design.md`.

| DB | Schema | Key Tables | Use in Portal |
|---|---|---|---|
| `ml_db` | `ml_schema` | `country`, `mobile_operator`, `ml_fx_rates`, `issuer_ml` | Reference/lookup data |
| `ml_db` | `service_management` | `remit_service`, `remit_corridor_reference`, `external_partner` | Corridor/service config |
| `keycloak` | `remittance` | `transaction`, `transaction_aud` | **Primary operational data** |
| `keycloak` | `customer` | `beneficiary`, `beneficiary_service` | Recipient profiles |
| `keycloak` | `payment` | `ml_m_sof_payment`, `m_ml_tokenized_card` | Payment/SOF records |
| `keycloak` | `portal` | `user`, `roles`, `workflow_requests`, `action_request` | Portal users & approvals |
| `keycloak` | `ekyc` | `ekyc_data`, `ekyc_reference` | Customer KYC identity |

**Primary query target for dashboards:** `remittance.transaction` — filter by `status`, `created_date`, `service_id`, `hub_id`.

**Transaction amount fields:** `remittance_amount` (sender), `recipient_amount` (destination), `retail_fee` (charged).

**PII columns** (sender/recipient MSISDN, names, DOB, account numbers) — mask in logs and AI prompts.

**Hubs:** TELEPIN, WU (Western Union), THUNES, TRANGLO — stored in `service_management.external_partner`.

## Key Modules / Features

1. **Operational Dashboard** — transaction counts, failures, processing time, alert metrics
2. **AI Assistant** — natural language queries over operational data
3. **Transaction Explorer** — filtering, search, audit timeline, status tracking
4. **AI Insights Engine** — summaries, anomaly explanations, recommendations, trend observations
5. **Admin Configuration** — AI prompts, thresholds, alert rules

## Development Strategy

- **Phase 1 (MVP):** `frontend/` + `backend/` + `database/` + `docker-compose.yml` only. Skip Kubernetes, RAG, embeddings, advanced monitoring.
- **Phase 2:** Add `ai-service/`, prompts engineering, analytics, AI summaries.
- **Phase 3:** Event-driven (Kafka), vector DB, AI agents, microservice extraction.

Start with prompt-based LLM intelligence (no ML training). Use LLMs to summarize, explain anomalies, and generate operational insights.

## Commands (to be added as services are scaffolded)

### Frontend
```bash
cd frontend
npm install
npm run dev       # development server
npm run build     # production build
npm run lint
```

### Backend / AI Service
```bash
cd ai-service
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload       # development server (port 8000)
pytest                              # all tests
pytest tests/path/test_file.py::test_name  # single test
```

Required env vars — all environments:

| Variable | Description |
|---|---|
| `APP_ENV` | `local` / `ci` / `uat` / `prod` |
| `ML_DB_URL` | Non-secure DB (ml_db) asyncpg connection string |
| `KEYCLOAK_DB_URL` | Secure DB (keycloak) asyncpg connection string |
| `ANTHROPIC_API_KEY` | Anthropic API key |

Environment-specific `.env` files (never committed):
```
.env.local   # developer local machine
.env.ci      # CI pipeline (injected by CI system)
.env.uat     # UAT deployment
```

Local example values:
```
APP_ENV=local
ML_DB_URL=postgresql+asyncpg://admin:admin@localhost:54320/ml_db
KEYCLOAK_DB_URL=postgresql+asyncpg://admin:admin@localhost:54320/keycloak
```

Config is loaded via `pydantic-settings` (`BaseSettings`). The active `.env` file is selected by `APP_ENV` at startup. CI and UAT inject env vars directly — no `.env` file needed in those environments.

### Infrastructure
```bash
docker-compose up -d   # start all services locally
docker-compose down
```
