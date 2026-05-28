# Runbook: Deploy Frontend to Vercel

**Service:** `frontend` (React + Vite + TailwindCSS)
**Target:** Vercel (free tier)
**Live URL:** `https://aiops.thanhnguyen.dev`
**AI Service URL:** `https://ai-operations-portal-api.onrender.com`
**Author:** First deployment — 2026-05-29
**Status:** Deployed ✅

---

## Vercel free tier facts

| | Value |
|---|---|
| Cost | $0 |
| Builds | 100 per day |
| Bandwidth | 100 GB/month |
| Serverless functions | Not used — pure static SPA |
| Custom domain | Supported on free tier |
| Auto-deploy | Every push to `master` |

---

## Prerequisites

- [ ] Code pushed to GitHub (`thanhnv2210/ai-operations-portal`)
- [ ] Vercel account at [vercel.com](https://vercel.com) — sign up with GitHub
- [ ] Render AI service is live: `https://ai-operations-portal-api.onrender.com/health`

---

## Step 1 — Import project on Vercel

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **Continue with GitHub** → authorize Vercel to access your repos
3. Find `thanhnv2210/ai-operations-portal` → click **Import**
4. Configure the project:

   | Field | Value |
   |---|---|
   | **Project Name** | `ai-operations-portal` *(or any name you prefer)* |
   | **Framework Preset** | `Vite` *(Vercel should auto-detect)* |
   | **Root Directory** | `frontend` |
   | **Build Command** | `npm run build` *(auto-filled)* |
   | **Output Directory** | `dist` *(auto-filled)* |
   | **Install Command** | `npm install` *(auto-filled)* |

   > **Root Directory is critical.** Click **Edit** next to Root Directory and type `frontend`. If you skip this, Vercel tries to build from the repo root and fails.

---

## Step 2 — Set environment variable

Still on the same import screen, expand **Environment Variables** and add:

| Key | Value |
|---|---|
| `VITE_API_URL` | `https://ai-operations-portal-api.onrender.com` |

This tells the frontend where to send API requests. It is baked into the JavaScript bundle at build time — if you change it later, you must redeploy.

---

## Step 3 — Deploy

Click **Deploy**. Vercel runs:
```
npm install
npm run build   # tsc -b && vite build
```

A successful build output looks like:
```
dist/index.html                   1.29 kB
dist/assets/index-xxx.css        35.02 kB
dist/assets/index-xxx.js        629.28 kB
✓ built in ~320ms
```

First deploy takes ~1–2 minutes. Vercel assigns a URL:
```
https://ai-operations-portal-<hash>.vercel.app
```

---

## Step 4 — Verify the deployment

Open the Vercel URL in a browser and check each page:

| Page | What to verify |
|---|---|
| Dashboard | Date range picker — set `2025-09-01` → `2026-04-30` to see data |
| Transaction Explorer | Filter by date range above — should show 175 transactions |
| AI Assistant | Send a message — response may be slow on first call (Render cold start) |
| Knowledge Base | Ask "What tables contain transaction data?" — should return cited answer |
| Admin Config | Page loads without errors |

---

## Step 5 — Update CORS on Render

Now that you have the Vercel URL, restrict the AI service to accept requests only from it.

1. Go to [dashboard.render.com](https://dashboard.render.com) → `ai-operations-portal-api` → **Environment**
2. Update `CORS_ORIGINS`:
   ```
   ["https://aiops.thanhnguyen.dev"]
   ```
3. Click **Save Changes** — Render redeploys automatically

> Until this is done, `CORS_ORIGINS=["*"]` is active — the API accepts requests from any origin. Update it promptly.

---

## Step 6 — Update README live URLs

README has been updated with the live URLs:
- Frontend: `https://aiops.thanhnguyen.dev`
- AI Service: `https://ai-operations-portal-api.onrender.com`

---

## Automatic deploys

Vercel auto-deploys every push to `master`. To change this:

Vercel dashboard → project → **Settings** → **Git** → toggle **Production Branch** or disable auto-deploy.

Each deploy gets a unique preview URL — useful for testing before it goes live:
```
https://ai-operations-portal-git-<branch>-<user>.vercel.app
```

---

## Custom domain (optional)

Vercel dashboard → project → **Settings** → **Domains** → **Add Domain**.

Point your DNS `CNAME` to `cname.vercel-dns.com`. Vercel provisions TLS automatically.

---

## Troubleshooting

### Build fails: `Cannot find module` or TypeScript error

Check the Vercel build log. Most likely a missing `npm install` or a TypeScript error that was ignored locally. Run `npm run build` locally first to confirm it passes before deploying.

### `VITE_API_URL` not set — all API calls fail

The env var must be set **before** the build runs (it is inlined at build time by Vite). If you add it after deploying, trigger a **Redeploy** from the Vercel dashboard (not just a page refresh).

To redeploy: Vercel dashboard → project → **Deployments** → latest deployment → **Redeploy**.

### Dashboard shows all zeros

The default date range is the last 30 days. The Neon data runs from `2025-09-25` to `2026-04-16`. Set the date range manually to `2025-09-01 → 2026-04-30` to see data.

### API calls fail with CORS error in browser

The Render service has `CORS_ORIGINS` set to a value that doesn't include the Vercel domain. Update it in the Render dashboard (Step 5).

### AI Assistant / Text-to-SQL is slow on first response

The Render free tier sleeps after 15 minutes of inactivity. The first request after sleep takes ~20–30 seconds to wake up. Subsequent requests are fast. Set up UptimeRobot (see Render runbook) to keep it warm.

---

## Related docs

- [`docs/runbook-render-deployment.md`](runbook-render-deployment.md) — AI service on Render
- [`docs/runbook-neon-migration.md`](runbook-neon-migration.md) — database migration to Neon
- [`README.md`](../README.md) — full project overview and live URLs
