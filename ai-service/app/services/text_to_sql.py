"""Text-to-SQL pipeline.

Full flow: NL question → SQL generation → safety validation → EXPLAIN dry-run
           → DB routing → execution → plain-English explanation (streaming).

Yields typed event dicts consumed by the SSE router:
  {"type": "status",  "text": "..."}          — pipeline progress message
  {"type": "sql",     "sql": "..."}           — generated SQL (show to user)
  {"type": "token",   "text": "..."}          — streamed explanation token
  {"type": "error",   "code": "...",
                      "message": "..."}       — terminal error
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.llm import complete, stream_response
from app.observability import get_tracer
from app.schema_context.loader import get_schema_context
from app.schema_context.relationships import get_relationships
from app.schema_context.status_ref import get_status_ref

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------

_WRITE_OP_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|TRUNCATE|ALTER|GRANT|REVOKE|COPY|EXECUTE|EXEC)\b",
    re.IGNORECASE,
)

# Schemas → which engine to use
_KEYCLOAK_SCHEMAS = {"remittance", "customer", "payment"}
_MLDB_SCHEMAS = {"ml_schema", "service_management"}

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a PostgreSQL SQL expert for a remittance fintech platform.

Task: Convert the user's natural language question into a single valid PostgreSQL SELECT query.

Rules:
- Output ONLY the SQL statement — no explanation, no markdown fences, no commentary.
- ONLY generate SELECT statements. Never INSERT, UPDATE, DELETE, DROP, CREATE, TRUNCATE, or any DDL/DML.
- Always use schema-qualified table names (e.g. remittance.transaction, not just transaction).
- Use PostgreSQL syntax: date_trunc, EXTRACT, ::date casts, INTERVAL literals.
- created_date stores timestamps in SGT (UTC+8) with no timezone info in the DB.
- For "today": created_date::date = CURRENT_DATE
- For failure rate: use CASE WHEN status IN (<failed statuses>) THEN 1 ELSE 0 END inside COUNT/SUM.
- Prefer snapshot columns hub_name and service_name from remittance.transaction over cross-DB joins.
- Generate queries targeting ONE database only (Keycloak DB or ML DB — never mix).
- Add LIMIT 1000 to any query that could return a large number of rows.
"""

_FEW_SHOT = """\
Examples:

Q: How many transactions failed today?
A: SELECT COUNT(*) AS failed_count FROM remittance.transaction WHERE status IN ('TRANSACTION_FAILED','TRANSACTION_DECLINED','PAYMENT_FAILED','PAYMENT_VALIDATION_FAILED','PAYMENT_RESERVATION_FAILED','PAYMENT_ACCEPTANCE_FAILED','SOF_PAY_FAILED','REFUND_FAILED','FRAUD_CHECK_FAILED','FRAUD_CHECK_DECLINED') AND created_date::date = CURRENT_DATE;

Q: Failure rate by hub this month?
A: SELECT hub_name, COUNT(*) AS total, SUM(CASE WHEN status IN ('TRANSACTION_FAILED','TRANSACTION_DECLINED','PAYMENT_FAILED','PAYMENT_VALIDATION_FAILED','PAYMENT_RESERVATION_FAILED','PAYMENT_ACCEPTANCE_FAILED','SOF_PAY_FAILED','REFUND_FAILED','FRAUD_CHECK_FAILED','FRAUD_CHECK_DECLINED') THEN 1 ELSE 0 END) AS failed, ROUND(SUM(CASE WHEN status IN ('TRANSACTION_FAILED','TRANSACTION_DECLINED','PAYMENT_FAILED','PAYMENT_VALIDATION_FAILED','PAYMENT_RESERVATION_FAILED','PAYMENT_ACCEPTANCE_FAILED','SOF_PAY_FAILED','REFUND_FAILED','FRAUD_CHECK_FAILED','FRAUD_CHECK_DECLINED') THEN 1 ELSE 0 END)::numeric / NULLIF(COUNT(*),0) * 100, 2) AS failure_rate_pct FROM remittance.transaction WHERE created_date >= date_trunc('month', CURRENT_DATE) GROUP BY hub_name ORDER BY total DESC;

Q: Top 5 corridors by volume this week?
A: SELECT service_name, COUNT(*) AS tx_count, ROUND(SUM(remittance_amount)::numeric, 2) AS total_volume_sgd FROM remittance.transaction WHERE created_date >= date_trunc('week', CURRENT_DATE) AND status IN ('TRANSACTION_SUCCESS','TRANSACTION_COMPLETED','TRANSACTION_CONFIRMED') GROUP BY service_name ORDER BY total_volume_sgd DESC LIMIT 5;

Q: Most common error codes in the last 7 days?
A: SELECT error_code, COUNT(*) AS occurrences FROM remittance.transaction WHERE error_code IS NOT NULL AND created_date >= CURRENT_DATE - INTERVAL '7 days' GROUP BY error_code ORDER BY occurrences DESC LIMIT 10;

Q: Hourly transaction volume in the last 24 hours?
A: SELECT date_trunc('hour', created_date) AS hour, COUNT(*) AS total, SUM(CASE WHEN status IN ('TRANSACTION_FAILED','TRANSACTION_DECLINED','PAYMENT_FAILED','PAYMENT_VALIDATION_FAILED','PAYMENT_RESERVATION_FAILED','PAYMENT_ACCEPTANCE_FAILED','SOF_PAY_FAILED','REFUND_FAILED','FRAUD_CHECK_FAILED','FRAUD_CHECK_DECLINED') THEN 1 ELSE 0 END) AS failed FROM remittance.transaction WHERE created_date >= NOW() - INTERVAL '24 hours' GROUP BY 1 ORDER BY 1;

Q: Which active corridors send to the Philippines?
A: SELECT system_name, service_name_display, min_amount, max_amount FROM service_management.remit_service WHERE foreign_country_name ILIKE '%Philippines%' AND status = 'ACTIVATE' AND is_available = true ORDER BY system_name;
"""

_EXPLAIN_SYSTEM = (
    "You are an AI operations analyst for a remittance platform. "
    "Summarise query results in 2-4 concise sentences for the operations team. "
    "Be specific about numbers. Never mention PII."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_engine(sql: str) -> str:
    """Return 'keycloak', 'ml_db', or 'cross' based on schemas referenced."""
    sql_lower = sql.lower()
    has_keycloak = any(f"{s}." in sql_lower for s in _KEYCLOAK_SCHEMAS)
    has_mldb = any(f"{s}." in sql_lower for s in _MLDB_SCHEMAS)
    if has_keycloak and has_mldb:
        return "cross"
    if has_mldb:
        return "ml_db"
    return "keycloak"  # default — most queries target remittance.transaction


def _validate(sql: str) -> str | None:
    """Return an error message if unsafe, None if the SQL is acceptable."""
    stripped = sql.strip()
    if not stripped.upper().startswith("SELECT"):
        return "Generated query does not start with SELECT — only read queries are allowed."
    if _WRITE_OP_RE.search(stripped):
        return "Query contains a disallowed operation. Only SELECT statements are permitted."
    return None


async def _generate_sql(question: str) -> str:
    """Call Claude to turn the question into a SQL SELECT statement."""
    schema = get_schema_context()
    status_ref = get_status_ref()
    relationships = get_relationships()

    prompt = (
        f"{schema}\n\n"
        f"{status_ref}\n\n"
        f"{relationships}\n\n"
        f"{_FEW_SHOT}\n\n"
        f"Q: {question}\nA:"
    )

    raw = await complete(
        messages=[{"role": "user", "content": prompt}],
        system=_SYSTEM_PROMPT,
        max_tokens=1024,
    )

    # Strip any accidental markdown fences the model may have added
    cleaned = re.sub(r"^```[a-z]*\n?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    return cleaned


async def _explain_results(
    question: str,
    sql: str,
    rows: list[dict],
) -> AsyncGenerator[str, None]:
    """Stream a plain-English explanation of the query results."""
    rows_preview = rows[:50]
    rows_text = json.dumps(rows_preview, default=str, indent=2)
    total = len(rows)

    prompt = (
        f"Question: {question}\n\n"
        f"SQL executed:\n{sql}\n\n"
        f"Results ({total} row{'s' if total != 1 else ''} total"
        f"{', showing first 50' if total > 50 else ''}):\n{rows_text}\n\n"
        "Provide a concise 2-4 sentence plain-English summary for the operations team. "
        "Be specific about numbers. Do not repeat the SQL."
    )

    async for token in stream_response(
        messages=[{"role": "user", "content": prompt}],
        system=_EXPLAIN_SYSTEM,
    ):
        yield token


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

async def run(
    question: str,
    keycloak_session: AsyncSession,
    ml_session: AsyncSession,
) -> AsyncGenerator[dict, None]:
    """Execute the full Text-to-SQL pipeline, yielding typed SSE event dicts."""
    tracer = get_tracer()

    with tracer.trace(
        "text_to_sql",
        input={"question": question},
        metadata={"pipeline": "text_to_sql"},
        tags=[get_settings().app_env],
    ) as trace:

        # ── Step 1: Generate SQL ─────────────────────────────────────────────
        yield {"type": "status", "text": "Generating SQL..."}
        try:
            with trace.span("generate_sql", input={"question": question}) as span:
                sql = await asyncio.wait_for(_generate_sql(question), timeout=60)
                span.set_output({"sql": sql})
        except asyncio.TimeoutError:
            trace.update(output={"error": "sql_generation_timeout"})
            yield {"type": "error", "code": "sql_generation_failed", "message": "SQL generation timed out."}
            return
        except Exception as exc:
            log.error("SQL generation failed: %s", exc)
            trace.update(output={"error": "sql_generation_failed"})
            yield {"type": "error", "code": "sql_generation_failed", "message": "Failed to generate SQL for that question."}
            return

        # ── Step 2: Safety validation ────────────────────────────────────────
        with trace.span("validate_sql", input={"sql": sql}) as span:
            err = _validate(sql)
            span.set_output({"valid": err is None, "error": err})
        if err:
            trace.update(output={"error": "sql_validation_rejected", "sql": sql})
            yield {"type": "error", "code": "sql_validation_rejected", "message": err}
            return

        # Emit the SQL so the frontend can show it before execution
        yield {"type": "sql", "sql": sql}

        # ── Step 3: DB routing ───────────────────────────────────────────────
        engine_target = _detect_engine(sql)
        trace.update(metadata={"engine": engine_target, "sql": sql})

        if engine_target == "cross":
            trace.update(output={"error": "cross_db_query"})
            yield {
                "type": "error",
                "code": "sql_validation_rejected",
                "message": (
                    "Query spans two databases (Keycloak + ML DB). "
                    "Please ask about transaction data or reference data separately."
                ),
            }
            return

        session = keycloak_session if engine_target == "keycloak" else ml_session

        # ── Step 4: EXPLAIN dry-run ──────────────────────────────────────────
        yield {"type": "status", "text": "Validating query..."}
        try:
            with trace.span("explain_dry_run", input={"sql": sql}) as span:
                await session.execute(text(f"EXPLAIN {sql}"))
                span.set_output({"valid": True})
        except Exception as exc:
            trace.update(output={"error": "explain_failed", "detail": str(exc)})
            yield {
                "type": "error",
                "code": "sql_generation_failed",
                "message": f"Query validation failed — likely an invalid column or table name. Detail: {exc}",
            }
            return

        # ── Step 5: Execute ──────────────────────────────────────────────────
        yield {"type": "status", "text": "Executing query..."}
        try:
            with trace.span("execute_sql", input={"sql": sql, "engine": engine_target}) as span:
                result = await asyncio.wait_for(
                    session.execute(text(sql)),
                    timeout=15,
                )
                rows_raw = result.fetchall()
                keys = list(result.keys())
                rows = [dict(zip(keys, row)) for row in rows_raw]
                span.set_output({"row_count": len(rows)})
        except asyncio.TimeoutError:
            trace.update(output={"error": "db_timeout"})
            yield {
                "type": "error",
                "code": "db_execution_error",
                "message": "Query timed out after 15 seconds — try adding a narrower date range or filter.",
            }
            return
        except Exception as exc:
            log.error("Query execution error: %s", exc)
            trace.update(output={"error": "db_execution_error", "detail": str(exc)})
            yield {"type": "error", "code": "db_execution_error", "message": f"Query execution failed: {exc}"}
            return

        if not rows:
            trace.update(output={"error": "no_results", "sql": sql})
            yield {"type": "error", "code": "no_results", "message": "No data found for that query."}
            return

        # ── Step 6: Stream explanation ───────────────────────────────────────
        yield {"type": "status", "text": "Generating explanation..."}
        explanation_tokens: list[str] = []
        with trace.span("stream_explanation", input={"row_count": len(rows)}) as span:
            async for token in _explain_results(question, sql, rows):
                explanation_tokens.append(token)
                yield {"type": "token", "text": token}
            span.set_output({"explanation_length": sum(len(t) for t in explanation_tokens)})

        trace.set_output({
            "sql": sql,
            "engine": engine_target,
            "row_count": len(rows),
            "explanation_chars": sum(len(t) for t in explanation_tokens),
        })
