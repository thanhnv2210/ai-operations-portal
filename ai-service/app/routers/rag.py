"""RAG knowledge base endpoints.

GET  /api/v1/rag/status  — collection stats (doc_count, last_ingested_at)
POST /api/v1/rag/query   — ask a question; returns {answer, sources}
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.rag import chain, store

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])

_MAX_QUESTION_LEN = 500


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=_MAX_QUESTION_LEN)


class SourceChunk(BaseModel):
    chunk_text: str
    section_title: str
    source_file: str
    vector_score: float
    rrf_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]


@router.get("/status")
async def rag_status() -> dict:
    """Return ChromaDB collection stats."""
    return store.get_status()


@router.post("/query", response_model=QueryResponse)
async def rag_query(req: QueryRequest) -> QueryResponse:
    """Answer a question grounded in the ingested knowledge base."""
    if store.get_collection().count() == 0:
        raise HTTPException(
            status_code=503,
            detail="Knowledge base is empty. Run: python -m app.rag.ingest",
        )

    try:
        result = await chain.query(req.question)
    except Exception as exc:
        log.error("RAG chain error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return QueryResponse(
        answer=result["answer"],
        sources=[SourceChunk(**s) for s in result["sources"]],
    )
