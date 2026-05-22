import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

log = logging.getLogger(__name__)

# Engines are created lazily at startup via init_engines() called from lifespan.
_ml_engine = None
_keycloak_engine = None

_MlSession: async_sessionmaker[AsyncSession] | None = None
_KeycloakSession: async_sessionmaker[AsyncSession] | None = None


def init_engines() -> None:
    """Create both async engines. Call once from the FastAPI lifespan."""
    global _ml_engine, _keycloak_engine, _MlSession, _KeycloakSession

    cfg = get_settings()

    _ml_engine = create_async_engine(
        cfg.ml_db_url,
        echo=cfg.is_local,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )
    _MlSession = async_sessionmaker(
        _ml_engine, expire_on_commit=False, class_=AsyncSession
    )

    _keycloak_engine = create_async_engine(
        cfg.keycloak_db_url,
        echo=cfg.is_local,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )
    _KeycloakSession = async_sessionmaker(
        _keycloak_engine, expire_on_commit=False, class_=AsyncSession
    )

    log.info("DB engines initialised (ml_db + keycloak)")


async def dispose_engines() -> None:
    """Dispose both engines. Call from lifespan shutdown."""
    if _ml_engine:
        await _ml_engine.dispose()
    if _keycloak_engine:
        await _keycloak_engine.dispose()
    log.info("DB engines disposed")


# --- FastAPI dependency injectors ---

async def get_ml_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session connected to ml_db (non-secure, product config)."""
    assert _MlSession is not None, "call init_engines() first"
    async with _MlSession() as session:
        yield session


async def get_keycloak_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session connected to the keycloak DB (secure, transactional)."""
    assert _KeycloakSession is not None, "call init_engines() first"
    async with _KeycloakSession() as session:
        yield session
