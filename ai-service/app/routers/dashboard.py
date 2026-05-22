"""Dashboard API — operational metrics for remittance.transaction."""

import logging
import statistics
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import ReferenceCache, get_cache
from app.database import get_keycloak_db
from app.models.remittance import FAILED_STATUSES, TERMINAL_STATUSES, Transaction

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


def _naive(dt: datetime) -> datetime:
    """Strip timezone — DB stores TIMESTAMP WITHOUT TIME ZONE."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt

# --- Shared dependency types ---

DbDep = Annotated[AsyncSession, Depends(get_keycloak_db)]
CacheDep = Annotated[ReferenceCache, Depends(get_cache)]


_MAX_RANGE_DAYS = 90


def _default_from() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=7)


def _default_to() -> datetime:
    return datetime.now(timezone.utc)


def _clamp_range(from_date: datetime, to_date: datetime) -> tuple[datetime, datetime]:
    """Cap the query window to MAX_RANGE_DAYS to protect the production DB."""
    if (to_date - from_date).days > _MAX_RANGE_DAYS:
        from_date = to_date - timedelta(days=_MAX_RANGE_DAYS)
    return from_date, to_date


# --- Response models ---

class OverviewResponse(BaseModel):
    total_transactions: int
    failed_transactions: int
    failure_rate: float          # 0.0–1.0
    total_volume: float          # sum of remittance_amount in sender currency
    avg_volume_per_tx: float
    from_date: datetime
    to_date: datetime


class VolumeTrendPoint(BaseModel):
    bucket: str                  # ISO datetime string for the bucket start
    total: int
    failed: int


class VolumeTrendResponse(BaseModel):
    interval: str                # "hour" | "day"
    points: list[VolumeTrendPoint]


class StatusCount(BaseModel):
    status: str
    count: int


class StatusDistributionResponse(BaseModel):
    statuses: list[StatusCount]


class ProcessingTimeResponse(BaseModel):
    p50_seconds: float | None
    p95_seconds: float | None
    sample_size: int


class HubMetric(BaseModel):
    hub_id: int | None
    hub_name: str
    total: int
    failed: int
    failure_rate: float
    total_volume: float


class HubBreakdownResponse(BaseModel):
    hubs: list[HubMetric]


# --- Helpers ---

def _failed_case():
    """SQLAlchemy CASE expression: 1 when status is a failure, else 0."""
    failed_values = [s.value for s in FAILED_STATUSES]
    return case((Transaction.status.in_(failed_values), 1), else_=0)


# --- Endpoints ---

@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    db: DbDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    hub_id: int | None = Query(default=None),
    service_id: int | None = Query(default=None),
):
    from_date, to_date = _clamp_range(from_date, to_date)
    q = (
        select(
            func.count().label("total"),
            func.sum(_failed_case()).label("failed"),
            func.coalesce(func.sum(Transaction.remittance_amount), 0).label("volume"),
        )
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
        )
    )
    if hub_id is not None:
        q = q.where(Transaction.hub_id == hub_id)
    if service_id is not None:
        q = q.where(Transaction.service_id == service_id)

    row = (await db.execute(q)).one()
    total = row.total or 0
    failed = int(row.failed or 0)
    volume = float(row.volume or 0)

    return OverviewResponse(
        total_transactions=total,
        failed_transactions=failed,
        failure_rate=failed / total if total else 0.0,
        total_volume=volume,
        avg_volume_per_tx=volume / total if total else 0.0,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/volume-trend", response_model=VolumeTrendResponse)
async def get_volume_trend(
    db: DbDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    hub_id: int | None = Query(default=None),
    service_id: int | None = Query(default=None),
    interval: str = Query(default="day", pattern="^(hour|day)$"),
):
    from_date, to_date = _clamp_range(from_date, to_date)
    trunc_fn = func.date_trunc(interval, Transaction.created_date)

    q = (
        select(
            trunc_fn.label("bucket"),
            func.count().label("total"),
            func.sum(_failed_case()).label("failed"),
        )
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
        )
        .group_by(trunc_fn)
        .order_by(trunc_fn)
    )
    if hub_id is not None:
        q = q.where(Transaction.hub_id == hub_id)
    if service_id is not None:
        q = q.where(Transaction.service_id == service_id)

    rows = (await db.execute(q)).all()
    return VolumeTrendResponse(
        interval=interval,
        points=[
            VolumeTrendPoint(
                bucket=row.bucket.isoformat() if row.bucket else "",
                total=row.total or 0,
                failed=int(row.failed or 0),
            )
            for row in rows
        ],
    )


@router.get("/status-distribution", response_model=StatusDistributionResponse)
async def get_status_distribution(
    db: DbDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    hub_id: int | None = Query(default=None),
    service_id: int | None = Query(default=None),
):
    from_date, to_date = _clamp_range(from_date, to_date)
    q = (
        select(Transaction.status, func.count().label("cnt"))
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
        )
        .group_by(Transaction.status)
        .order_by(func.count().desc())
    )
    if hub_id is not None:
        q = q.where(Transaction.hub_id == hub_id)
    if service_id is not None:
        q = q.where(Transaction.service_id == service_id)

    rows = (await db.execute(q)).all()
    return StatusDistributionResponse(
        statuses=[
            StatusCount(status=row.status or "UNKNOWN", count=row.cnt)
            for row in rows
        ]
    )


@router.get("/processing-time", response_model=ProcessingTimeResponse)
async def get_processing_time(
    db: DbDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    hub_id: int | None = Query(default=None),
    service_id: int | None = Query(default=None),
):
    """Return p50/p95 processing time in seconds for terminal transactions."""
    from_date, to_date = _clamp_range(from_date, to_date)
    terminal_values = [s.value for s in TERMINAL_STATUSES]

    q = (
        select(Transaction.created_date, Transaction.updated_date)
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
            Transaction.status.in_(terminal_values),
            Transaction.updated_date.is_not(None),
        )
    )
    if hub_id is not None:
        q = q.where(Transaction.hub_id == hub_id)
    if service_id is not None:
        q = q.where(Transaction.service_id == service_id)

    rows = (await db.execute(q)).all()

    durations = [
        (row.updated_date - row.created_date).total_seconds()
        for row in rows
        if row.created_date and row.updated_date and row.updated_date > row.created_date
    ]

    if not durations:
        return ProcessingTimeResponse(p50_seconds=None, p95_seconds=None, sample_size=0)

    durations.sort()
    n = len(durations)

    def percentile(data: list[float], p: float) -> float:
        idx = int(p / 100 * n)
        return data[min(idx, n - 1)]

    return ProcessingTimeResponse(
        p50_seconds=round(percentile(durations, 50), 2),
        p95_seconds=round(percentile(durations, 95), 2),
        sample_size=n,
    )


@router.get("/hub-breakdown", response_model=HubBreakdownResponse)
async def get_hub_breakdown(
    db: DbDep,
    cache: CacheDep,
    from_date: datetime = Query(default_factory=_default_from),
    to_date: datetime = Query(default_factory=_default_to),
    service_id: int | None = Query(default=None),
):
    from_date, to_date = _clamp_range(from_date, to_date)
    q = (
        select(
            Transaction.hub_id,
            Transaction.hub_name,
            func.count().label("total"),
            func.sum(_failed_case()).label("failed"),
            func.coalesce(func.sum(Transaction.remittance_amount), 0).label("volume"),
        )
        .where(
            Transaction.created_date >= _naive(from_date),
            Transaction.created_date <= _naive(to_date),
        )
        .group_by(Transaction.hub_id, Transaction.hub_name)
        .order_by(func.count().desc())
    )
    if service_id is not None:
        q = q.where(Transaction.service_id == service_id)

    rows = (await db.execute(q)).all()

    hubs = []
    for row in rows:
        total = row.total or 0
        failed = int(row.failed or 0)
        hub_id = int(row.hub_id) if row.hub_id is not None else None
        resolved_name = cache.partner_name(hub_id) or row.hub_name or "Unknown"
        hubs.append(
            HubMetric(
                hub_id=hub_id,
                hub_name=resolved_name,
                total=total,
                failed=failed,
                failure_rate=failed / total if total else 0.0,
                total_volume=float(row.volume or 0),
            )
        )

    return HubBreakdownResponse(hubs=hubs)
