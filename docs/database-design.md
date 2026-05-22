# Database Design Reference

> Sourced from live DB (localhost:54320) and service entity classes.
> Source repositories: `ml-app-db-liquibase`, `ml-secure-db-liquibase`, `ml-remittance-service`, `ml-customer-service`.

## Connection Info (Non-Prod)

| Property | Value |
|---|---|
| Host | `localhost:54320` |
| User / Password | `admin / admin` |
| App DB | `ml_db` |
| Secure DB | `keycloak` |

---

## Overview: Two Databases, Five Domains

```
ml_db
├── ml_schema          — master/reference data (countries, operators, FX rates, issuers)
└── service_management — remittance service/corridor configuration

keycloak
├── remittance         — transaction lifecycle
├── customer           — beneficiary management
├── payment            — SOF (source of funds) payment records
├── portal             — internal portal users, roles, maker-checker workflows
└── ekyc               — customer KYC/identity data
```

---

## ml_db — ml_schema (Reference / Master Data)

### `ml_schema.country`
Country master data used across all services.

| Column | Type | Notes |
|---|---|---|
| id | int PK | Internal surrogate key |
| country_id | int | Telepin/external country ID |
| country_name | varchar(50) | Display name |
| country_iso_code | varchar(3) | 3-digit ISO code |
| isd_code | varchar(3) | International dialling code |
| currency_iso | varchar(5) | Default currency |

### `ml_schema.mobile_operator`
Remittance destination operators (banks, wallets, mobile money providers).

| Column | Type | Notes |
|---|---|---|
| id | int PK (serial, unique) | Internal ML ID |
| operator_id | int | Telepin operator ID |
| operator_name | varchar(128) | Display name |
| operator_name_hiapp | varchar(148) | HiApp-specific display name |
| iso_code | varchar(3) | Country ISO |
| country_id | int | FK → country |
| country_name | varchar(25) | Denormalized country name |
| operator_code | varchar | Partner-specific code |
| exclusion_id | int | FK → mobile_operator_exclusion |
| default_issuer_id | int | Default bank issuer for this operator |
| service_message / service_message_hiapp | varchar(256) | SMS instructions shown to sender |

### `ml_schema.issuer` / `ml_schema.issuer_ml`
Bank issuers. `issuer` is Telepin-sourced; `issuer_ml` is ML-owned (IDs starting from 10000).

| Column | Type | Notes |
|---|---|---|
| issuer_id | int PK | |
| issuer_name | varchar(100) | Bank name |
| mobile_operator_id | int | Operator this bank belongs to |
| country_id | int | (`issuer_ml` only) |
| active | boolean | (`issuer_ml` only) |

### `ml_schema.ml_fx_rates`
Current FX rates used for displaying quotes to customers.

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| brand_id | varchar(20) | Channel/brand identifier |
| from_currency | varchar(20) | Sending currency (e.g. SGD) |
| to_currency | varchar(20) | Receiving currency (e.g. PHP) |
| fx_rate | numeric(24,12) | Retail rate shown to customer |
| service_id | int | Links to remit_service |
| receiving_country_id | varchar(20) | |
| created_date | timestamp | Rate timestamp |

### `ml_schema.receiving_countries`
Active receiving country + hub/partner combinations.

| Column | Type | Notes |
|---|---|---|
| country_id | int PK, FK → country | |
| partner_id | varchar(25) PK | Hub name (TELEPIN, WU, THUNES, TRANGLO) |
| iso_code | varchar(3) | |
| active_flag | boolean | |

### `ml_schema.ml_r_hub_service_data`
Hub payer configuration (maps payer codes to hubs per country).

| Column | Type | Notes |
|---|---|---|
| payer_type | varchar PK | e.g. BANK, WALLET, CASH_PICKUP |
| payer_value | varchar PK | Partner-specific payer ID |
| country_iso_code | varchar(2) PK | |
| hub_id | int | Links to external_partner |
| payer_name | varchar | Display name |

### Other ml_schema tables
- `purpose_of_remittance` — remittance purpose codes
- `fx_params_config` — FX configuration params per remit_service
- `ml_fx_rates_history` — historical FX rate snapshots
- `ml_enabled_brands` — enabled brand/corridor summary view
- `mobile_operator_exclusion` — operators excluded from specific channels
- `ml_translation_content` — i18n translations
- `occupation`, `source_of_wealth`, `cardtype` — KYC lookup tables
- `province`, `city` — geographic reference (used in beneficiary address)
- `customer_relationship` — sender-beneficiary relationship types

---

## ml_db — service_management (Corridor Configuration)

### `service_management.external_partner`
Hub/partner registry (Telepin, WU, Thunes, Tranglo).

| Column | Type | Notes |
|---|---|---|
| external_partner_id | int PK | |
| external_partner_name | varchar(255) | e.g. "TELEPIN", "THUNES" |
| customer_names_input_required | boolean | Whether sender/bene names must be provided |

### `service_management.remit_service`
The core corridor definition. Each row = one sending country + receiving country + operator + hub combination.

| Column | Type | Notes |
|---|---|---|
| remit_service_id | int PK | |
| system_name | varchar(255) | Internal name |
| service_name_display | varchar(255) | Customer-facing name |
| local_currency / local_country_id / local_country_name | | Sending side |
| foreign_currency / foreign_country_id / foreign_country_name | | Receiving side |
| external_service_id | int | Hub's service ID |
| external_partner_id | int FK → external_partner | Hub/partner |
| reference_hub | int FK → external_partner | For services that reference another hub |
| mobile_operator_id | int | Target operator |
| status | varchar(10) | ACTIVATE / INACTIVE |
| service_type | int | 1=mobile wallet, 2=bank, 3=wechat, etc. |
| markup_fee | numeric(10,4) | Fixed fee in local currency |
| markup_rate_percentage | numeric(6,4) | Rate markup % |
| min_amount / max_amount | numeric(20,9) | Transaction limits |
| payment_method | varchar(16) | SOF payment method |
| beneficiary_validation_required | boolean | Trigger bene account validation before submit |
| beneficiary_auto_inclusion | boolean | Auto-add bene on first successful transaction |
| is_available | boolean | Service currently available |
| time_check_required | boolean | Active time window check |
| active_time_start / active_time_end | time | Allowed operating hours |

### `service_management.remit_service_tier_fee`
Tiered fee structure per service (overrides flat fee in remit_service for amount ranges).

| Column | Notes |
|---|---|
| remit_service_id + min_amount | Composite PK |
| max_amount | Upper bound of tier |
| markup_fee | Fixed fee for tier |
| markup_rate_percentage | Rate markup for tier |
| retail_fee | Final retail fee |

### `service_management.remit_corridor_reference`
Maps receiving corridor details to a service (country + payer + partner).

| Column | Notes |
|---|---|
| country_id | Destination country |
| referer_id | Corridor identifier used by Thunes/Tranglo |
| payer_id | Hub's payer ID |
| payer_type | BANK / WALLET / CASH_PICKUP |
| service_id | FK → remit_service |
| external_partner_id | Hub |
| bene_validation_required | Validate beneficiary before submit |
| bene_transaction_validation_required | Validate on each transaction |

### `service_management.remit_service_beneficiary_field_mapping`
Defines which beneficiary fields are required/mapped per service (used for validation rules and hub field name translation).

### `service_management.remit_service_channel_mapping`
Maps services to distribution channels/brands (HiApp, etc.) with active status.

### `service_management.ml_fx_transaction_fee`
Per-hub transaction fee snapshot keyed by date + currency pair + payer type.

### Other service_management tables
- `partner` / `partner_blacklist_service` / `partner_globalfx_service` — partner access control
- `mobile_operator_service_mapping` — which ML operators can use which service
- `beneficiary_service_dependency` — service cross-dependencies (e.g. WechatPay depends on bank service)
- `ml_r_remit_service_brand_mapping` — virtual brand ID per service

---

## keycloak — remittance (Transaction Lifecycle)

### `remittance.transaction`
Core transaction table. One row per remittance attempt. Status drives the full lifecycle.

| Column | Type | Notes |
|---|---|---|
| internal_transaction_id | bigint PK | ML internal ID (sequence) |
| hub_id | bigint | Which hub processed this (FK concept to external_partner) |
| hub_name | varchar(255) | Hub name snapshot (TELEPIN/WU/THUNES/TRANGLO) |
| payment_reference_id | varchar(16) | ML payment reference shown to customer |
| hub_transaction_id | varchar(16) | Hub's short transaction ID |
| hub_transaction_id_check | varchar(48) | Hub TX ID from check step |
| hub_transaction_id_submit | varchar(48) | Hub TX ID from submit step |
| partner_transaction_id_check | varchar(48) | Partner TX ID from check step |
| partner_transaction_id_submit | varchar(48) | Partner TX ID from submit step |
| hub_transaction_reference | text | Wechat share link / external reference |
| refund_reference_id | varchar(16) | Reference for refund transaction |
| service_id | bigint | FK → remit_service |
| service_name | varchar(255) | Snapshot of service name |
| service_type | smallint | Snapshot of service type |
| partner_id | varchar(10) | Distribution partner/channel |
| status | varchar(50) | See TransactionStatus enum below |
| sender_account_id | varchar(16) | Sender's Telepin account ID |
| sender_msisdn | varchar(40) | Sender phone (PII — masked in logs) |
| sender_fullname | varchar(356) | (PII — masked) |
| sender_dob | varchar(32) | (PII — masked) |
| sender_currency | varchar(32) | |
| sender_country | varchar(60) | |
| sender_country_of_residence | varchar(50) | |
| sender_nationality | varchar(50) | |
| sender_email | varchar(50) | |
| recipient_id | varchar(16) | Beneficiary Telepin ID |
| recipient_msisdn | varchar(40) | (PII — masked) |
| recipient_fullname | varchar(356) | (PII — masked) |
| recipient_currency | varchar(8) | |
| recipient_country | varchar(60) | |
| recipient_nationality | varchar(60) | |
| recipient_dob | varchar(32) | (PII — masked) |
| recipient_pickup_code | varchar(256) | Cash pickup code (encrypted) |
| remittance_amount | numeric(20,9) | Amount in sender currency |
| recipient_amount | numeric(20,9) | Amount in recipient currency |
| customer_key_in_amount | numeric(20,9) | Amount customer typed (before conversion) |
| currency_flag | smallint | 0 = source mode, 1 = destination mode |
| hub_exchange_rate | numeric(24,12) | Hub's rate |
| retail_exchange_rate | numeric(24,12) | Customer-facing rate |
| markup_rate | numeric(6,4) | Applied markup % |
| markup_fee | numeric(20,9) | Fixed markup fee charged |
| hub_gross_fee | numeric(20,9) | Hub's gross fee |
| retail_fee | numeric(20,9) | Final fee charged to customer |
| retail_tax_amount | numeric(20,9) | Tax component |
| error_code / error_message | | ML-level error |
| hub_status_id / hub_status | | Hub's status code and description |
| hub_sub_status_id / hub_sub_status | | Hub's sub-status |
| hub_error_code / hub_error_message | | Hub-level error |
| fraud_status | varchar(30) | Result of Forter fraud check |
| payment_mode | varchar(40) | SOF type: NETS_CLICK, PAYNOW, etc. |
| card_id | varchar(40) | Tokenized card ID used for SOF |
| device_id | varchar(64) | Mobile device ID |
| external_service_id | int | External payment service reference |
| reference_hub_name | varchar(32) | Fallback hub name (Tranglo check) |
| proxy_refund_status | varchar(20) | INITIATED / COMPLETED / FAILED |
| remit_purpose_id | varchar(20) | Purpose of remittance code |
| source_of_fund_ref_id | varchar(21) | PayNow/SOF reference |
| transaction_digest | varchar(100) | Integrity hash (masked in logs) |
| is_notify_sms_sender | boolean | Send SMS notification to sender |
| salt | varchar(50) | Encryption salt |
| created_date / updated_date / version | | Optimistic locking + audit |

**Transaction Status Lifecycle (TransactionStatus enum):**
```
Payment phase:    PAYMENT_VALIDATED → PAYMENT_ACCEPTED → PAYMENT_PENDING
                  → PAYMENT_RESERVED (funds held) or PAYMENT_*_FAILED

SOF phase:        SOF_PAY_PENDING → SOF_PAY_COMPLETED or SOF_PAY_FAILED

Remittance phase: TRANSACTION_SUBMITTED → TRANSACTION_IN_PROGRESS
                  → TRANSACTION_SUCCESS / TRANSACTION_COMPLETED / TRANSACTION_CONFIRMED
                  → TRANSACTION_FAILED / TRANSACTION_DECLINED / TRANSACTION_ON_HOLD

Refund:           *_REFUND_REQUIRED → REFUNDED / REFUND_FAILED
Special:          FRAUD_CHECK_FAILED / FRAUD_CHECK_DECLINED / FRAUD_CHECK_TIMEOUT
```

### `remittance.transaction_aud`
Hibernate Envers audit table — full history of every status change on a transaction. Same columns plus `rev`, `revtype`, `audit_date`, `salt`.

### `remittance.paynow_credit_notification` + `remittance.paynow_transactions`
PayNow inbound credit flow. Notification → creates a paynow_transaction with QR data, then links to a remittance transaction via `source_of_fund_ref_id`.

### `remittance.service_config`
Key-value config per hub service (e.g. SMS message templates, Tranglo agent extension text).

---

## keycloak — customer (Beneficiary Management)

### `customer.beneficiary`
Saved recipient profiles per sender.

| Column | Notes |
|---|---|
| id | ML internal PK |
| bene_id | Telepin beneficiary ID |
| sender_account_id | FK concept to sender's Telepin account |
| bene_first_name / bene_last_name / bene_full_name | Recipient name (PII) |
| sender_first_name / sender_last_name | Sender name snapshot (PII) |
| benemsisdn | Recipient phone/wallet number (PII) |
| receiving_country | FK → country |
| mobile_operator | Telepin operator_id |
| ml_operator_id | FK → mobile_operator (ML internal ID) |
| issuer_id / issuer_alternative_id | Bank issuer |
| bene_bank_acct_no | Bank account number (PII) |
| wallet_account_number | E-wallet account (PII) |
| branch_code | Bank branch |
| bank_acc_type_flag | true = savings, false = current |
| remit_purpose / remit_purpose_note | Purpose of transfer |
| cust_relationship | Relationship to sender |
| nationality / dob / birth_place | Identity fields (PII) |
| gender / job / other_job | Profile fields |
| bene_address / province_id / city_id / postal_code | Address |
| status | ACTIVE / INACTIVE / DELETED |
| status_remark / warning_message | Status context |
| sys_flag | System origin flag |
| old_bene_id | Pre-migration Telepin bene ID |
| salt | Encryption salt |

### `customer.beneficiary_service`
Links a beneficiary to a specific remit service (validated status per corridor).

| Column | Notes |
|---|---|
| ml_bene_id | FK → beneficiary |
| service_id | FK → remit_service |
| sender_account_id | |
| ml_operator_id | |
| validation_status | PENDING / VALID / INVALID |
| validation_state_partner_response | Raw partner validation response |
| referer_id | Corridor referer identifier |

### `customer.remit_corridor_reference_field_validation`
Regex validation rules for beneficiary fields per corridor (e.g. account number format for Thai banks).

### `customer.customer_grey_list`
Flagged sender accounts (AML/compliance hold list).

---

## keycloak — payment (Source of Funds)

### `payment.m_ml_tokenized_card`
NETS tokenized debit cards registered for SOF payments.

| Column | Notes |
|---|---|
| card_id | UUID PK |
| telepin_account_id | Owner's Telepin account |
| device_id | Mobile device that registered the card |
| sof_type | e.g. NETS_CLICK |
| card_token / token_expiry | Card token (48 chars) |
| last_4_digits_fpan / bank_fiid / issuer_short_name | Card identification |
| token_status | smallint — registered/unregistered |
| card_status | REGISTERED / UNREGISTERED |

### `payment.ml_m_sof_payment`
SOF payment attempt per transaction. One-to-one with remittance.transaction via `internal_transaction_id`.

| Column | Notes |
|---|---|
| payment_id | PK (used as NETS REF) |
| internal_transaction_id | FK → remittance.transaction (unique) |
| card_id | Tokenized card used |
| payment_amount | Amount charged |
| status | Payment lifecycle status |
| refund_initiated_by | "system" or portal user login |

### `payment.ml_r_sof_payment_message`
ISO 8583-style payment messages for each NETS interaction (authorization, refund, etc.).

### `payment.ml_a_sof_payment`
Audit table for ml_m_sof_payment (every status change persisted).

---

## keycloak — portal (Internal Operations Portal)

### `portal.user`
Internal portal operator accounts.

| Column | Notes |
|---|---|
| login_id | Unique — matches Keycloak username |
| email_id | |
| status | 0=active, 1=inactive |

### `portal.roles` + `portal.privileges`
RBAC model. Roles have a `function` field (OPERATION/ADMIN/etc.). Privileges have `is_secure` and `is_common` flags.

### `portal.role_menu_mapping` + `portal.role_privileges`
Many-to-many: roles → menus and roles → privileges.

### `portal.workflow_requests`
Legacy maker-checker table. Stores `request_payload` and `result` as JSON blobs, linked to creator and approver users.

| Column | Notes |
|---|---|
| function | Domain function name (e.g. UPDATE_REMIT_SERVICE) |
| operation | CREATE / UPDATE / DELETE |
| status | PENDING / APPROVED / REJECTED / CANCELLED |
| request_payload | JSON of the change request |
| result | JSON of the applied result |

### `portal.action_request`
Newer maker-checker table (replaces workflow_requests). Uses `request_flow_id` for approval routing.

### `portal.service_config`
Portal-level service configuration with validation regex (e.g. allowed WU payout countries, Tranglo limits).

### `portal.ml_user_audit`
Audit trail of all portal user actions.

---

## keycloak — ekyc (Customer Identity)

### `ekyc.ekyc_reference` + `ekyc.ekyc_data`
Customer KYC verification records. Linked by `(correlation_id, verification_id)`. Stores OCR output from Jumio alongside verified MyInfo/NRIC data, with photos as `bytea`.

Fields include: id_type, id_number, id_expiry_date, fullname, dob, nationality, address fields, source_of_fund, selfie/front/back ID photos.

---

## Key Relationships (Cross-Schema)

```
remittance.transaction.service_id        → ml_db.service_management.remit_service.remit_service_id
remittance.transaction.hub_id            → ml_db.service_management.external_partner.external_partner_id (conceptual)
customer.beneficiary.receiving_country   → ml_db.ml_schema.country.id
customer.beneficiary.mobile_operator     → ml_db.ml_schema.mobile_operator.operator_id
customer.beneficiary_service.service_id  → ml_db.service_management.remit_service.remit_service_id
payment.ml_m_sof_payment.internal_transaction_id → remittance.transaction.internal_transaction_id
```

> Note: Cross-database FKs are not enforced at DB level — they are enforced by application logic.

---

## Notes for AI Operations Portal

- **Primary operational data** for dashboards: `remittance.transaction` — query by `status`, `created_date`, `service_id`, `hub_id`
- **Failure analysis**: join `error_code`, `hub_error_code`, `fraud_status` with `hub_status`/`hub_sub_status` for root cause
- **Transaction amounts**: `remittance_amount` = sender amount, `recipient_amount` = destination amount, `retail_fee` = charged fee
- **PII columns** are masked in application logs (senderMsisdn, senderFullname, recipientMsisdn, etc.) — handle carefully in AI prompts
- **Audit tables** (`_aud` suffix) use Hibernate Envers pattern: same columns + `rev` (revision number) + `revtype` (0=insert, 1=update, 2=delete)
- **Backup tables** (`_bk_*` suffix) are point-in-time snapshots used for manual data recovery — do not query for analytics
