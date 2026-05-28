"""Hybrid retriever: vector search (ChromaDB) + BM25 keyword search, merged with RRF.

Reciprocal Rank Fusion (k=60):
  For each result in both ranked lists:  score += 1 / (rank + 1 + k)
  Final ranking = summed scores across both lists → top-6 unique chunks.

Why RRF over weighted fusion:
  - No hyperparameter tuning needed.
  - Vector search handles semantic similarity ("PII", "sensitive fields").
  - BM25 handles exact terms ("sender_msisdn", "remit_service_id").
  - RRF reliably combines both without manual weight balancing.

BM25 index is built in memory at API startup (load_bm25_from_store) and
rebuilt after each ingest run (rebuild_bm25).
"""

import logging
from typing import Any

from rank_bm25 import BM25Okapi

from app.rag.store import get_collection

log = logging.getLogger(__name__)

# --- BM25 in-memory state ---

_bm25: BM25Okapi | None = None
_bm25_corpus: list[dict] = []   # [{id, text, source_file, section_title, table_name}]

_RRF_K = 60
_VECTOR_TOP_N = 8
_BM25_TOP_N = 8
_FINAL_TOP_K = 6

# Minimum vector similarity (1 - cosine_distance/2) to proceed to Claude.
# Below this threshold the docs are considered too distant → grounding guard fires.
SIMILARITY_THRESHOLD = 0.40


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def rebuild_bm25(chunks: list[dict]) -> None:
    """Rebuild the BM25 index from a list of chunk dicts.

    Each dict must have at least: {id, text, source_file, section_title, table_name}.
    Called after ingestion and at startup (via load_bm25_from_store).
    """
    global _bm25, _bm25_corpus
    _bm25_corpus = chunks
    if not chunks:
        _bm25 = None
        log.info("BM25 index cleared (no chunks)")
        return
    corpus = [_tokenize(c["text"]) for c in chunks]
    _bm25 = BM25Okapi(corpus)
    log.info("BM25 index built over %d chunks", len(chunks))


def load_bm25_from_store() -> None:
    """Load all chunks from ChromaDB and build the BM25 index.

    Called once from FastAPI lifespan at startup.
    No-op if the collection is empty (before first ingest).
    """
    col = get_collection()
    count = col.count()
    if count == 0:
        log.info("ChromaDB collection is empty — BM25 index not built (run ingest first)")
        return

    result = col.get(include=["documents", "metadatas"])
    chunks = [
        {
            "id":            doc_id,
            "text":          doc,
            "source_file":   meta.get("source_file", ""),
            "section_title": meta.get("section_title", ""),
            "table_name":    meta.get("table_name", ""),
        }
        for doc_id, doc, meta in zip(
            result["ids"], result["documents"], result["metadatas"]
        )
    ]
    rebuild_bm25(chunks)


def _vector_search(query_embedding: list[float]) -> list[dict]:
    """Query ChromaDB and return top-N results with similarity scores."""
    col = get_collection()
    if col.count() == 0:
        return []

    res = col.query(
        query_embeddings=[query_embedding],
        n_results=min(_VECTOR_TOP_N, col.count()),
        include=["documents", "metadatas", "distances"],
    )

    results = []
    for doc_id, doc, meta, dist in zip(
        res["ids"][0],
        res["documents"][0],
        res["metadatas"][0],
        res["distances"][0],
    ):
        # ChromaDB cosine distance ∈ [0, 2]; convert to similarity ∈ [0, 1]
        similarity = max(0.0, 1.0 - dist / 2.0)
        results.append({
            "id":            doc_id,
            "text":          doc,
            "source_file":   meta.get("source_file", ""),
            "section_title": meta.get("section_title", ""),
            "table_name":    meta.get("table_name", ""),
            "vector_score":  round(similarity, 4),
        })
    return results


def _bm25_search(question: str) -> list[dict]:
    """Search the in-memory BM25 index and return top-N results."""
    if _bm25 is None or not _bm25_corpus:
        return []

    scores = _bm25.get_scores(_tokenize(question))
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:_BM25_TOP_N]

    results = []
    for idx in top_indices:
        if scores[idx] <= 0:
            break
        chunk = _bm25_corpus[idx]
        results.append({**chunk, "bm25_score": round(float(scores[idx]), 4)})
    return results


def _rrf_merge(
    vector_results: list[dict],
    bm25_results: list[dict],
) -> list[dict]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    rrf_scores: dict[str, float] = {}
    chunk_by_id: dict[str, dict] = {}

    for rank, chunk in enumerate(vector_results):
        cid = chunk["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (rank + 1 + _RRF_K)
        chunk_by_id[cid] = chunk

    for rank, chunk in enumerate(bm25_results):
        cid = chunk["id"]
        rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (rank + 1 + _RRF_K)
        if cid not in chunk_by_id:
            chunk_by_id[cid] = chunk

    sorted_ids = sorted(rrf_scores, key=lambda k: rrf_scores[k], reverse=True)[:_FINAL_TOP_K]
    return [
        {**chunk_by_id[cid], "rrf_score": round(rrf_scores[cid], 6)}
        for cid in sorted_ids
    ]


async def retrieve(
    question: str,
    question_embedding: list[float] | None,
) -> tuple[list[dict], float]:
    """Hybrid retrieval.

    When question_embedding is None (no embedding service available), falls back
    to BM25-only and bypasses the vector grounding guard.

    Returns:
      (chunks, best_vector_score)
        chunks            — top-6 merged results (each has text, section_title, source_file, rrf_score, vector_score)
        best_vector_score — highest vector similarity; 1.0 in BM25-only mode to bypass grounding guard
    """
    bm25_results = _bm25_search(question)

    if question_embedding is None:
        # No embedding service — BM25-only mode
        if not bm25_results:
            return [], 0.0
        chunks = [
            {**c, "rrf_score": round(1.0 / (rank + 1 + _RRF_K), 6), "vector_score": 0.0}
            for rank, c in enumerate(bm25_results[:_FINAL_TOP_K])
        ]
        return chunks, 1.0  # score=1.0 bypasses the grounding guard

    vector_results = _vector_search(question_embedding)

    if not vector_results and not bm25_results:
        return [], 0.0

    merged = _rrf_merge(vector_results, bm25_results)
    best_score = max((c.get("vector_score", 0.0) for c in merged), default=0.0)
    return merged, best_score
