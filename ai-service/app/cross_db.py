"""Cross-DB join helpers.

ml_db and keycloak are separate databases — joins happen here in Python,
using the in-memory cache for ml_db reference data.
"""

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime

from app.cache import ReferenceCache
from app.models.remittance import Transaction


@dataclass
class EnrichedTransaction:
    """Transaction row with ml_db reference data resolved."""

    # Core identity
    internal_transaction_id: int
    payment_reference_id: str | None
    status: str | None

    # Amounts
    remittance_amount: Decimal | None
    recipient_amount: Decimal | None
    retail_fee: Decimal | None
    sender_currency: str | None
    recipient_currency: str | None

    # Hub / service (resolved from cache)
    hub_id: int | None
    hub_name: str | None           # snapshot from transaction row
    hub_name_resolved: str | None  # resolved from external_partner via cache
    service_id: int | None
    service_name: str | None       # snapshot
    service_name_resolved: str | None  # resolved from remit_service via cache
    foreign_country_name: str | None   # destination country from service config

    # Errors
    error_code: str | None
    hub_error_code: str | None
    fraud_status: str | None

    # Dates
    created_date: datetime | None
    updated_date: datetime | None


def enrich_transaction(tx: Transaction, cache: ReferenceCache) -> EnrichedTransaction:
    """Resolve ml_db reference IDs for a single transaction row."""
    hub_id = int(tx.hub_id) if tx.hub_id is not None else None
    service_id = int(tx.service_id) if tx.service_id is not None else None

    svc = cache.services_by_id.get(service_id) if service_id else None

    return EnrichedTransaction(
        internal_transaction_id=tx.internal_transaction_id,
        payment_reference_id=tx.payment_reference_id,
        status=tx.status,
        remittance_amount=tx.remittance_amount,
        recipient_amount=tx.recipient_amount,
        retail_fee=tx.retail_fee,
        sender_currency=tx.sender_currency,
        recipient_currency=tx.recipient_currency,
        hub_id=hub_id,
        hub_name=tx.hub_name,
        hub_name_resolved=cache.partner_name(hub_id),
        service_id=service_id,
        service_name=tx.service_name,
        service_name_resolved=cache.service_name(service_id),
        foreign_country_name=svc.foreign_country_name if svc else None,
        error_code=tx.error_code,
        hub_error_code=tx.hub_error_code,
        fraud_status=tx.fraud_status,
        created_date=tx.created_date,
        updated_date=tx.updated_date,
    )


def enrich_transactions(
    transactions: list[Transaction], cache: ReferenceCache
) -> list[EnrichedTransaction]:
    return [enrich_transaction(tx, cache) for tx in transactions]
