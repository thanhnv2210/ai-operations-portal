"""Text-to-SQL assistant endpoint.

POST /api/v1/assistant/query
  body:  { "question": str }
  stream: text/event-stream — typed SSE events from app.services.text_to_sql
"""

import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_keycloak_db, get_ml_db
from app.services import text_to_sql

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

KeycloakDep = Annotated[AsyncSession, Depends(get_keycloak_db)]
MlDep = Annotated[AsyncSession, Depends(get_ml_db)]

_MAX_QUESTION_LEN = 500


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=_MAX_QUESTION_LEN)


@router.post("/query")
async def query(
    req: QueryRequest,
    keycloak_db: KeycloakDep,
    ml_db: MlDep,
) -> StreamingResponse:
    """Convert a natural language question to SQL, execute it, and stream a plain-English explanation."""

    async def sse_generator():
        try:
            async for event in text_to_sql.run(req.question, keycloak_db, ml_db):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:
            log.error("Text-to-SQL stream error: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'code': 'internal_error', 'message': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
