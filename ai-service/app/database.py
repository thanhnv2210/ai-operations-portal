import logging
from collections.abc import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings


def _asyncpg_ssl_args(url: str) -> tuple[str, dict]:
    """Strip sslmode from URL and return (clean_url, connect_args).

    asyncpg does not accept 'sslmode' as a query parameter. SQLAlchemy 2.x
    passes URL query params directly to asyncpg.connect(), causing a TypeError.
    Instead, ssl is configured via connect_args={"ssl": True}.
    """
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)
    sslmode = params.pop("sslmode", [None])[0]
    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))
    connect_args: dict = {}
    if sslmode in ("require", "verify-ca", "verify-full"):
        connect_args["ssl"] = True
    return clean_url, connect_args

log = logging.getLogger(__name__)

# Engines are created lazily at startup via init_engines() called from lifespan.
_ml_engine = None
_keycloak_engine = None
_portal_engine = None

_MlSession: async_sessionmaker[AsyncSession] | None = None
_KeycloakSession: async_sessionmaker[AsyncSession] | None = None
_PortalSession: async_sessionmaker[AsyncSession] | None = None


async def init_portal_db() -> None:
    """Create portal engine and run DDL (create tables if not exist). Call from lifespan."""
    global _portal_engine, _PortalSession

    from app.models.portal import PortalBase

    cfg = get_settings()
    connect_args = {"check_same_thread": False} if "sqlite" in cfg.portal_db_url else {}
    _portal_engine = create_async_engine(
        cfg.portal_db_url,
        echo=cfg.is_local,
        connect_args=connect_args,
    )
    _PortalSession = async_sessionmaker(
        _portal_engine, expire_on_commit=False, class_=AsyncSession
    )
    async with _portal_engine.begin() as conn:
        await conn.run_sync(PortalBase.metadata.create_all)

    log.info("Portal DB initialised → %s", cfg.portal_db_url)


def init_engines() -> None:
    """Create both async engines. Call once from the FastAPI lifespan."""
    global _ml_engine, _keycloak_engine, _MlSession, _KeycloakSession

    cfg = get_settings()

    ml_pool_size = 5 if cfg.is_local else 2
    ml_url, ml_connect_args = _asyncpg_ssl_args(cfg.ml_db_url)
    _ml_engine = create_async_engine(
        ml_url,
        echo=cfg.is_local,
        pool_pre_ping=True,
        pool_size=ml_pool_size,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args=ml_connect_args,
    )
    _MlSession = async_sessionmaker(
        _ml_engine, expire_on_commit=False, class_=AsyncSession
    )

    keycloak_pool_size = 10 if cfg.is_local else 3
    kc_url, kc_connect_args = _asyncpg_ssl_args(cfg.keycloak_db_url)
    _keycloak_engine = create_async_engine(
        kc_url,
        echo=cfg.is_local,
        pool_pre_ping=True,
        pool_size=keycloak_pool_size,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800,
        connect_args=kc_connect_args,
    )
    _KeycloakSession = async_sessionmaker(
        _keycloak_engine, expire_on_commit=False, class_=AsyncSession
    )

    log.info("DB engines initialised (ml_db + keycloak)")


async def dispose_engines() -> None:
    """Dispose all engines. Call from lifespan shutdown."""
    if _ml_engine:
        await _ml_engine.dispose()
    if _keycloak_engine:
        await _keycloak_engine.dispose()
    if _portal_engine:
        await _portal_engine.dispose()
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


async def get_portal_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a session connected to the portal DB (read-write, portal-owned data)."""
    assert _PortalSession is not None, "call init_portal_db() first"
    async with _PortalSession() as session:
        yield session
