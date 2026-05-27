"""Schema context for Text-to-SQL prompts.

Builds a compact, PII-stripped, whitelisted schema string from the existing
SQLAlchemy models. This string is injected into every Text-to-SQL prompt so
Claude knows the exact column names, types, and semantics.

Whitelisted tables only — never expose PII columns or non-query-safe tables.
"""

_SCHEMA_CONTEXT = """\
=== DATABASE SCHEMA CONTEXT ===

Two separate PostgreSQL databases are in use. Generate SQL targeting ONE database per query.

Keycloak DB  — schemas: remittance, customer, payment
ML DB        — schemas: ml_schema, service_management

---

TABLE: remittance.transaction  [Keycloak DB]
  Primary operational table. One row per remittance attempt.

  internal_transaction_id  bigint          PRIMARY KEY
  hub_id                   bigint          FK → service_management.external_partner.external_partner_id
  hub_name                 varchar(255)    Hub name snapshot: TELEPIN | WU | THUNES | TRANGLO
  service_id               bigint          FK → service_management.remit_service.remit_service_id
  service_name             varchar(255)    Corridor name snapshot (e.g. "SGD-PHP-WU-WALLET")
  status                   varchar(50)     Current status — see TransactionStatus reference
  remittance_amount        numeric(20,9)   Sender amount in sender currency (SGD)
  recipient_amount         numeric(20,9)   Destination currency amount
  retail_fee               numeric(20,9)   Fee charged to sender (SGD)
  retail_exchange_rate     numeric(24,12)  Rate shown to customer
  hub_exchange_rate        numeric(24,12)  Rate received from hub
  markup_rate              numeric(6,4)    Markup percentage applied
  markup_fee               numeric(20,9)   Markup fee amount
  error_code               varchar         Application error code when status is a failure
  error_message            text            Human-readable error description
  hub_error_code           varchar         Hub-specific error code (from partner)
  hub_error_message        text            Hub-specific error description
  fraud_status             varchar(30)     Fraud check result (e.g. FRAUD_PASSED, FRAUD_REJECTED)
  payment_mode             varchar(40)     Payment method (e.g. CARD, EWALLET, CASH)
  sender_currency          varchar(32)     Sender currency code (e.g. SGD)
  sender_country           varchar(60)     Sender country name
  recipient_currency       varchar(8)      Destination currency code (e.g. PHP, MYR)
  recipient_country        varchar(60)     Destination country name
  created_date             timestamp       Creation time in SGT (stored without timezone)
  updated_date             timestamp       Last update time in SGT

  PII columns (NEVER include in queries or results):
    sender_msisdn, sender_fullname, sender_dob, sender_email,
    recipient_msisdn, recipient_fullname, recipient_dob

---

TABLE: service_management.remit_service  [ML DB]
  Corridor configuration — one row per sending/receiving country + operator + hub combination.

  remit_service_id         int             PRIMARY KEY  (= remittance.transaction.service_id)
  system_name              varchar(255)    Corridor code (e.g. "SGD-PHP-WU-WALLET")
  service_name_display     varchar(255)    Human-readable corridor name
  local_currency           varchar(10)     Sending currency (e.g. SGD)
  local_country_name       varchar(100)    Sending country name
  foreign_currency         varchar(10)     Receiving currency (e.g. PHP)
  foreign_country_name     varchar(100)    Receiving country name
  external_partner_id      int             FK → external_partner.external_partner_id
  status                   varchar(10)     ACTIVATE or INACTIVE
  service_type             int             1=wallet  2=bank  3=wechat
  min_amount               numeric(20,9)   Minimum transaction amount
  max_amount               numeric(20,9)   Maximum transaction amount
  is_available             boolean         Whether service is currently available

---

TABLE: service_management.external_partner  [ML DB]
  Hub/partner registry.

  external_partner_id      int             PRIMARY KEY  (= remittance.transaction.hub_id)
  external_partner_name    varchar(255)    Hub name: TELEPIN | WU | THUNES | TRANGLO

---

TABLE: ml_schema.country  [ML DB]
  Country reference data.

  id                       int             PRIMARY KEY
  country_name             varchar(50)     Full country name
  country_iso_code         varchar(3)      ISO 3166 alpha-3 code
  currency_iso             varchar(5)      Currency code

---

TABLE: ml_schema.ml_fx_rates  [ML DB]
  FX rate reference data.

  id                       int             PRIMARY KEY
  from_currency            varchar(20)     Source currency
  to_currency              varchar(20)     Destination currency
  fx_rate                  numeric(24,12)  Exchange rate
  service_id               int             FK → service_management.remit_service.remit_service_id

===================================
"""


def get_schema_context() -> str:
    """Return the PII-stripped, whitelisted schema string for LLM prompts."""
    return _SCHEMA_CONTEXT
