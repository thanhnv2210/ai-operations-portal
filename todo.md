# AI Operations Portal — TODO

## Phase 1: Foundation
- [x] Project scaffolding (dirs, .gitignore)
- [x] todo.md created
- [x] FastAPI ai-service setup
  - [x] `requirements.txt`
  - [x] `app/config.py` — pydantic-settings, multi-env (local/ci/uat)
  - [x] `app/database.py` — two async engines (ML_DB_URL + KEYCLOAK_DB_URL)
  - [x] `app/main.py` — FastAPI lifespan, CORS, health check
  - [x] `.env.local.example`
- [x] React frontend bootstrap
  - [x] Vite + React 19 + TypeScript
  - [x] TailwindCSS v4 (`@tailwindcss/vite` plugin)
  - [x] Path alias `@/` → `src/`
  - [x] Dev port 3001
  - [x] Vitest + @testing-library/react + jsdom
- [x] Docker Compose (local dev)

## Phase 2: Data Layer
- [x] SQLAlchemy read models
  - [x] `remittance.transaction` (65 columns, TransactionStatus enum)
  - [x] `service_management.remit_service` + `external_partner`
  - [x] `ml_schema` reference models (country, mobile_operator, issuer_ml, ml_fx_rates)
  - [x] `customer.beneficiary` + `beneficiary_service`
  - [x] `payment.ml_m_sof_payment`
- [x] Cross-DB join helpers (Python-level)
- [x] In-memory reference data cache (countries, operators, services)

## Phase 3: Operational Dashboard
- [x] API: transaction volume + failure rate by time window + hub
- [x] API: processing time percentiles (p50/p95)
- [x] API: status distribution breakdown
- [x] Frontend: metric cards + Recharts charts
- [x] Frontend: hub/service filter controls

## Phase 4: Transaction Explorer
- [x] API: paginated search (status, date range, service, hub, error_code)
- [x] API: single transaction detail
- [x] API: transaction audit history (`transaction_aud`)
- [x] Frontend: filter panel + results table
- [x] Frontend: transaction detail drawer with audit timeline

## Phase 5: AI Assistant + Insights Engine
- [x] Anthropic client (streaming, adaptive thinking, Ollama fallback)
- [x] Prompt templates: summary, anomaly explanation, trend observation
- [x] API: natural language query endpoint
- [x] API: AI insights generation (on-demand)
- [x] Frontend: AI chat panel
- [x] Frontend: insights display

## Phase 6: Admin Configuration
- [x] API: CRUD for prompt templates + alert thresholds
- [x] Frontend: config form UI
