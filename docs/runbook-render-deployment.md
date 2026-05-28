# Runbook: Deploy AI Service to Render

**Service:** `ai-service` (FastAPI + Python 3.12)
**Target:** Render.com — Free tier (Web Service, Docker runtime)
**Author:** First deployment — 2026-05-29

---

## Free tier facts you need to know upfront

| | Free tier |
|---|---|
| Cost | $0 (no credit card required) |
| RAM | 512 MB |
| CPU | 0.1 shared CPU |
| Inactivity sleep | Spins down after **15 minutes** of no requests |
| Cold start | ~20–30 seconds on first request after sleep |
| Hours | 750 free hours/month (enough for one service 24/7) |
| Persistent disk | Not available on free tier — `rag_data/` and `portal_data.db` reset on every deploy |

The cold start delay is the main trade-off. For a portfolio project it is acceptable. If you demo it, hit the `/health` endpoint first to wake it up.

---

## Prerequisites

- [ ] Code pushed to GitHub (`thanhnv2210/ai-operations-portal`)
- [ ] Render account created at [render.com](https://render.com) — sign up with GitHub
- [ ] Anthropic API key available
- [ ] Database connection strings available
- [ ] Databases reachable from a public IP (see note in Railway runbook)

---

## Step 1 — Push deployment config to GitHub

The following files were added in the deployment setup session. Commit and push them if not done already:

```bash
cd /Users/ThanhNguyen/AI_WS/ai-operations-portal

git add \
  render.yaml \
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

git commit -m "Add deployment config: Railway + Render + Vercel"
git push
```

---

## Step 2 — Create the Web Service on Render

### Option A: Blueprint (render.yaml — recommended)

The `render.yaml` at the repo root tells Render exactly how to build and run the service.

1. Go to [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint**
2. Connect your GitHub account if not already connected
3. Select the repo `thanhnv2210/ai-operations-portal`
4. Render reads `render.yaml` and shows a preview of the service `ai-operations-portal-api`
5. Click **Apply** — Render creates the service and starts the first build

### Option B: Manual (via dashboard)

If you prefer to configure it yourself without the Blueprint:

1. Render dashboard → **New** → **Web Service**
2. Connect GitHub repo → `thanhnv2210/ai-operations-portal`
3. Fill in the fields:

   | Field | Value |
   |---|---|
   | **Name** | `ai-operations-portal-api` |
   | **Region** | Singapore (`sgp1`) — closest to your DBs |
   | **Branch** | `master` |
   | **Root Directory** | `ai-service` |
   | **Runtime** | `Docker` |
   | **Dockerfile Path** | `./Dockerfile` *(relative to root directory)* |
   | **Plan** | `Free` |

4. Click **Create Web Service**

---

## Step 3 — Set environment variables

After the service is created, go to the service → **Environment** tab → add each variable.

> **Never put secrets in `render.yaml`** — the file is committed to git. All sensitive values must be entered in the Render dashboard.

| Variable | Value |
|---|---|
| `APP_ENV` | `uat` |
| `ML_DB_URL` | `postgresql+asyncpg://<user>:<pass>@<host>:<port>/ml_db` |
| `KEYCLOAK_DB_URL` | `postgresql+asyncpg://<user>:<pass>@<host>:<port>/keycloak` |
| `ANTHROPIC_API_KEY` | `sk-ant-...` |
| `CORS_ORIGINS` | Set after Vercel deploy — see Step 6 |
| `OPENAI_API_KEY` | *(optional)* better RAG embeddings |
| `LANGFUSE_PUBLIC_KEY` | *(optional)* LLM tracing |
| `LANGFUSE_SECRET_KEY` | *(optional)* LLM tracing |

After saving variables, Render automatically triggers a redeploy.

---

## Step 4 — Monitor the build

1. Service → **Events** tab — shows build progress
2. Service → **Logs** tab — shows live container output

A successful first start looks like:
```
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

If the build takes more than 10 minutes, check the logs for pip install errors.

---

## Step 5 — Verify deployment

Render assigns a URL automatically:
```
https://ai-operations-portal-api.onrender.com
```

Find it in the service dashboard at the top. Test the health endpoint:

```bash
curl https://ai-operations-portal-api.onrender.com/health
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

> If the service is sleeping (first request after 15 min idle), the curl will hang for ~20–30 seconds then succeed. That is normal on the free tier.

---

## Step 6 — Update CORS after Vercel deploy

Once the frontend is deployed to Vercel and you have its URL (e.g. `https://ai-ops-portal.vercel.app`):

1. Render dashboard → service → **Environment**
2. Add or update:
   ```
   CORS_ORIGINS=["https://ai-ops-portal.vercel.app"]
   ```
3. Save — Render redeploys automatically

---

## Step 7 — Run RAG ingest (one-time, required for Knowledge Base)

Render's free tier does not have a persistent disk, so `rag_data/` (ChromaDB) is empty after every deploy. The Knowledge Base page will show no results until ingest runs.

**Using Render Shell** (easiest — no CLI needed):

1. Render dashboard → service → **Shell** tab
2. In the terminal that opens, run:
   ```bash
   python -m app.rag.ingest
   ```

Expected output:
```
Loaded 1 file(s)
Split into 51 chunks
Embedded 51 chunks
Upserted to ChromaDB collection: ai_ops_portal_docs
Ingestion complete. doc_count=51
```

> The Shell tab spins up a temporary container alongside your running service — it does not interrupt live traffic.

**Using Render CLI** (alternative):

```bash
npm install -g @render-oss/cli
render login
render shell <service-name>
python -m app.rag.ingest
```

> **Important:** Because there is no persistent disk on the free tier, you need to re-run this after every deploy if you want the Knowledge Base to work. Upgrade to a paid Render plan and mount a disk at `/app/rag_data` to avoid this.

---

## Step 8 — Auto-deploy on git push

Render auto-deploys every time you push to `master` by default. To change this:

Service → **Settings** → **Build & Deploy** → toggle **Auto-Deploy** off if you want manual control.

To trigger a manual deploy:
- Dashboard: **Manual Deploy** → **Deploy latest commit**
- Or: push a new commit to `master`

---

## Keeping the service warm (optional)

The free tier sleeps after 15 minutes of inactivity. To prevent this during demos, you can use a free uptime service like UptimeRobot to ping `/health` every 10 minutes.

1. Go to [uptimerobot.com](https://uptimerobot.com) → create a free account
2. Add a new monitor: **HTTP(s)**, URL = `https://ai-operations-portal-api.onrender.com/health`
3. Set interval to **10 minutes**

This keeps the service awake 24/7 within the 750 free hours/month limit.

---

## Troubleshooting

### Build fails with "No space left on device"

The free tier has limited build cache. Go to service → **Settings** → **Clear build cache** → redeploy.

### Service starts but crashes immediately

Check **Logs** tab. Common causes:
- Missing required env var (`APP_ENV`, `ML_DB_URL`, `KEYCLOAK_DB_URL`, `ANTHROPIC_API_KEY`)
- DB unreachable — logs will show `asyncpg.exceptions.ConnectionDoesNotExistError`

### `/health` returns `"ml_db": "error"` or `"keycloak_db": "error"`

The DB connection string is wrong or the host is not reachable from Render's network. Double-check:
1. The URL format: `postgresql+asyncpg://user:pass@host:port/dbname`
2. The host allows connections from `0.0.0.0/0` (or Render's IP range)
3. Port is correct — your local DB is on `54320`, not the default `5432`

### `CORS_ORIGINS` rejected by browser

The value must be a valid JSON array string:
```
["https://your-app.vercel.app"]
```
Check for typos — missing `https://`, trailing slash, or wrong domain.

### Knowledge Base returns empty / "not enough context"

RAG ingest was not run or was reset by a redeploy. Use the Shell tab to re-run:
```bash
python -m app.rag.ingest
```

---

## Summary of deployed URLs

| Component | URL |
|---|---|
| AI Service (Render) | `https://ai-operations-portal-api.onrender.com` ✅ |
| Health check | `https://ai-operations-portal-api.onrender.com/health` ✅ |
| Frontend (Vercel) | TBD — deploy with `docs/runbook-vercel-deployment.md` |

---

## Related docs

- [`docs/runbook-railway-deployment.md`](runbook-railway-deployment.md) — Railway alternative (paid, no cold start)
- [`docs/environment-verification.md`](environment-verification.md) — verify local environment
- [`README.md`](../README.md) — full deployment overview
