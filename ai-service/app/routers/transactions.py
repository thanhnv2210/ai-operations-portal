"""Transaction Explorer API — search, detail, audit history."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Annotated

_SGT = timezone(timedelta(hours=8))

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import ReferenceCache, get_cache
from app.database import get_keycloak_db
from app.models.remittance import Transaction, TransactionAud

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/transactions", tags=["transactions"])

DbDep = Annotated[AsyncSession, Depends(get_keycloak_db)]
CacheDep = Annotated[ReferenceCache, Depends(get_cache)]


def _naive(dt: datetime) -> datetime:
    """Convert to SGT-naive — DB stores TIMESTAMP WITHOUT TIME ZONE in SGT."""
    if dt.tzinfo:
        dt = dt.astimezone(_SGT)
    return dt.replace(tzinfo=None)


_MAX_RANGE_DAYS = 90


def _default_from() -> datetime:
    return (datetime.now(_SGT) - timedelta(days=30)).replace(tzinfo=None)


def _default_to() -> datetime:
    return datetime.now(_SGT).replace(tzinfo=None)


def _clamp_range(from_date: datetime, to_date: datetime) -> tuple[datetime, datetime]:
    """Cap the query window to MAX_RANGE_DAYS to protect the production DB."""
    if (to_date - from_date).days > _MAX_RANGE_DAYS:
        from_date = to_date - timedelta(days=_MAX_RANGE_DAYS)
    return from_date, to_date


# --- Response models ---

class TransactionRow(BaseModel):
    internal_transaction_id: int
    payment_reference_id: str | None
    status: str | None
    hub_name: str | None
    service_name: str | None
    remittance_amount: float | None
    recipient_amount: float | None
    sender_currency: str | None
    recipient_currency: str | None
    recipient_country: str | None
    error_code: str | None
    hub_error_code: str | None
    fraud_status: str | None
    payment_mode: str | None
    created_date: datetime | None
    updated_date: datetime | None


class TransactionPage(BaseModel):
    items: list[TransactionRow]
    total: int
    page: int
    page_size: int
    pages: int


class AuditEntry(BaseModel):
    id: int
    audit_date: datetime | None
    status: str | None
    hub_status: str | None
    hub_sub_status: str | None
    error_code: str | None
    hub_error_code: str | None
    fraud_status: str | None
    proxy_refund_status: str | None


class TransactionDetail(BaseModel):
    # Identity
    internal_transaction_id: int
    payment_reference_id: str | None
    hub_transaction_id: str | None
    hub_transaction_id_submit: str | None
    partner_transaction_id_submit: str | None
    refund_reference_id: str | None

    # Status
    status: str | None
    fraud_status: str | None
    proxy_refund_status: str | None

    # Hub / service
    hub_id: int | None
    hub_name: str | None
    hub_name_resolved: str | None
    service_id: int | None
    service_name: str | None
    service_name_resolved: str | None
    service_type: int | None
    partner_id: str | None

    # Amounts
    remittance_amount: float | None
    recipient_amount: float | None
    retail_fee: float | None
    retail_tax_amount: float | None
    sender_currency: str | None
    recipient_currency: str | None
    currency_flag: int | None

    # FX
    hub_exchange_rate: float | None
    retail_exchange_rate: float | None
    markup_rate: float | None
    markup_fee: float | None
    hub_gross_fee: float | None

    # Sender (non-PII only)
    sender_account_id: str | None
    sender_country: str | None
    sender_nationality: str | None

    # Recipient (non-PII only)
    recipient_id: str | None
    recipient_country: str | None
    recipient_nationality: str | None

    # Errors
    error_code: str | None
    error_message: str | None
    hub_status: str | None
    hub_status_id: str | None
    hub_sub_status: str | None
    hub_error_code: str | None
    hub_error_message: str | None

    # Payment
    payment_mode: str | None
    remit_purpose_id: str | None
    external_service_id: int | None

    # Audit
    created_date: datetime | None
    updated_date: datetime | None
    version: int | None


# --- Helpers ---

def _tx_to_row(tx: Transaction, cache: ReferenceCache) -> TransactionRow:
    hub_id = int(tx.hub_id) if tx.hub_id else None
    svc_id = int(tx.service_id) if tx.service_id else None
    return TransactionRow(
        internal_transaction_id=tx.internal_transaction_id,
        payment_reference_id=tx.payment_reference_id,
        status=tx.status,
        hub_name=cache.partner_name(hub_id) or tx.hub_name,
        service_name=cache.service_name(svc_id) or tx.service_name,
        remittance_amount=float(tx.remittance_amount) if tx.remittance_amount else None,
        recipient_amount=float(tx.recipient_amount) if tx.recipient_amount else None,
        sender_currency=tx.sender_currency,
        recipient_currency=tx.recipient_currency,
        recipient_country=tx.recipient_country,
        error_code=tx.error_code,
        hub_error_code=tx.hub_error_code,
        fraud_status=tx.fraud_status,
        payment_mode=tx.payment_mode,
        created_date=tx.created_date,
        updated_date=tx.updated_date,
    )


def _tx_to_detail(tx: Transaction, cache: ReferenceCache) -> TransactionDetail:
    hub_id = int(tx.hub_id) if tx.hub_id else None
    svc_id = int(tx.service_id) if tx.service_id else None
    return TransactionDetail(
        internal_transaction_id=tx.internal_transaction_id,
        payment_reference_id=tx.payment_reference_id,
        hub_transaction_id=tx.hub_transaction_id,
        hub_transaction_id_submit=tx.hub_transaction_id_submit,
        partner_transaction_id_submit=tx.partner_transaction_id_submit,
        refund_reference_id=tx.refund_reference_id,
        status=tx.status,
        fraud_status=tx.fraud_status,
        proxy_refund_status=tx.proxy_refund_status,
        hub_id=hub_id,
        hub_name=tx.hub_name,
        hub_name_resolved=cache.partner_name(hub_id),
        service_id=svc_id,
        service_name=tx.service_name,
        service_name_resolved=cache.service_name(svc_id),
        service_type=tx.service_type,
        partner_id=tx.partner_id,
        remittance_amount=float(tx.remittance_amount) if tx.remittance_amount else None,
        recipient_amount=float(tx.recipient_amount) if tx.recipient_amount else None,
        retail_fee=float(tx.retail_fee) if tx.retail_fee else None,
        retail_tax_amount=float(tx.retail_tax_amount) if tx.retail_tax_amount else None,
        sender_currency=tx.sender_currency,
        recipient_currency=tx.recipient_currency,
        currency_flag=tx.currency_flag,
        hub_exchange_rate=float(tx.hub_exchange_rate) if tx.hub_exchange_rate else None,
        retail_exchange_rate=float(tx.retail_exchange_rate) if tx.retail_exchange_rate else None,
        markup_rate=float(tx.markup_rate) if tx.markup_rate else None,
        markup_fee=float(tx.markup_fee) if tx.markup_fee else None,
        hub_gross_fee=float(tx.hub_gross_fee) if tx.hub_gross_fee else None,
        sender_account_id=tx.sender_account_id,
        sender_country=tx.sender_country,
        sender_nationality=tx.sender_nationality,
        recipient_id=tx.recipient_id,
        recipient_country=tx.recipient_country,
        recipient_nationality=tx.recipient_nationality,
        error_code=tx.error_code,
        error_message=tx.error_message,
        hub_status=tx.hub_status,
        hub_status_id=tx.hub_status_id,
        hub_sub_status=tx.hub_sub_status,
        hub_error_code=tx.hub_error_code,
        hub_error_message=tx.hub_error_message,
        payment_mode=tx.payment_mode,
        remit_purpose_id=tx.remit_purpose_id,
        external_service_id=tx.external_service_id,
        created_date=tx.created_date,
        updated_date=tx.updated_date,
        version=tx.version,
    )


# --- Endpoints ---

@router.get("", response_model=TransactionPage)
async def search_transactions(
    db: DbDep,
    cache: CacheDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    status: list[str] = Query(default=[]),
    hub_id: int | None = Query(default=None),
    service_id: int | None = Query(default=None),
    error_code: str | None = Query(default=None),
    payment_reference_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    from_date, to_date = _clamp_range(from_date, to_date)
    base = (
        select(Transaction)
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
        )
    )
    if status:
        base = base.where(Transaction.status.in_(status))
    if hub_id is not None:
        base = base.where(Transaction.hub_id == hub_id)
    if service_id is not None:
        base = base.where(Transaction.service_id == service_id)
    if error_code:
        base = base.where(
            or_(
                Transaction.error_code.ilike(f"%{error_code}%"),
                Transaction.hub_error_code.ilike(f"%{error_code}%"),
            )
        )
    if payment_reference_id:
        base = base.where(
            Transaction.payment_reference_id.ilike(f"%{payment_reference_id}%")
        )

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()

    rows = (
        await db.execute(
            base.order_by(desc(Transaction.created_date))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return TransactionPage(
        items=[_tx_to_row(tx, cache) for tx in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, -(-total // page_size)),  # ceil division
    )


@router.get("/{transaction_id}", response_model=TransactionDetail)
async def get_transaction(
    transaction_id: int,
    db: DbDep,
    cache: CacheDep,
):
    tx = (
        await db.execute(
            select(Transaction).where(Transaction.internal_transaction_id == transaction_id)
        )
    ).scalar_one_or_none()

    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    return _tx_to_detail(tx, cache)


@router.get("/{transaction_id}/audit", response_model=list[AuditEntry])
async def get_transaction_audit(
    transaction_id: int,
    db: DbDep,
):
    rows = (
        await db.execute(
            select(TransactionAud)
            .where(TransactionAud.internal_transaction_id == transaction_id)
            .order_by(asc(TransactionAud.id))
        )
    ).scalars().all()

    return [
        AuditEntry(
            id=r.id,
            audit_date=r.audit_date,
            status=r.status,
            hub_status=r.hub_status,
            hub_sub_status=r.hub_sub_status,
            error_code=r.error_code,
            hub_error_code=r.hub_error_code,
            fraud_status=r.fraud_status,
            proxy_refund_status=r.proxy_refund_status,
        )
        for r in rows
    ]
