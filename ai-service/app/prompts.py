"""Prompt templates and live context builder for the AI assistant."""

import json
from datetime import datetime, timedelta, timezone

_SGT = timezone(timedelta(hours=8))

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import ReferenceCache
from app.models.remittance import FAILED_STATUSES, Transaction

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an AI operations analyst for a remittance platform.
You have access to live transaction data and help operations teams understand
performance, diagnose failures, and identify trends.

Rules:
- NEVER include or request PII (sender/recipient names, phone numbers, dates of birth, account numbers).
- When you don't have enough data, say so clearly.
- Be concise and actionable. Prefer bullet points over long paragraphs.
- When asked for JSON output, return valid JSON only — no markdown fences, no explanation outside the JSON.
- Amounts are in SGD unless otherwise stated.
- Hubs: TELEPIN, WU (Western Union), THUNES, TRANGLO.
"""

# ---------------------------------------------------------------------------
# Context builder — fetches live summary from DB and formats for the prompt
# ---------------------------------------------------------------------------

async def build_context(
    db: AsyncSession,
    cache: ReferenceCache,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> str:
    """Return a structured text block describing current operational state."""
    if to_date is None:
        to_date = datetime.now(_SGT).replace(tzinfo=None)
    if from_date is None:
        from_date = to_date - timedelta(days=7)

    def naive(dt: datetime) -> datetime:
        """Convert to SGT-naive — DB stores TIMESTAMP WITHOUT TIME ZONE in SGT."""
        if dt.tzinfo:
            dt = dt.astimezone(_SGT)
        return dt.replace(tzinfo=None)

    # Kill any individual DB query that runs longer than 10 seconds
    await db.execute(text("SET LOCAL statement_timeout = '10000'"))

    failed_values = [s.value for s in FAILED_STATUSES]
    failed_case = case((Transaction.status.in_(failed_values), 1), else_=0)

    # Overall summary
    summary_row = (await db.execute(
        select(
            func.count().label("total"),
            func.sum(failed_case).label("failed"),
            func.coalesce(func.sum(Transaction.remittance_amount), 0).label("volume"),
        ).where(
            Transaction.created_date >= naive(from_date),
            Transaction.created_date <= naive(to_date),
        )
    )).one()

    total = summary_row.total or 0
    failed = int(summary_row.failed or 0)
    volume = float(summary_row.volume or 0)
    failure_rate = failed / total if total else 0.0

    # Per-hub breakdown
    hub_rows = (await db.execute(
        select(
            Transaction.hub_id,
            Transaction.hub_name,
            func.count().label("total"),
            func.sum(failed_case).label("failed"),
        ).where(
            Transaction.created_date >= naive(from_date),
            Transaction.created_date <= naive(to_date),
        )
        .group_by(Transaction.hub_id, Transaction.hub_name)
        .order_by(func.count().desc())
    )).all()

    # Status breakdown (top 10)
    status_rows = (await db.execute(
        select(Transaction.status, func.count().label("cnt"))
        .where(
            Transaction.created_date >= naive(from_date),
            Transaction.created_date <= naive(to_date),
        )
        .group_by(Transaction.status)
        .order_by(func.count().desc())
        .limit(10)
    )).all()

    # Top error codes
    error_rows = (await db.execute(
        select(Transaction.error_code, func.count().label("cnt"))
        .where(
            Transaction.created_date >= naive(from_date),
            Transaction.created_date <= naive(to_date),
            Transaction.error_code.is_not(None),
        )
        .group_by(Transaction.error_code)
        .order_by(func.count().desc())
        .limit(5)
    )).all()

    hub_lines = []
    for r in hub_rows:
        hub_id = int(r.hub_id) if r.hub_id else None
        name = cache.partner_name(hub_id) or r.hub_name or "Unknown"
        t = r.total or 0
        f = int(r.failed or 0)
        hub_lines.append(f"  - {name}: {t} transactions, {f} failed ({f/t*100:.1f}%)" if t else f"  - {name}: 0")

    status_lines = [f"  - {r.status}: {r.cnt}" for r in status_rows if r.status]
    error_lines  = [f"  - {r.error_code}: {r.cnt}" for r in error_rows if r.error_code]

    context = f"""=== LIVE OPERATIONAL CONTEXT ===
Period: {from_date.strftime('%Y-%m-%d %H:%M')} → {to_date.strftime('%Y-%m-%d %H:%M')} SGT

OVERALL:
  Total transactions : {total:,}
  Failed             : {failed:,} ({failure_rate*100:.1f}%)
  Total volume (SGD) : {volume:,.2f}

HUB BREAKDOWN:
{chr(10).join(hub_lines) or '  (no data)'}

STATUS DISTRIBUTION (top 10):
{chr(10).join(status_lines) or '  (no data)'}

TOP ERROR CODES:
{chr(10).join(error_lines) or '  (none)'}
================================="""

    return context


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def nl_query_messages(question: str, context: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": f"{context}\n\nQuestion: {question}",
        }
    ]


def insights_messages(context: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": f"""{context}

Analyse the operational data above and return a JSON object with this exact shape:
{{
  "summary": "2-3 sentence plain-English summary of the current operational state",
  "health": "good" | "warning" | "critical",
  "anomalies": [
    {{"title": "...", "detail": "...", "severity": "low"|"medium"|"high"}}
  ],
  "recommendations": [
    {{"action": "...", "reason": "..."}}
  ]
}}

Return JSON only.""",
        }
    ]
