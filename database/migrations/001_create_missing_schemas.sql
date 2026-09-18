-- Migration: Create ml_schema and payment schemas with their tables
-- Run against: Neon UAT (same DB as keycloak / service_management)
-- Idempotent: uses IF NOT EXISTS throughout

-- ── ml_schema ────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS ml_schema;

CREATE TABLE IF NOT EXISTS ml_schema.country (
    id               INTEGER PRIMARY KEY,
    country_id       INTEGER,
    country_name     VARCHAR(50),
    country_iso_code VARCHAR(3),
    isd_code         VARCHAR(3),
    currency_iso     VARCHAR(5)
);

CREATE TABLE IF NOT EXISTS ml_schema.mobile_operator (
    id                  INTEGER PRIMARY KEY,
    operator_id         INTEGER,
    operator_name       VARCHAR(128),
    operator_name_hiapp VARCHAR(148),
    iso_code            VARCHAR(3),
    country_id          INTEGER,
    country_name        VARCHAR(25),
    operator_code       VARCHAR,
    default_issuer_id   INTEGER
);

CREATE TABLE IF NOT EXISTS ml_schema.ml_fx_rates (
    id                   INTEGER PRIMARY KEY,
    brand_id             VARCHAR(20),
    from_currency        VARCHAR(20),
    to_currency          VARCHAR(20),
    fx_rate              NUMERIC(24, 12),
    service_id           INTEGER,
    receiving_country_id VARCHAR(20)
);

-- ── payment ───────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS payment;

CREATE TABLE IF NOT EXISTS payment.ml_m_sof_payment (
    payment_id               VARCHAR PRIMARY KEY,
    internal_transaction_id  BIGINT,
    card_id                  VARCHAR(40),
    payment_amount           NUMERIC(20, 9),
    status                   VARCHAR,
    refund_initiated_by      VARCHAR
);
