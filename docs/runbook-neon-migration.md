# Runbook: Neon Database Setup (`dash`)

**Purpose:** Set up the `dash` Neon database for UAT/demo with production-accurate schema and realistic seed data.

**Last updated:** 2026-09-20

---

## Overview

All schemas live in a single Neon database called **`dash`** (same endpoint, both `ML_DB_URL` and `KEYCLOAK_DB_URL` point to it):

| Schema | Contents |
|---|---|
| `ml_schema` | `country`, `mobile_operator`, `ml_fx_rates` — reference/lookup data |
| `service_management` | `external_partner`, `remit_service` — hub & corridor config |
| `remittance` | `transaction`, `transaction_aud` — transaction lifecycle |
| `customer` | `beneficiary` — recipient profiles |
| `payment` | `ml_m_sof_payment`, `overseas_payment_transactions` — SOF payments |

---

## Prerequisites

```bash
psql --version    # need psql client
python3.12 --version
```

Connection string (replace `<password>` with actual value from `.env.local`):
```
DASH_URL="postgresql://neondb_owner:<password>@ep-dry-cherry-aoh661hd.c-2.ap-southeast-1.aws.neon.tech/dash?sslmode=require"
```

---

## Step 1 — Create the `dash` database

> Skip if already created.

```bash
# Connect to the default neondb and create dash
psql "postgresql://neondb_owner:<password>@ep-dry-cherry-aoh661hd.c-2.ap-southeast-1.aws.neon.tech/neondb?sslmode=require" \
  -c "CREATE DATABASE dash;"
```

---

## Step 2 — Apply the production DDL

The production-accurate schema is in `database/schema_dash.sql` (sourced from `tmp/2026_09_20_db_structure.sql`):

```bash
psql "$DASH_URL" -f database/schema_dash.sql
```

Verify:
```bash
psql "$DASH_URL" -c "
SELECT schemaname, tablename FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog','information_schema')
ORDER BY schemaname, tablename;"
```

Expected: 10 tables across 5 schemas.

---

## Step 3 — Load production reference data

Reference and config data (countries, operators, hubs, corridors) from `tmp/2026_09_20_db_data_init.sql`:

```bash
psql "$DASH_URL" -f tmp/2026_09_20_db_data_init.sql
```

Verify:
```bash
psql "$DASH_URL" -c "
SELECT 'country'          AS tbl, COUNT(*) FROM ml_schema.country
UNION ALL SELECT 'mobile_operator',  COUNT(*) FROM ml_schema.mobile_operator
UNION ALL SELECT 'external_partner', COUNT(*) FROM service_management.external_partner
UNION ALL SELECT 'remit_service',    COUNT(*) FROM service_management.remit_service;"
```

Expected: 250 / 47 / 4 / 112.

---

## Step 4 — Seed transaction data

Generates ~2,000 realistic fake transactions spanning 14 months with hub migration story:

```bash
cd ai-service

# Ensure venv uses Python 3.12
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run seed
python scripts/seed_dummy_data.py \
  --ml-db-url       "$DASH_URL" \
  --keycloak-db-url "$DASH_URL"
```

Expected output:
```
[1/3] Seeding ml_schema.ml_fx_rates …  ✓ Inserted 39 fx rate rows
[2/3] Building transaction dataset …   Generated: 2153 tx | 8400 aud | 1695 sof
[3/3] Seeding keycloak …               ✓ keycloak: 2153 tx | 8400 aud | 1695 sof
✅ Seed complete.
```

The seed script is idempotent — re-running truncates and reseeds transactional tables only. Reference data (`ml_fx_rates` is also reseeded; `country`, `remit_service` etc. are untouched).

---

## Step 5 — Configure `.env.local`

Both DB URLs must use the `+asyncpg` driver and point to `dash`:

```
ML_DB_URL=postgresql+asyncpg://neondb_owner:<password>@ep-dry-cherry-aoh661hd.c-2.ap-southeast-1.aws.neon.tech/dash?sslmode=require
KEYCLOAK_DB_URL=postgresql+asyncpg://neondb_owner:<password>@ep-dry-cherry-aoh661hd.c-2.ap-southeast-1.aws.neon.tech/dash?sslmode=require
```

> The app's `database.py` strips `sslmode` from the URL and passes `ssl=True` to asyncpg — no manual handling needed.

---

## Step 6 — Start services and verify

```bash
# Backend (port 8000)
cd ai-service && .venv/bin/uvicorn app.main:app --reload --port 8000

# Frontend (port 3007)
cd frontend && npm run dev
```

Health check:
```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected:
```json
{
  "status": "ok",
  "env": "local",
  "cache": {"loaded": true, "countries": 250, "services": 112, "partners": 4}
}
```

Dashboard API smoke test:
```bash
curl -s "http://localhost:3007/api/v1/dashboard/overview" | python3 -m json.tool
```

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'psycopg2'`
The DB URL is missing `+asyncpg`. Add it: `postgresql+asyncpg://...`

### `pydantic-core` or `greenlet` build failure during `pip install`
The venv is using Python 3.13+. Recreate with Python 3.12:
```bash
rm -rf .venv && python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

### `Bad Gateway` on frontend
The Vite proxy in `frontend/vite.config.ts` must point to port `8000`:
```ts
proxy: { '/api': 'http://localhost:8000' }
```

### `ERROR: duplicate key value` when running seed
Tables already have data. The seed script handles this automatically (truncates before reinserting transactional tables).

### `ERROR: relation "..." does not exist`
Schema not applied yet. Run Step 2 first.

---

## Related docs

- [`database/schema_dash.sql`](../database/schema_dash.sql) — production DDL
- [`ai-service/scripts/seed_dummy_data.py`](../ai-service/scripts/seed_dummy_data.py) — transaction seed script
- [`docs/dummy_data_seed_plan.md`](dummy_data_seed_plan.md) — seed data design
- [`docs/environment-verification.md`](environment-verification.md) — full env checklist
- [`docs/runbook-render-deployment.md`](runbook-render-deployment.md) — deploy to Render
