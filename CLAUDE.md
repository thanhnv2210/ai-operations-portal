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

## Current Goal — Dummy Data Generation

**Objective:** Generate realistic dummy data for both databases so the portal UI shows meaningful, representative data at `aiops.thanhnguyen.dev` — useful for demos and the ACS PCE Group 2 evidence bundle.

### Why dummy data is needed
The local databases (`localhost:54320`) have real production data that cannot be shared or shown in screenshots. The deployed app on Render/Neon currently has no data, so the dashboard shows empty states. We need a seed script that populates Neon with realistic (but fake) transactional data across all 4 hubs.

### Seed script location
`ai-service/scripts/seed_dummy_data.py` — to be created.

Run against Neon (UAT DB):
```bash
cd ai-service
source .venv/bin/activate
# Set UAT DB URLs in env or pass as args
python scripts/seed_dummy_data.py
```

### What to generate

**ml_db — ml_schema (reference/lookup data)**
- `country`: ~10 rows — SGD source + key destinations: Philippines (PHP), Indonesia (IDR), India (INR), Bangladesh (BDT), Vietnam (VND), China (CNY), Thailand (THB), Malaysia (MYR)
- `mobile_operator`: ~20 rows — banks and wallets per destination country (e.g. BDO/GCash for PH, BCA/GoPay for ID, SBI/HDFC for IN)
- `ml_fx_rates`: ~40 rows — one rate per service_id (SGD → each destination currency, realistic rates)

**ml_db — service_management**
- `external_partner`: 4 rows — TELEPIN (id=1), THUNES (id=2), TRANGLO (id=3), WU (id=4)
- `remit_service`: ~30 rows — corridors per hub:
  - TELEPIN: SG→PH bank, SG→PH wallet, SG→ID bank, SG→ID wallet, SG→VN bank
  - THUNES: SG→IN bank, SG→BD bank, SG→TH bank, SG→CN wallet
  - TRANGLO: SG→PH bank, SG→ID bank, SG→MY bank
  - WU: SG→PH cash pickup, SG→BD cash pickup, SG→IN cash pickup
  - Status mix: ~80% ACTIVATE, ~20% INACTIVE (matches real migration pattern)

**keycloak — remittance**
- `transaction`: ~500–1000 rows spanning last 90 days
  - Realistic status distribution: ~75% COMPLETED, ~10% FAILED (mix of failure types), ~8% PROCESSING, ~7% REFUNDED/CANCELLED
  - Hub distribution roughly: TELEPIN 40%, THUNES 25%, TRANGLO 20%, WU 15%
  - Remittance amounts: SGD 50–500 range (realistic for SG remittance)
  - Daily volume pattern: weekday peak, weekend dip
  - Include realistic errors for FAILED rows: hub timeout, invalid account, insufficient funds
- `transaction_aud`: 2–4 audit rows per transaction (status change trail)

**keycloak — customer**
- `beneficiary`: ~50 rows — fake names, phone numbers, bank accounts (masked/fake only)

**keycloak — payment**
- `ml_m_sof_payment`: ~1 row per completed transaction — PayNow/NETS_CLICK mix

### Terminal status values (for COMPLETED transactions)
```
TRANSACTION_COMPLETED
```
### Key failed terminal statuses to seed
```
TRANSACTION_FAILED, SOF_PAY_FAILED, HUB_TIMEOUT, PAYMENT_RESERVED_FAILED
```

### Constraints
- Use `asyncpg` or `psycopg2` — match existing `ai-service/` stack
- All PII fields (sender_msisdn, sender_fullname, recipient_msisdn, recipient_fullname) must be **fake only** — use Faker library
- Insert in FK order: reference tables first, then transactions
- Script must be idempotent (skip or truncate+reseed)
- Target DB: Neon (UAT) — connection strings from `.env.local` or CLI args

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
