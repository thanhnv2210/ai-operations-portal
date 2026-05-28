# Runbook: Migrate Local Databases to Neon

**Purpose:** Move `ml_db` and `keycloak` databases from `localhost:54320` to Neon (free tier cloud PostgreSQL) so the deployed app on Render can reach them.

**Author:** First migration — 2026-05-29

---

## Strategy

| Database | Schemas | What to migrate |
|---|---|---|
| `ml_db` | `ml_schema`, `service_management` | Schema + **all data** (reference data, no PII) |
| `keycloak` | `remittance` | Schema + **anonymized sample** (500 transactions, PII masked) |
| `keycloak` | `customer`, `payment`, `ekyc` | **Schema only**, no data (app shows empty — acceptable for demo) |
| `keycloak` | `portal` | **Skip** — portal users are internal; not needed for demo |

The portal query history DB (`portal_data.db`) stays as SQLite — it resets on every Render deploy anyway.

---

## Neon free tier facts

| | Value |
|---|---|
| Cost | $0 |
| Projects | 1 |
| Databases per project | Unlimited |
| Storage | 500 MB |
| Compute | Autoscales to zero when idle (similar to Render) |
| Connection limit | 20 concurrent connections |

One Neon project can hold both `ml_db` and `keycloak` as separate databases — same host, different database names in the connection string.

---

## Prerequisites

- [ ] Neon account at [neon.tech](https://neon.tech) — sign up with GitHub
- [ ] Local databases running on `localhost:54320`
- [ ] `pg_dump` and `psql` installed locally (`brew install libpq` if missing)
- [ ] Render service created (from Render runbook)

Check tools:
```bash
pg_dump --version
psql --version
```

If missing:
```bash
brew install libpq
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"   # already in ~/.zshrc
```

---

## Step 1 — Create Neon project and databases

### 1a — Create the project

1. Go to [console.neon.tech](https://console.neon.tech) → **New Project**
2. Name: `ai-operations-portal`
3. Region: `AWS / ap-southeast-1` (Singapore — closest to your data)
4. PostgreSQL version: `16`
5. Click **Create Project**

Neon creates a default database called `neondb`. You will rename/replace this with your own databases.

### 1b — Create `ml_db` database

In the Neon dashboard → **Databases** tab → **New Database**:
- Database name: `ml_db`
- Owner: `neondb_owner` (default)

### 1c — Create `keycloak` database

Same step:
- Database name: `keycloak`
- Owner: `neondb_owner`

### 1d — Get connection strings

Go to **Dashboard** → **Connection Details**. Switch the database dropdown between `ml_db` and `keycloak` to get each string. They look like:

```
postgresql://neondb_owner:<password>@ep-xxx-yyy.ap-southeast-1.aws.neon.tech/ml_db?sslmode=require
```

Copy both. You will need them in Step 5.

**Convert to asyncpg format** (replace `postgresql://` with `postgresql+asyncpg://`):
```
postgresql+asyncpg://neondb_owner:<password>@ep-xxx-yyy.ap-southeast-1.aws.neon.tech/ml_db?sslmode=require
postgresql+asyncpg://neondb_owner:<password>@ep-xxx-yyy.ap-southeast-1.aws.neon.tech/keycloak?sslmode=require
```

---

## Step 2 — Export schemas from local

Create a working directory for the migration files:
```bash
mkdir -p /tmp/neon-migration && cd /tmp/neon-migration
```

### 2a — `ml_db` schema (both schemas)

```bash
PGPASSWORD=admin pg_dump \
  -h localhost -p 54320 -U admin \
  --schema-only \
  --schema=ml_schema \
  --schema=service_management \
  --no-owner --no-privileges \
  ml_db > ml_db_schema.sql

echo "ml_db schema lines: $(wc -l < ml_db_schema.sql)"
```

### 2b — `keycloak` schema (remittance + customer + payment + ekyc)

```bash
PGPASSWORD=admin pg_dump \
  -h localhost -p 54320 -U admin \
  --schema-only \
  --schema=remittance \
  --schema=customer \
  --schema=payment \
  --schema=ekyc \
  --no-owner --no-privileges \
  keycloak > keycloak_schema.sql

echo "keycloak schema lines: $(wc -l < keycloak_schema.sql)"
```

---

## Step 3 — Export data

### 3a — `ml_db` reference data (full — no PII)

```bash
PGPASSWORD=admin pg_dump \
  -h localhost -p 54320 -U admin \
  --data-only \
  --schema=ml_schema \
  --schema=service_management \
  --no-owner \
  ml_db > ml_db_data.sql

echo "ml_db data lines: $(wc -l < ml_db_data.sql)"
```

### 3b — `remittance.transaction` anonymized sample

PII columns (`sender_msisdn`, `sender_fullname`, `sender_dob`, `sender_email`, `recipient_msisdn`, `recipient_fullname`, `recipient_dob`) are replaced with placeholder values. Only the last 500 transactions are exported.

```bash
PGPASSWORD=admin psql \
  -h localhost -p 54320 -U admin -d keycloak \
  -c "\COPY (
    SELECT
      id,
      transaction_ref,
      status,
      service_id,
      hub_id,
      hub_ref,
      hub_transaction_id,
      error_code,
      error_message,
      remittance_amount,
      recipient_amount,
      retail_fee,
      currency_iso,
      recipient_currency_iso,
      'DEMO_SENDER'        AS sender_msisdn,
      'Demo Sender'        AS sender_fullname,
      NULL                 AS sender_dob,
      NULL                 AS sender_email,
      'DEMO_RECIPIENT'     AS recipient_msisdn,
      'Demo Recipient'     AS recipient_fullname,
      NULL                 AS recipient_dob,
      created_date,
      updated_date,
      created_by,
      updated_by
    FROM remittance.transaction
    ORDER BY created_date DESC
    LIMIT 500
  ) TO STDOUT WITH CSV HEADER" > transaction_sample.csv

echo "Transaction rows exported: $(wc -l < transaction_sample.csv)"
```

> **Note:** The SELECT above covers the most commonly used columns. If your `remittance.transaction` has more columns, the COPY import will fail with a column mismatch. Adjust the column list to match your actual schema. Check with:
> ```bash
> PGPASSWORD=admin psql -h localhost -p 54320 -U admin -d keycloak \
>   -c "\d remittance.transaction"
> ```

---

## Step 4 — Import into Neon

Set your Neon connection strings as shell variables (replace with your actual values):

```bash
NEON_ML="postgresql://neondb_owner:<password>@ep-xxx.ap-southeast-1.aws.neon.tech/ml_db?sslmode=require"
NEON_KC="postgresql://neondb_owner:<password>@ep-xxx.ap-southeast-1.aws.neon.tech/keycloak?sslmode=require"
```

### 4a — Create schemas on Neon

Neon databases start empty — schemas (`ml_schema`, `service_management`, `remittance`, etc.) must be created first:

```bash
psql "$NEON_ML" -c "CREATE SCHEMA IF NOT EXISTS ml_schema;"
psql "$NEON_ML" -c "CREATE SCHEMA IF NOT EXISTS service_management;"

psql "$NEON_KC" -c "CREATE SCHEMA IF NOT EXISTS remittance;"
psql "$NEON_KC" -c "CREATE SCHEMA IF NOT EXISTS customer;"
psql "$NEON_KC" -c "CREATE SCHEMA IF NOT EXISTS payment;"
psql "$NEON_KC" -c "CREATE SCHEMA IF NOT EXISTS ekyc;"
```

### 4b — Import `ml_db` schema

```bash
psql "$NEON_ML" -f ml_db_schema.sql
echo "ml_db schema imported"
```

### 4c — Import `ml_db` data

```bash
psql "$NEON_ML" -f ml_db_data.sql
echo "ml_db data imported"
```

### 4d — Import `keycloak` schema

```bash
psql "$NEON_KC" -f keycloak_schema.sql
echo "keycloak schema imported"
```

### 4e — Import transaction sample

```bash
psql "$NEON_KC" -c "\COPY remittance.transaction FROM '/tmp/neon-migration/transaction_sample.csv' WITH CSV HEADER"
echo "Transactions imported"
```

---

## Step 5 — Verify the import

```bash
# ml_db — check row counts
psql "$NEON_ML" -c "SELECT 'country' AS tbl, COUNT(*) FROM ml_schema.country
  UNION ALL SELECT 'mobile_operator', COUNT(*) FROM ml_schema.mobile_operator
  UNION ALL SELECT 'ml_fx_rates', COUNT(*) FROM ml_schema.ml_fx_rates
  UNION ALL SELECT 'remit_service', COUNT(*) FROM service_management.remit_service
  UNION ALL SELECT 'external_partner', COUNT(*) FROM service_management.external_partner;"

# keycloak — check transaction count
psql "$NEON_KC" -c "SELECT COUNT(*) AS transactions FROM remittance.transaction;"
```

Expected: reference tables have data, transactions show ~500 rows.

---

## Step 6 — Update Render environment variables

Go to the Render dashboard → your service → **Environment** tab. Update the two DB connection strings to the Neon asyncpg URLs:

```
ML_DB_URL=postgresql+asyncpg://neondb_owner:<password>@ep-xxx.ap-southeast-1.aws.neon.tech/ml_db?sslmode=require
KEYCLOAK_DB_URL=postgresql+asyncpg://neondb_owner:<password>@ep-xxx.ap-southeast-1.aws.neon.tech/keycloak?sslmode=require
```

Save → Render redeploys automatically.

---

## Step 7 — Verify end-to-end

After Render finishes redeploying:

```bash
curl https://ai-operations-portal-api.onrender.com/health
```

Expected:
```json
{
  "status": "ok",
  "ml_db": "connected",
  "keycloak_db": "connected"
}
```

Then open the deployed frontend and confirm:
- Dashboard loads with data (transaction counts, hub breakdown)
- Transaction Explorer shows the 500 sample rows
- AI Assistant can answer questions about the data

---

## Troubleshooting

### `pg_dump: error: connection to server failed: FATAL: password authentication failed`

Your local DB password is wrong. Try without the password flag:
```bash
psql -h localhost -p 54320 -U admin -d ml_db
```
If it asks for a password, use `admin`. If it connects without password, remove `PGPASSWORD=admin` from the commands.

### `psql: error: connection to server ... SSL connection required`

The `?sslmode=require` is missing from the Neon URL. Make sure your connection string ends with `?sslmode=require`.

### `ERROR: schema "ml_schema" does not exist`

You skipped Step 4a. Run the `CREATE SCHEMA` commands first, then re-run the import.

### `ERROR: column "..." of relation "transaction" does not exist` on COPY

Your `remittance.transaction` has different columns than what the sample SELECT lists. Check the actual columns:
```bash
PGPASSWORD=admin psql -h localhost -p 54320 -U admin -d keycloak \
  -c "SELECT column_name FROM information_schema.columns WHERE table_schema='remittance' AND table_name='transaction' ORDER BY ordinal_position;"
```
Then adjust the SELECT in Step 3b to match.

### `ERROR: duplicate key value violates unique constraint`

You ran the import twice. Clear the tables and re-import:
```bash
psql "$NEON_ML" -c "TRUNCATE ml_schema.country, ml_schema.mobile_operator, ml_schema.ml_fx_rates CASCADE;"
psql "$NEON_ML" -f ml_db_data.sql
```

### Render `/health` shows `"ml_db": "error"` after updating env vars

1. Check the URL is in `postgresql+asyncpg://` format (not `postgresql://`)
2. Check `?sslmode=require` is at the end
3. Check Render logs for the specific asyncpg error

### Neon free tier: `max_connections` exceeded

Neon free tier allows 20 connections. The app's pool is already capped at 2–3 for UAT mode. If you see connection errors, confirm `APP_ENV=uat` is set (not `local`, which uses a larger pool).

---

## Keeping Neon data current (optional)

The sample data is static — it will not reflect new transactions from the live system. For a demo project this is fine. Options if you want fresher data:

1. **Re-run the export/import** from the same steps whenever you want to refresh
2. **Direct connection:** if your databases become publicly accessible, update the Render env vars to point directly to `localhost:54320` via an SSH tunnel or a public endpoint

---

## Related docs

- [`docs/runbook-render-deployment.md`](runbook-render-deployment.md) — deploy ai-service to Render
- [`docs/environment-verification.md`](environment-verification.md) — verify local environment
- [`README.md`](../README.md) — full deployment overview
