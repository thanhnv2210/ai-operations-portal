# Dummy Data Seed Plan

**Generated:** 2026-09-18
**Script:** `ai-service/scripts/seed_dummy_data.py`
**Target DB:** Neon UAT (ML_DB_URL + KEYCLOAK_DB_URL from `.env.local`)
**Mode:** Truncate + full reseed (idempotent)

---

## Scope

| Item | Value |
|---|---|
| Date range | 2025-08-01 → 2026-10-01 (14 months) |
| Est. transactions | ~2,000–2,500 |
| Seed mode | Truncate all target tables, then reseed |
| PII | Faker only — no real data |

---

## Hub ID Mapping (from transaction.hub_id column comment)

| hub_id | Hub name |
|---|---|
| 1 | TELEPIN |
| 2 | WU |
| 3 | THUNES |
| 5 | TRANGLO |

> Note: external_partner_id (1=TELEPIN, 2=THUNES, 3=TRANGLO, 4=WU) differs from hub_id.

---

## Hub Migration Phases

| Phase | Period | TELEPIN | THUNES | TRANGLO | WU | Description |
|---|---|---|---|---|---|---|
| 1 | 2025-08-01 – 2025-09-30 | 100% | 0% | 0% | 0% | Baseline — TELEPIN only |
| 2 | 2025-10-01 – 2025-11-30 | 50% | 50% | 0% | 0% | Switch 50% traffic to THUNES |
| 3 | 2025-12-01 – 2026-01-31 | 30% | 60% | 10% | 0% | -10% TELEPIN→THUNES, -10% TELEPIN→TRANGLO |
| 4 | 2026-02-01 – 2026-03-31 | 30% | 40% | 10% | 20% | -20% THUNES→WU |
| 5 | 2026-04-01 – 2026-05-31 | 30% | 20% | 10% | 40% | -20% THUNES→WU |
| 6 | 2026-06-01 – 2026-07-31 | 10% | 0% | 10% | 80% | THUNES fully out, -20% TELEPIN→WU |
| 7 | 2026-08-01 – 2026-10-01 | 0% | 0% | 0% | 100% | All traffic on WU (target reached) |

---

## Daily Volume Baseline

| Day type | Base tx/day | Notes |
|---|---|---|
| Weekday | 5 | Mon–Fri |
| Weekend | 2 | Sat–Sun |
| Growth | +0.7%/week | ~3% MoM compound |
| Incident volume_mult | See table below | Overrides base |

---

## Incident Days (1 per month, 14 total)

| Date | Type | Affected Hub | fail_rate | volume_mult | Description |
|---|---|---|---|---|---|
| 2025-08-14 | HUB_TIMEOUT | TELEPIN | 35% | 1.0× | Hub timeout spike on TELEPIN |
| 2025-09-22 | MAINTENANCE | ALL | 0% | 0.2× | Scheduled maintenance window — volume drops to ~1–2 tx |
| 2025-10-08 | SOF_PAY_FAILED | THUNES | 40% | 1.0× | THUNES onboarding SOF failures |
| 2025-11-19 | FRAUD_CHECK_TIMEOUT | TELEPIN | 30% | 1.0× | Fraud check service timeout batch |
| 2025-12-03 | PAYMENT_RESERVATION_FAILED | ALL | 25% | 1.0× | Payment reservation failures across all hubs |
| 2026-01-15 | HUB_TIMEOUT | TRANGLO | 100% | 1.0× | TRANGLO API fully down — 0 successful TRANGLO txs |
| 2026-02-11 | TRANSACTION_FAILED | WU | 45% | 1.0× | WU onboarding errors — high failure rate |
| 2026-03-27 | TRANSACTION_DECLINED | THUNES | 50% | 1.0× | Invalid account batch — 50% THUNES declined |
| 2026-04-09 | VOLUME_SPIKE | ALL | 12% | 2.5× | Promo event — 2.5× volume, slightly elevated failures |
| 2026-05-21 | HUB_TIMEOUT | TELEPIN | 60% | 0.8× | TELEPIN sunset cutover — most txs fail, volume drops |
| 2026-06-16 | TRANSACTION_FAILED | WU | 35% | 1.0× | WU FX rate sync failure — txs rejected |
| 2026-07-04 | HUB_TIMEOUT | TRANGLO | 70% | 0.5× | TRANGLO final migration day — most txs fail |
| 2026-08-18 | VOLUME_SPIKE | WU | 8% | 3.0× | WU capacity test — 3× volume, low failure rate |
| 2026-09-05 | SOF_PAY_FAILED | WU | 40% | 1.0× | PayNow outage — SOF failures, recovers same day |

---

## Services Seeded

### TELEPIN (hub_id=1, ep_id=1) — all DEACTIVATE

| service_id | Corridor | Type |
|---|---|---|
| 101 | SG→PH | BANK-ACCOUNT |
| 102 | SG→PH | E-WALLET |
| 103 | SG→ID | BANK-ACCOUNT |
| 104 | SG→BD | CASH-PICKUP |
| 105 | SG→VN | BANK-ACCOUNT |

### THUNES (hub_id=3, ep_id=2) — all DEACTIVATE

| service_id | Corridor | Type |
|---|---|---|
| 201 | SG→PH | BANK-ACCOUNT |
| 202 | SG→ID | BANK-ACCOUNT |
| 203 | SG→BD | BANK-ACCOUNT |
| 204 | SG→VN | BANK-ACCOUNT |
| 205 | SG→IN | BANK-ACCOUNT |

### TRANGLO (hub_id=5, ep_id=3) — all DEACTIVATE

| service_id | Corridor | Type |
|---|---|---|
| 301 | SG→MY | BANK-ACCOUNT |
| 302 | SG→ID | BANK-ACCOUNT |
| 303 | SG→IN | BANK-ACCOUNT |
| 304 | SG→MY | E-WALLET |

### WU (hub_id=2, ep_id=4) — all ACTIVATE

| service_id | Corridor | Type |
|---|---|---|
| 401 | SG→PH | CASH-PICKUP |
| 402 | SG→IN | CASH-PICKUP |
| 403 | SG→BD | CASH-PICKUP |
| 404 | SG→PH | BANK-ACCOUNT |
| 405 | SG→PH | E-WALLET |
| 406 | SG→ID | BANK-ACCOUNT |
| 407 | SG→ID | E-WALLET |
| 408 | SG→BD | BANK-ACCOUNT |
| 409 | SG→BD | E-WALLET |
| 410 | SG→VN | BANK-ACCOUNT |
| 411 | SG→TH | BANK-ACCOUNT |
| 412 | SG→MY | E-WALLET |

---

## Transaction Status Distribution (normal day)

| Status | Weight | Terminal? |
|---|---|---|
| TRANSACTION_COMPLETED | 75% | Yes |
| TRANSACTION_IN_PROGRESS | 8% | No |
| REFUNDED | 4% | Yes |
| TRANSACTION_CANCELLED | 3% | Yes |
| TRANSACTION_FAILED | 5% | Yes |
| SOF_PAY_FAILED | 2% | Yes |
| TRANSACTION_FAILED (hub timeout) | 2% | Yes |
| PAYMENT_RESERVATION_FAILED | 1% | Yes |

---

## Transaction Amount Ranges (SGD)

| Destination | Min | Max | Avg |
|---|---|---|---|
| Philippines | 80 | 350 | 180 |
| Indonesia | 50 | 300 | 150 |
| India | 100 | 500 | 220 |
| Bangladesh | 80 | 300 | 160 |
| Vietnam | 50 | 250 | 130 |
| Thailand | 80 | 350 | 170 |
| Malaysia | 100 | 400 | 200 |

## FX Rates (SGD → destination, approximate)

| Currency | Rate |
|---|---|
| PHP | 41.50 |
| IDR | 11,500.00 |
| INR | 62.50 |
| BDT | 82.00 |
| VND | 18,500.00 |
| THB | 25.80 |
| MYR | 3.40 |

Retail markup: ~1.5% over wholesale rate.

---

## Tables Seeded (in FK order)

**ml_db:**
1. `service_management.external_partner` — 4 rows
2. `ml_schema.country` — 9 rows
3. `ml_schema.mobile_operator` — 20 rows
4. `service_management.remit_service` — 26 rows
5. `ml_schema.ml_fx_rates` — 26 rows (one per service)

**keycloak:**
6. `customer.beneficiary` — 50 rows
7. `remittance.transaction` — ~2,000–2,500 rows
8. `remittance.transaction_aud` — 2–4 rows per transaction
9. `payment.ml_m_sof_payment` — 1 row per COMPLETED/REFUNDED transaction

---

## Out of Scope

- `portal` schema (users, workflow_requests)
- `ekyc` schema
- `customer.beneficiary_service`
- `payment.m_ml_tokenized_card`
