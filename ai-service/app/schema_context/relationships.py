"""Cross-schema join hints for Text-to-SQL prompts.

Tells Claude how tables relate across schemas and databases, and how to
handle cross-DB lookups using snapshot columns instead of real SQL joins.
"""

_RELATIONSHIPS = """\
=== CROSS-SCHEMA JOIN HINTS ===

Foreign key relationships (logical — not enforced by DB):
  remittance.transaction.service_id  →  service_management.remit_service.remit_service_id
  remittance.transaction.hub_id      →  service_management.external_partner.external_partner_id

IMPORTANT — Two separate databases, no cross-DB SQL joins:
  remittance.transaction lives in Keycloak DB.
  service_management.* and ml_schema.* live in ML DB.
  SQL cannot JOIN across these two databases directly.

Use snapshot columns instead of cross-DB joins:
  - remittance.transaction.hub_name    already contains the hub name (TELEPIN, WU, THUNES, TRANGLO)
  - remittance.transaction.service_name  already contains the corridor name
  - Use these snapshot columns for hub/corridor breakdowns — no join to external_partner or remit_service needed.

When to query ML DB tables:
  - Corridor configuration (min/max amount, active corridors, service_type)
  - FX rate lookups (ml_schema.ml_fx_rates)
  - Country reference data (ml_schema.country)

Example — corridor volume (single DB, uses snapshot column):
  SELECT service_name, COUNT(*), SUM(remittance_amount)
  FROM remittance.transaction
  WHERE created_date >= CURRENT_DATE - INTERVAL '7 days'
  GROUP BY service_name ORDER BY 3 DESC;

Example — active corridors (ML DB only):
  SELECT system_name, foreign_country_name, min_amount, max_amount
  FROM service_management.remit_service
  WHERE status = 'ACTIVATE' AND is_available = true;

=================================
"""


def get_relationships() -> str:
    """Return cross-schema join hints for injection into LLM prompts."""
    return _RELATIONSHIPS
