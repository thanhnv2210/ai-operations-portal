# Environment Verification Checklist

Run this top-to-bottom before starting a dev session or after a machine restart to confirm everything is wired up correctly.

---

## 1. Prerequisites

```bash
node --version          # expect: v20.x or higher
python3.12 --version    # expect: 3.12.x
docker --version        # expect: 24.x or higher
docker compose version  # expect: v2.x
```

---

## 2. Databases (Neon — `dash`)

All schemas (ml_schema, service_management, remittance, customer, payment) now live in a single Neon database called **`dash`**. Both `ML_DB_URL` and `KEYCLOAK_DB_URL` in `.env.local` point to it.

```bash
DASH_URL="postgresql://neondb_owner:<password>@ep-dry-cherry-aoh661hd.c-2.ap-southeast-1.aws.neon.tech/dash?sslmode=require"

psql "$DASH_URL" -c "SELECT 1 AS ok;"
```

Spot-check data presence:
```bash
psql "$DASH_URL" -c "
  SELECT 'country'          AS tbl, COUNT(*) FROM ml_schema.country
  UNION ALL
  SELECT 'external_partner',         COUNT(*) FROM service_management.external_partner
  UNION ALL
  SELECT 'remit_service',            COUNT(*) FROM service_management.remit_service
  UNION ALL
  SELECT 'transaction',              COUNT(*) FROM remittance.transaction;"
```

Expected: 250 countries, 4 partners, 112 services, 2000+ transactions.

**Re-seed if empty:**
```bash
cd ai-service
python scripts/seed_dummy_data.py \
  --ml-db-url      "postgresql://..." \
  --keycloak-db-url "postgresql://..."
```

---

## 3. AI Service (port 8000)

```bash
# Health check
curl -s http://localhost:8000/health | python3 -m json.tool

# RAG status (should show chunk count > 0 if knowledge base is ingested)
curl -s http://localhost:8000/api/v1/rag/status | python3 -m json.tool
```

Expected `/health` response:
```json
{"status": "ok", "env": "local", "cache": {"loaded": true, "countries": 250, "services": 112, "partners": 4}}
```

Expected `/api/v1/rag/status` response (after ingest):
```json
{"status": "ready", "chunk_count": 201, ...}
```

If the service is not running, start it:
```bash
cd ai-service
.venv/bin/uvicorn app.main:app --reload --port 8000
```

**Note:** The venv must be built with **Python 3.12** (`python3.12 -m venv .venv`). Python 3.13+ breaks `pydantic-core` and `greenlet`.

**Interactive API docs:** http://localhost:8000/docs

---

## 4. Frontend (port 3007)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:3007
# expect: 200
```

If not running:
```bash
cd frontend
npm run dev
# or: aiops-start
```

---

## 5. Langfuse — LLM Observability (port 3020)

Langfuse is **optional** — AI pipelines run without it. Only verify if you need trace visibility.

```bash
# Container status
docker compose -f infrastructure/docker-compose.langfuse.yml ps

# HTTP reachability
curl -s -o /dev/null -w "%{http_code}" http://localhost:3020
# expect: 200
```

Expected container output:
```
infrastructure-langfuse-1     running   0.0.0.0:3020->3000/tcp
infrastructure-langfuse-db-1  running (healthy)
```

If not running:
```bash
docker compose -f infrastructure/docker-compose.langfuse.yml up -d
```

**UI:** http://localhost:3020

---

## 6. Ollama — Local Embeddings (optional)

Required only if `OPENAI_API_KEY` is **not** set in `.env.local`. Used for RAG embeddings.

```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool | grep nomic
# expect: "nomic-embed-text" in the list
```

If model is missing:
```bash
ollama pull nomic-embed-text
```

---

## 7. Environment Variables

```bash
# Check required vars are present in .env.local (no actual values shown)
grep -E "^(APP_ENV|ML_DB_URL|KEYCLOAK_DB_URL|ANTHROPIC_API_KEY)" ai-service/.env.local
```

All four must be present and non-empty. `ANTHROPIC_API_KEY` must start with `sk-ant-`.

Optional Langfuse vars (needed to activate tracing):
```bash
grep -E "^LANGFUSE_" ai-service/.env.local
# expect: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
```

---

## 8. Knowledge Base Ingest

The RAG knowledge base must be ingested at least once after checkout, or after any edit to `docs/database-design.md`.

```bash
# Check if already ingested
curl -s http://localhost:8007/api/v1/rag/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if d.get('chunk_count',0) > 0 else 'NOT INGESTED')"
```

If not ingested:
```bash
cd ai-service
source .venv/bin/activate
python -m app.rag.ingest
# expect: "Ingested N chunks into ChromaDB"
```

---

## 9. Run Tests

```bash
# Frontend — Vitest (29 tests)
cd frontend && npm test -- --run

# AI service — pytest (101 tests)
cd ai-service && source .venv/bin/activate && pytest
```

Both suites must pass before pushing.

---

## Quick Status Summary

Run this one-liner to get a birds-eye view:

```bash
echo "=== Ports ===" && \
  for port in 8000 3007 3020 11434; do \
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:$port 2>/dev/null); \
    echo "  :$port -> HTTP $status"; \
  done && \
echo "=== Neon dash DB ===" && \
  curl -s http://localhost:8000/health | python3 -m json.tool && \
echo "=== Langfuse ===" && \
  docker compose -f infrastructure/docker-compose.langfuse.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null
```

---

## Port Reference

| Port  | Service                        | Start command |
|-------|--------------------------------|---------------|
| 3007  | Frontend (React + Vite)        | `cd frontend && npm run dev` |
| 8000  | AI Service (FastAPI)           | `cd ai-service && .venv/bin/uvicorn app.main:app --reload --port 8000` |
| 3020  | Langfuse (LLM tracing)         | `docker compose -f infrastructure/docker-compose.langfuse.yml up -d` |
| 11434 | Ollama (local embeddings)      | `ollama serve` |

> Local PostgreSQL (`localhost:54320`) is no longer used. All DB traffic goes to Neon (`dash`).
