"""Query history router — CRUD for saved Text-to-SQL queries."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_portal_db
from app.models.portal import QueryHistory

router = APIRouter(prefix="/api/v1/history", tags=["history"])

MAX_HISTORY = 50


# --- Schemas ---

class HistoryEntryOut(BaseModel):
    id: str
    timestamp: datetime
    question: str
    sql: str
    is_favorite: bool

    model_config = {"from_attributes": True}


class CreateHistoryRequest(BaseModel):
    question: str
    sql: str


# --- Endpoints ---

@router.get("", response_model=list[HistoryEntryOut])
async def list_history(
    favorites: bool = False,
    db: AsyncSession = Depends(get_portal_db),
) -> list[QueryHistory]:
    stmt = select(QueryHistory).order_by(QueryHistory.timestamp.desc())
    if favorites:
        stmt = stmt.where(QueryHistory.is_favorite.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=HistoryEntryOut, status_code=201)
async def create_history(
    body: CreateHistoryRequest,
    db: AsyncSession = Depends(get_portal_db),
) -> QueryHistory:
    # Deduplicate: remove any previous entry with the same question
    await db.execute(
        delete(QueryHistory).where(QueryHistory.question == body.question)
    )

    # Trim to MAX_HISTORY - 1 oldest non-favorite entries to make room
    count_result = await db.execute(select(QueryHistory))
    all_entries = list(count_result.scalars().all())
    non_favorites = sorted(
        [e for e in all_entries if not e.is_favorite],
        key=lambda e: e.timestamp,
    )
    overflow = len(all_entries) - MAX_HISTORY + 1
    if overflow > 0:
        ids_to_delete = [e.id for e in non_favorites[:overflow]]
        if ids_to_delete:
            await db.execute(delete(QueryHistory).where(QueryHistory.id.in_(ids_to_delete)))

    entry = QueryHistory(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        question=body.question,
        sql=body.sql,
        is_favorite=False,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{entry_id}/favorite", response_model=HistoryEntryOut)
async def toggle_favorite(
    entry_id: str,
    db: AsyncSession = Depends(get_portal_db),
) -> QueryHistory:
    entry = await db.get(QueryHistory, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    entry.is_favorite = not entry.is_favorite
    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
async def delete_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_portal_db),
) -> None:
    entry = await db.get(QueryHistory, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="History entry not found")
    await db.delete(entry)
    await db.commit()


@router.delete("", status_code=204)
async def clear_history(
    db: AsyncSession = Depends(get_portal_db),
) -> None:
    """Delete all non-favorite entries."""
    await db.execute(delete(QueryHistory).where(QueryHistory.is_favorite.is_(False)))
    await db.commit()
