"""Portal-owned models — stored in the portal DB (SQLite locally, PostgreSQL in prod).

These are tables the portal itself writes to (query history, saved searches, etc.).
They are completely separate from ml_db and keycloak, which are read-only sources.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class PortalBase(DeclarativeBase):
    """Base for all portal-owned models."""


class QueryHistory(PortalBase):
    __tablename__ = "query_history"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(String, nullable=False)
    sql: Mapped[str] = mapped_column(Text, nullable=False)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
