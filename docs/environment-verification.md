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

## 2. Databases (localhost:54320)

Both `ml_db` and `keycloak` must be reachable. These are read-only sources — the portal never writes to them.

```bash
# ml_db — reference data, corridor config
psql postgresql://admin:admin@localhost:54320/ml_db -c "SELECT 1 AS ok;"

# keycloak DB — transactions, customers, payments
psql postgresql://admin:admin@localhost:54320/keycloak -c "SELECT 1 AS ok;"
```

Expected output for both: a single row with `ok = 1`.

Spot-check data presence:
```bash
psql postgresql://admin:admin@localhost:54320/keycloak \
  -c "SELECT COUNT(*) FROM remittance.transaction LIMIT 1;"

psql postgresql://admin:admin@localhost:54320/ml_db \
  -c "SELECT COUNT(*) FROM service_management.external_partner;"
```

**Troubleshooting:** If the DB is not reachable, start it with whatever local Docker/service manages it (not part of this repo).

---

## 3. AI Service (port 8007)

```bash
# Health check
curl -s http://localhost:8007/health | python3 -m json.tool

# RAG status (should show chunk count > 0 if knowledge base is ingested)
curl -s http://localhost:8007/api/v1/rag/status | python3 -m json.tool
```

Expected `/health` response:
```json
{"status": "ok"}
```

Expected `/api/v1/rag/status` response (after ingest):
```json
{"status": "ready", "chunk_count": 51, ...}
```

If the service is not running, start it:
```bash
cd ai-service
source .venv/bin/activate
uvicorn app.main:app --reload --port 8007
# or: aiops-start
```

**Interactive API docs:** http://localhost:8007/docs

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
  for port in 8007 3007 3020 11434; do \
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:$port 2>/dev/null); \
    echo "  :$port -> HTTP $status"; \
  done && \
echo "=== DB ===" && \
  psql postgresql://admin:admin@localhost:54320/ml_db -c "SELECT 1 AS ml_db_ok;" -t 2>/dev/null | head -1 && \
  psql postgresql://admin:admin@localhost:54320/keycloak -c "SELECT 1 AS keycloak_ok;" -t 2>/dev/null | head -1 && \
echo "=== Langfuse ===" && \
  docker compose -f infrastructure/docker-compose.langfuse.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null
```

---

## Port Reference

| Port  | Service                        | Start command |
|-------|--------------------------------|---------------|
| 3007  | Frontend (React + Vite)        | `cd frontend && npm run dev` |
| 8007  | AI Service (FastAPI)           | `uvicorn app.main:app --reload --port 8007` |
| 3020  | Langfuse (LLM tracing)         | `docker compose -f infrastructure/docker-compose.langfuse.yml up -d` |
| 11434 | Ollama (local embeddings)      | `ollama serve` |
| 54320 | PostgreSQL (ml_db + keycloak)  | managed externally |
