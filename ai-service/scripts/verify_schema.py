"""Schema verification script.

Introspects SQLAlchemy model definitions and compares them against the connected database.
Reports columns that exist in the model but are missing from the DB (will cause crashes)
and columns in the DB that are not yet mapped in the model (safe, but informational).

Usage:
    cd ai-service
    source .venv/bin/activate
    python scripts/verify_schema.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(".env", override=True)

import asyncpg
from sqlalchemy import inspect as sa_inspect

from app.config import get_settings
from app.models.base import MlBase, KeycloakBase
import app.models.ml_schema          # noqa: F401 — register models
import app.models.service_management  # noqa: F401
import app.models.remittance          # noqa: F401
import app.models.customer            # noqa: F401
import app.models.payment             # noqa: F401


def collect_models(base) -> dict[str, dict[str, list[str]]]:
    """Return {schema.table: [mapped_column_names]} for all models on a declarative base."""
    result = {}
    for mapper in base.registry.mappers:
        table = mapper.persist_selectable
        schema = table.schema or "public"
        key = f"{schema}.{table.name}"
        result[key] = [col.name for col in table.columns]
    return result


async def get_db_columns(conn: asyncpg.Connection, schema: str, table: str) -> set[str]:
    rows = await conn.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = $1 AND table_name = $2
        """,
        schema, table,
    )
    return {r["column_name"] for r in rows}


async def verify(db_url: str, models: dict[str, list[str]], db_label: str) -> bool:
    url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(url)
    ok = True
    print(f"\n{'='*60}")
    print(f"  {db_label}")
    print(f"{'='*60}")
    try:
        for full_table in sorted(models):
            schema, table = full_table.split(".", 1)
            model_cols = set(models[full_table])
            db_cols = await get_db_columns(conn, schema, table)

            print(f"\n  [{full_table}]")

            if not db_cols:
                print("    WARNING  table not found in DB")
                ok = False
                continue

            missing_in_db    = model_cols - db_cols   # crashes the app
            missing_in_model = db_cols - model_cols   # safe, unmapped

            if not missing_in_db and not missing_in_model:
                print("    OK — all model columns present")
            for col in sorted(missing_in_db):
                print(f"    MISSING IN DB      {col}  <- remove from model")
                ok = False
            for col in sorted(missing_in_model):
                print(f"    unmapped in model  {col}")
    finally:
        await conn.close()
    return ok


async def main() -> None:
    cfg = get_settings()
    print(f"Verifying schema  APP_ENV={cfg.app_env}")

    ml_models = collect_models(MlBase)
    kc_models = collect_models(KeycloakBase)

    ml_ok = await verify(cfg.ml_db_url,      ml_models, f"ml_db  ({cfg.ml_db_url.split('@')[-1]})")
    kc_ok = await verify(cfg.keycloak_db_url, kc_models, f"keycloak  ({cfg.keycloak_db_url.split('@')[-1]})")

    print(f"\n{'='*60}")
    if ml_ok and kc_ok:
        print("  RESULT: all model columns exist in DB")
    else:
        print("  RESULT: FAILURES — fix MISSING IN DB columns before running the app")
    print(f"{'='*60}\n")
    sys.exit(0 if (ml_ok and kc_ok) else 1)


if __name__ == "__main__":
    asyncio.run(main())
