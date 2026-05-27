"""Pytest configuration.

Sets required environment variables before any app module is imported.
All unit tests in this suite are pure-logic tests — no DB or LLM calls.
"""

import os

# Must be set before app.config is imported via any test module.
os.environ.setdefault("APP_ENV", "ci")
os.environ.setdefault("ML_DB_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("KEYCLOAK_DB_URL", "postgresql+asyncpg://x:x@localhost/x")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
