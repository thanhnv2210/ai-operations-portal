import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

# Load env file BEFORE pydantic-settings reads environment.
# local → .env.local, ci/uat → env vars injected by platform (no file).
_app_env = os.getenv("APP_ENV", "local")
if _app_env == "local":
    load_dotenv(dotenv_path=f".env.{_app_env}", override=False)
    load_dotenv(dotenv_path=".env", override=False)

import json

from pydantic import Field  # noqa: E402  (must come after load_dotenv)
from pydantic_settings import BaseSettings, SettingsConfigDict  # noqa: E402

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # For non-local envs, vars come from the OS environment only.
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    # --- Environment ---
    app_env: str = Field(..., description="One of: local, ci, uat")

    # --- Database ---
    ml_db_url: str = Field(..., description="postgresql+asyncpg URL for ml_db")
    keycloak_db_url: str = Field(..., description="postgresql+asyncpg URL for keycloak DB")
    portal_db_url: str = Field(
        default="sqlite+aiosqlite:///./portal_data.db",
        description="Portal-owned DB for query history etc. SQLite by default; swap to PostgreSQL in prod.",
    )

    # --- AI ---
    anthropic_api_key: str = Field(..., description="Anthropic API key")
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key (optional — used for RAG embeddings via text-embedding-3-small)",
    )
    anthropic_model: str = Field(
        default="claude-opus-4-6",
        description="Primary Anthropic model ID",
    )
    anthropic_concurrency: int = Field(
        default=5,
        description="Max concurrent Anthropic API calls",
    )

    # Ollama fallback (local or sidecar)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama OpenAI-compatible endpoint",
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Ollama model to use as fallback",
    )

    # --- CORS ---
    # Stored as a raw string so pydantic-settings does not attempt json.loads()
    # before we can sanitise the value. Platforms like Render may inject an empty
    # string when a variable is declared but not given a value, which would crash
    # the list[str] parser. Use the cors_origins_list property everywhere instead.
    cors_origins: str = Field(
        default='["http://localhost:3007"]',
        description="Allowed CORS origins — JSON array string or comma-separated",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        val = self.cors_origins.strip()
        if not val:
            return ["*"]
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            # accept comma-separated fallback: http://a.com,http://b.com
            return [v.strip() for v in val.split(",") if v.strip()]

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    log.info("Config loaded: env=%s", settings.app_env)
    return settings
