import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# load_dotenv must run before any local import reads env vars at module level.
_app_env = os.getenv("APP_ENV", "local")
if _app_env == "local":
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=f".env.{_app_env}", override=False)

import app.config_store as config_store  # noqa: E402
from app.cache import get_cache, load as load_cache  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import dispose_engines, get_ml_db, init_engines  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    log.info("Starting ai-service [env=%s]", cfg.app_env)
    init_engines()
    config_store.init()

    # Populate reference data cache from ml_db
    async for ml_session in get_ml_db():
        await load_cache(ml_session)

    yield

    log.info("Shutting down ai-service")
    await dispose_engines()


def create_app() -> FastAPI:
    cfg = get_settings()

    app = FastAPI(
        title="AI Operations Portal — ai-service",
        version="0.1.0",
        docs_url="/docs" if cfg.is_local else None,
        redoc_url="/redoc" if cfg.is_local else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --- Routers ---
    from app.routers.admin import router as admin_router
    from app.routers.ai import router as ai_router
    from app.routers.dashboard import router as dashboard_router
    from app.routers.transactions import router as transactions_router
    app.include_router(dashboard_router)
    app.include_router(transactions_router)
    app.include_router(ai_router)
    app.include_router(admin_router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict:
        cache = get_cache()
        return {
            "status": "ok",
            "env": cfg.app_env,
            "cache": {
                "loaded": cache.loaded,
                "countries": len(cache.countries_by_id),
                "services": len(cache.services_by_id),
                "partners": len(cache.partners_by_id),
            },
        }

    return app


app = create_app()
