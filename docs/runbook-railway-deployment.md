# Runbook: Deploy AI Service to Railway

**Service:** `ai-service` (FastAPI + Python 3.12)
**Target:** Railway.app
**Author:** First deployment — 2026-05-29

---

## Prerequisites

- [ ] Code pushed to GitHub (`thanhnv2210/ai-operations-portal`)
- [ ] Anthropic API key available
- [ ] Database connection strings available (ML_DB + Keycloak DB)
- [ ] Databases are reachable from a public IP (see note below)
- [ ] Railway account created at [railway.app](https://railway.app)

> **Database reachability:** Railway containers run in the cloud and connect to your databases over the public internet. Your databases must either have a public hostname with auth, or you need to whitelist Railway's outbound IPs. If databases are behind a VPN/private network only, this deployment approach won't work without a tunnel or proxy.

---

## Step 1 — Install Railway CLI

```bash
npm install -g @railway/cli
railway login
```

Login opens a browser. Authenticate with GitHub or email.

Verify:
```bash
railway --version
```

---

## Step 2 — Push deployment config to GitHub

The following files were added in this session. Ensure they are committed and pushed:

```bash
cd /Users/ThanhNguyen/AI_WS/ai-operations-portal

git add \
  ai-service/railway.json \
  ai-service/.dockerignore \
  frontend/vercel.json \
  frontend/nginx.conf \
  frontend/Dockerfile \
  frontend/src/lib/api.ts \
  frontend/src/hooks/useDashboard.ts \
  frontend/src/hooks/useTransactions.ts \
  frontend/src/hooks/useAi.ts \
  frontend/src/hooks/useTextToSql.ts \
  frontend/src/hooks/useQueryHistory.ts \
  frontend/src/pages/AdminConfig.tsx \
  frontend/src/pages/KnowledgeBase.tsx \
  README.md

git commit -m "Add deployment config: Railway + Vercel"
git push
```

---

## Step 3 — Create Railway project

### Option A: via Dashboard (recommended for first time)

1. Go to [railway.app/new](https://railway.app/new)
2. Click **Deploy from GitHub repo**
3. Authorize Railway to access your GitHub if prompted
4. Select `thanhnv2210/ai-operations-portal`
5. When asked for **Root Directory**, type: `ai-service`
   - Railway will find `ai-service/Dockerfile` and use it
6. Click **Deploy**

Railway starts the first build. It will likely fail — that is expected because environment variables are not set yet (Step 4).

### Option B: via CLI

```bash
cd /Users/ThanhNguyen/AI_WS/ai-operations-portal/ai-service
railway init          # creates a new project, follow prompts
railway up            # triggers first deploy
```

---

## Step 4 — Set environment variables

In the Railway dashboard: select the service → **Variables** tab → add each variable.

Or via CLI (faster):

```bash
railway variables set APP_ENV=uat
railway variables set ANTHROPIC_API_KEY=sk-ant-...
railway variables set ML_DB_URL="postgresql+asyncpg://<user>:<pass>@<host>:<port>/ml_db"
railway variables set KEYCLOAK_DB_URL="postgresql+asyncpg://<user>:<pass>@<host>:<port>/keycloak"
```

> `CORS_ORIGINS` is set after the Vercel frontend is deployed. For now you can skip it or set a placeholder — the service still works, CORS only matters for browser requests.

After setting variables, Railway automatically redeploys.

**Full variable reference:**

| Variable | Required | Description |
|---|---|---|
| `APP_ENV` | Yes | Set to `uat` — disables SQL echo and hides `/docs` |
| `ML_DB_URL` | Yes | asyncpg connection string for `ml_db` |
| `KEYCLOAK_DB_URL` | Yes | asyncpg connection string for `keycloak` DB |
| `ANTHROPIC_API_KEY` | Yes | Claude claude-opus-4-6 for SQL generation + RAG |
| `CORS_ORIGINS` | Yes (after Vercel) | e.g. `["https://your-app.vercel.app"]` |
| `OPENAI_API_KEY` | No | Better RAG embeddings (`text-embedding-3-small`); falls back to Ollama otherwise |
| `LANGFUSE_PUBLIC_KEY` | No | LLM observability traces |
| `LANGFUSE_SECRET_KEY` | No | LLM observability traces |
| `LANGFUSE_HOST` | No | Default: `https://cloud.langfuse.com` |

---

## Step 5 — Generate public domain

1. Railway dashboard → select service → **Settings** tab
2. Under **Networking**, click **Generate Domain**
3. Copy the URL: `https://ai-operations-portal-production.up.railway.app`

Save this URL — you will need it when deploying the frontend to Vercel (`VITE_API_URL`).

Or via CLI:
```bash
railway domain
```

---

## Step 6 — Verify deployment

```bash
curl https://<your-railway-url>.up.railway.app/health
```

Expected response:
```json
{
  "status": "ok",
  "ml_db": "connected",
  "keycloak_db": "connected",
  "cache": {
    "countries": 50,
    "services": 12,
    "partners": 4
  }
}
```

If either DB shows `"error"` instead of `"connected"`, the connection string is wrong or the DB is unreachable.

**Check deploy logs:**
```bash
railway logs
```

Or in the dashboard: service → **Deployments** → click a deployment → **View Logs**.

---

## Step 7 — Run RAG ingest (one-time, required for Knowledge Base)

The ChromaDB vector store (`rag_data/`) is not included in the Docker image (gitignored). Knowledge Base queries will return empty results until ingest is run.

```bash
# Link CLI to your project first (if not already done)
railway link

# Run ingest as a one-off command inside the running container
railway run python -m app.rag.ingest
```

Expected output:
```
Loaded 1 file(s)
Split into 51 chunks
Embedded 51 chunks
Upserted to ChromaDB collection: ai_ops_portal_docs
Ingestion complete. doc_count=51, last_ingested_at=...
```

> **Important:** `rag_data/` is stored inside the container filesystem on Railway. It will be **reset on every new deployment**. To persist it across deploys, mount a Railway Volume at `/app/rag_data`. Until then, re-run ingest after each deploy if you need the Knowledge Base to work.

---

## Step 8 — Re-run ingest after each deploy (if needed)

If you redeploy and want the Knowledge Base working again:

```bash
railway run python -m app.rag.ingest
```

---

## Troubleshooting

### Build fails: `pip install` errors

Check `requirements.txt` for packages that need system libraries (e.g. `psycopg2` vs `asyncpg`). The Dockerfile uses `python:3.12-slim` — if a build dependency is missing, add a `RUN apt-get install -y ...` line before the pip install step.

### Deploy starts but `/health` returns 500

Almost always a DB connection issue. Check:
1. `ML_DB_URL` and `KEYCLOAK_DB_URL` — are they correctly formatted?
2. Is the DB host reachable from Railway's network? Try connecting with `psql` from a machine with the same IP as Railway.
3. Check `railway logs` for the specific exception.

### `CORS_ORIGINS` not working

The value must be valid JSON:
```bash
railway variables set CORS_ORIGINS='["https://your-app.vercel.app"]'
```
Note the single quotes around the JSON array. Do not use double quotes around the outer string.

### RAG returns "Not enough relevant context"

The similarity threshold is 0.40. This means either:
- Ingest was not run (ChromaDB is empty) — run `railway run python -m app.rag.ingest`
- The question is too far from the ingested docs — expected behaviour

---

## Quick reference — Railway CLI commands

```bash
railway login                          # authenticate
railway link                           # link local directory to a Railway project
railway up                             # deploy current directory
railway logs                           # tail live logs
railway logs --tail 100                # last 100 lines
railway run <command>                  # run a command inside the deployed service
railway variables                      # list all env vars
railway variables set KEY=value        # set an env var (triggers redeploy)
railway domain                         # show the public URL
railway status                         # show project/service status
railway open                           # open the dashboard in browser
```

---

## Related docs

- [`docs/environment-verification.md`](environment-verification.md) — verify local environment is healthy
- [`README.md`](../README.md) — full deployment overview (Vercel + Railway + Docker)
