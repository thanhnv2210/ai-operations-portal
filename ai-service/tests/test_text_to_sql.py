"""Unit tests for app.services.text_to_sql pure-logic functions.

No DB or LLM calls — all functions under test are synchronous and pure.
"""

import pytest

from app.services.text_to_sql import _detect_engine, _validate


class TestValidate:
    """_validate(sql) returns None for safe SQL, an error string otherwise."""

    def test_accepts_select(self):
        assert _validate("SELECT 1") is None

    def test_accepts_select_with_schema(self):
        sql = (
            "SELECT COUNT(*) FROM remittance.transaction "
            "WHERE status LIKE '%FAILED%' AND created_date::date = CURRENT_DATE"
        )
        assert _validate(sql) is None

    def test_accepts_select_with_leading_whitespace(self):
        assert _validate("   SELECT hub_name FROM remittance.transaction") is None

    def test_accepts_multiline_select(self):
        sql = "SELECT\n  hub_name,\n  COUNT(*)\nFROM remittance.transaction\nGROUP BY hub_name"
        assert _validate(sql) is None

    def test_rejects_insert(self):
        assert _validate("INSERT INTO foo VALUES (1)") is not None

    def test_rejects_update(self):
        assert _validate("UPDATE foo SET x = 1 WHERE id = 1") is not None

    def test_rejects_delete(self):
        assert _validate("DELETE FROM foo WHERE id = 1") is not None

    def test_rejects_drop(self):
        assert _validate("DROP TABLE remittance.transaction") is not None

    def test_rejects_create(self):
        assert _validate("CREATE TABLE shadow_copy AS SELECT * FROM remittance.transaction") is not None

    def test_rejects_truncate(self):
        assert _validate("TRUNCATE TABLE remittance.transaction") is not None

    def test_rejects_alter(self):
        assert _validate("ALTER TABLE remittance.transaction ADD COLUMN x int") is not None

    def test_rejects_grant(self):
        assert _validate("GRANT SELECT ON remittance.transaction TO hacker") is not None

    def test_rejects_case_insensitive(self):
        assert _validate("insert into foo values (1)") is not None
        assert _validate("drop table foo") is not None
        assert _validate("DELETE FROM foo") is not None

    def test_rejects_explain_as_first_word(self):
        # EXPLAIN is not SELECT — must be rejected even though it's safe
        assert _validate("EXPLAIN SELECT 1") is not None

    def test_returns_string_on_rejection(self):
        result = _validate("DROP TABLE foo")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_none_on_acceptance(self):
        assert _validate("SELECT 1") is None


class TestDetectEngine:
    """_detect_engine(sql) routes to 'keycloak', 'ml_db', or 'cross'."""

    # --- Keycloak schemas ---

    def test_remittance_schema_routes_keycloak(self):
        assert _detect_engine("SELECT * FROM remittance.transaction") == "keycloak"

    def test_customer_schema_routes_keycloak(self):
        assert _detect_engine("SELECT * FROM customer.beneficiary") == "keycloak"

    def test_payment_schema_routes_keycloak(self):
        assert _detect_engine("SELECT * FROM payment.ml_m_sof_payment") == "keycloak"

    def test_keycloak_detection_is_case_insensitive(self):
        assert _detect_engine("SELECT * FROM REMITTANCE.transaction") == "keycloak"

    # --- ML DB schemas ---

    def test_ml_schema_routes_mldb(self):
        assert _detect_engine("SELECT * FROM ml_schema.country") == "ml_db"

    def test_service_management_routes_mldb(self):
        assert _detect_engine("SELECT * FROM service_management.remit_service") == "ml_db"

    def test_mldb_detection_is_case_insensitive(self):
        assert _detect_engine("SELECT * FROM ML_SCHEMA.country") == "ml_db"

    # --- Cross-DB ---

    def test_remittance_plus_service_management_is_cross(self):
        sql = (
            "SELECT t.hub_name, s.foreign_country_name "
            "FROM remittance.transaction t "
            "JOIN service_management.remit_service s ON t.service_id = s.remit_service_id"
        )
        assert _detect_engine(sql) == "cross"

    def test_remittance_plus_ml_schema_is_cross(self):
        sql = "SELECT * FROM remittance.transaction, ml_schema.country"
        assert _detect_engine(sql) == "cross"

    # --- Default ---

    def test_no_schema_prefix_defaults_to_keycloak(self):
        # Unrecognised or bare table name → default to keycloak (most queries hit transaction)
        assert _detect_engine("SELECT 1") == "keycloak"
        assert _detect_engine("SELECT * FROM transaction") == "keycloak"
