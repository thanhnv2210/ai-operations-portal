# AI Operations Portal

An AI-assisted operational intelligence platform for enterprise transactional systems. Provides natural language analytics, real-time dashboards, and AI-generated insights over remittance and fintech operational data — without requiring any new database schema.

## Features

| Module | Description |
|---|---|
| **Operational Dashboard** | Transaction counts, failure rates, processing time (p50/p95), hub breakdown |
| **Transaction Explorer** | Paginated search with filters, detail view, full audit timeline |
| **AI Assistant** | Natural language queries over live operational data (streaming) |
| **AI Insights Engine** | Auto-generated summaries, anomaly explanations, trend observations |
| **Admin Configuration** | Manage AI prompt templates and alert thresholds |

## Architecture

```
frontend/       React 19 + Vite 8 + TailwindCSS v4 — port 3007
ai-service/     Python FastAPI + SQLAlchemy async — port 8007
docs/           Database design, API contracts
infrastructure/ Docker Compose
```

The frontend proxies all `/api` requests to the ai-service. No separate backend — the FastAPI service handles everything.

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
npm test           # Vitest

# AI Service
pytest                                          # all tests
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
| POST | `/api/v1/ai/chat` | Streaming natural language query (SSE) |
| POST | `/api/v1/ai/insights` | Generate AI operational insights |
| GET/PUT | `/api/v1/admin/thresholds` | Alert threshold configuration |
| GET/POST | `/api/v1/admin/prompts` | Prompt template management |
| PUT/DELETE | `/api/v1/admin/prompts/{id}` | Update or delete a prompt template |

Interactive API docs available at `http://localhost:8007/docs` (local only).

## AI Integration

- **Primary:** `claude-opus-4-6` via Anthropic SDK with adaptive thinking and streaming
- **Fallback:** Ollama (Mistral) via OpenAI-compatible endpoint for local/offline use
- Prompt templates are user-configurable via the Admin panel and persisted to `ai-service/data/admin_config.json`
- PII fields (MSISDN, names, account numbers) are never included in AI prompts

## Multi-Environment Config

| Variable | Description |
|---|---|
| `APP_ENV` | `local` / `ci` / `uat` |
| `ML_DB_URL` | asyncpg connection string for ml_db |
| `KEYCLOAK_DB_URL` | asyncpg connection string for keycloak DB |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `OLLAMA_BASE_URL` | Ollama base URL (default: `http://localhost:11434`) |

CI and UAT inject environment variables directly — no `.env` file needed in those environments.
