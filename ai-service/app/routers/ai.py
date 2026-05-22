"""AI Assistant + Insights Engine API."""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import ReferenceCache, get_cache
from app.database import get_keycloak_db
from app.llm import complete, stream_response
from app.prompts import SYSTEM_PROMPT, build_context, insights_messages, nl_query_messages

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

DbDep    = Annotated[AsyncSession, Depends(get_keycloak_db)]
CacheDep = Annotated[ReferenceCache, Depends(get_cache)]


def _default_from() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=7)


def _default_to() -> datetime:
    return datetime.now(timezone.utc)


# --- Request / response models ---

class ChatRequest(BaseModel):
    message: str
    from_date: datetime | None = None
    to_date: datetime | None = None


class InsightsRequest(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None


class Anomaly(BaseModel):
    title: str
    detail: str
    severity: str  # low | medium | high


class Recommendation(BaseModel):
    action: str
    reason: str


class InsightsResponse(BaseModel):
    summary: str
    health: str   # good | warning | critical
    anomalies: list[Anomaly]
    recommendations: list[Recommendation]
    context_period: str


# --- Endpoints ---

@router.post("/chat")
async def chat(
    req: ChatRequest,
    db: DbDep,
    cache: CacheDep,
) -> StreamingResponse:
    """Stream an AI response to a natural language question about operations."""
    context = await build_context(
        db, cache,
        from_date=req.from_date,
        to_date=req.to_date,
    )
    messages = nl_query_messages(req.message, context)

    async def sse_generator():
        try:
            async for chunk in stream_response(messages, system=SYSTEM_PROMPT):
                # Server-Sent Events format
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as e:
            log.error("AI chat stream error: %s", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/insights", response_model=InsightsResponse)
async def generate_insights(
    req: InsightsRequest,
    db: DbDep,
    cache: CacheDep,
) -> InsightsResponse:
    """Generate a structured operational insights report for a time window."""
    from_date = req.from_date or _default_from()
    to_date   = req.to_date   or _default_to()

    context = await build_context(db, cache, from_date=from_date, to_date=to_date)
    messages = insights_messages(context)

    raw = await complete(messages, system=SYSTEM_PROMPT)

    # Parse JSON — strip any accidental fences
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("Could not parse insights JSON, returning raw as summary")
        data = {
            "summary": raw,
            "health": "warning",
            "anomalies": [],
            "recommendations": [],
        }

    period = f"{from_date.strftime('%Y-%m-%d')} → {to_date.strftime('%Y-%m-%d')}"

    return InsightsResponse(
        summary=data.get("summary", ""),
        health=data.get("health", "warning"),
        anomalies=[Anomaly(**a) for a in data.get("anomalies", [])],
        recommendations=[Recommendation(**r) for r in data.get("recommendations", [])],
        context_period=period,
    )
