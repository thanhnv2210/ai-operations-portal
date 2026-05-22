import logging
import os
from functools import lru_cache

from dotenv import load_dotenv

# Load env file BEFORE pydantic-settings reads environment.
# local → .env.local, ci/uat → env vars injected by platform (no file).
_app_env = os.getenv("APP_ENV", "local")
if _app_env == "local":
    load_dotenv(dotenv_path=f".env.{_app_env}", override=False)

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

    # --- AI ---
    anthropic_api_key: str = Field(..., description="Anthropic API key")
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
        default="mistral",
        description="Ollama model to use as fallback",
    )

    # --- CORS ---
    cors_origins: list[str] = Field(
        default=["http://localhost:3001"],
        description="Allowed CORS origins",
    )

    @property
    def is_local(self) -> bool:
        return self.app_env == "local"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()  # type: ignore[call-arg]
    log.info("Config loaded: env=%s", settings.app_env)
    return settings
