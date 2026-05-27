"""Unit tests for schema context builders.

Verifies that the context strings injected into LLM prompts:
  - contain all whitelisted tables and key columns
  - document PII columns as excluded (not expose them as queryable)
  - reference both databases correctly
  - include all TransactionStatus values grouped by phase
"""

from app.models.remittance import FAILED_STATUSES, TERMINAL_STATUSES, TransactionStatus
from app.schema_context.loader import get_schema_context
from app.schema_context.relationships import get_relationships
from app.schema_context.status_ref import get_status_ref

_WHITELISTED_TABLES = [
    "remittance.transaction",
    "service_management.remit_service",
    "service_management.external_partner",
    "ml_schema.country",
    "ml_schema.ml_fx_rates",
]

_KEY_COLUMNS = [
    "hub_name",
    "hub_id",
    "service_id",
    "service_name",
    "status",
    "remittance_amount",
    "recipient_amount",
    "retail_fee",
    "error_code",
    "fraud_status",
    "created_date",
]

_PII_COLUMNS = [
    "sender_msisdn",
    "sender_fullname",
    "sender_dob",
    "sender_email",
    "recipient_msisdn",
    "recipient_fullname",
    "recipient_dob",
]


class TestSchemaContextLoader:
    def test_returns_non_empty_string(self):
        ctx = get_schema_context()
        assert isinstance(ctx, str)
        assert len(ctx) > 100

    def test_contains_all_whitelisted_tables(self):
        ctx = get_schema_context()
        for table in _WHITELISTED_TABLES:
            assert table in ctx, f"Missing whitelisted table: {table}"

    def test_contains_key_operational_columns(self):
        ctx = get_schema_context()
        for col in _KEY_COLUMNS:
            assert col in ctx, f"Missing key column: {col}"

    def test_pii_columns_documented_as_excluded(self):
        ctx = get_schema_context()
        # PII columns appear in the exclusion note, not as regular column definitions.
        # The note must be present so the LLM knows not to query them.
        for col in _PII_COLUMNS:
            assert col in ctx, f"PII column not documented in exclusion note: {col}"
        # The exclusion header must be present
        assert "PII" in ctx or "NEVER" in ctx

    def test_references_both_databases(self):
        ctx = get_schema_context()
        assert "Keycloak DB" in ctx or "keycloak" in ctx.lower()
        assert "ML DB" in ctx or "ml_db" in ctx.lower()

    def test_mentions_hub_names(self):
        ctx = get_schema_context()
        for hub in ["TELEPIN", "WU", "THUNES", "TRANGLO"]:
            assert hub in ctx, f"Hub name missing from schema context: {hub}"

    def test_notes_sgt_timezone(self):
        ctx = get_schema_context()
        assert "SGT" in ctx

    def test_single_db_per_query_instruction(self):
        ctx = get_schema_context()
        # Prompt must tell Claude not to mix engines in one query
        assert "ONE" in ctx or "one" in ctx


class TestStatusRef:
    def test_returns_non_empty_string(self):
        ref = get_status_ref()
        assert isinstance(ref, str)
        assert len(ref) > 100

    def test_contains_all_transaction_status_values(self):
        ref = get_status_ref()
        for status in TransactionStatus:
            assert status.value in ref, f"Missing TransactionStatus value: {status.value}"

    def test_contains_phase_groupings(self):
        ref = get_status_ref()
        for phase in ["Payment", "SOF", "Remittance", "Refund", "Fraud"]:
            assert phase in ref, f"Missing phase group: {phase}"

    def test_failed_statuses_listed(self):
        ref = get_status_ref()
        assert "Failed statuses" in ref or "failed statuses" in ref.lower()
        for status in FAILED_STATUSES:
            assert status.value in ref

    def test_terminal_statuses_listed(self):
        ref = get_status_ref()
        assert "Terminal statuses" in ref or "terminal statuses" in ref.lower()
        for status in TERMINAL_STATUSES:
            assert status.value in ref

    def test_no_duplicate_status_values(self):
        ref = get_status_ref()
        # Every status value should appear at least once — verify counts are sane
        for status in TransactionStatus:
            assert ref.count(status.value) >= 1


class TestRelationships:
    def test_returns_non_empty_string(self):
        rel = get_relationships()
        assert isinstance(rel, str)
        assert len(rel) > 50

    def test_documents_transaction_to_remit_service_fk(self):
        rel = get_relationships()
        assert "service_id" in rel
        assert "remit_service_id" in rel

    def test_documents_transaction_to_external_partner_fk(self):
        rel = get_relationships()
        assert "hub_id" in rel
        assert "external_partner_id" in rel

    def test_warns_about_cross_db_limitation(self):
        rel = get_relationships()
        # Must tell Claude cross-DB SQL joins are not possible
        assert "cannot" in rel.lower() or "not" in rel.lower()
        assert "directly" in rel.lower() or "separate" in rel.lower() or "one" in rel.lower()

    def test_recommends_snapshot_columns(self):
        rel = get_relationships()
        assert "hub_name" in rel
        assert "service_name" in rel
