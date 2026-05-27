"""Embedding model abstraction.

Priority:
  1. OpenAI text-embedding-3-small — when OPENAI_API_KEY is set and openai package is installed.
  2. Ollama nomic-embed-text — local fallback via httpx (requires: ollama pull nomic-embed-text).

Both return list[list[float]] — a vector per input text.
"""

import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

# Detect openai availability once at import time
try:
    from openai import AsyncOpenAI as _AsyncOpenAI
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

_OPENAI_MODEL = "text-embedding-3-small"
_OLLAMA_MODEL = "nomic-embed-text"
_BATCH_SIZE = 100


async def embed(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts. Returns one float vector per text."""
    if not texts:
        return []

    cfg = get_settings()
    if _OPENAI_AVAILABLE and cfg.openai_api_key:
        log.debug("Embedding %d texts via OpenAI %s", len(texts), _OPENAI_MODEL)
        return await _openai_embed(texts, cfg.openai_api_key)

    log.debug("Embedding %d texts via Ollama %s", len(texts), _OLLAMA_MODEL)
    return await _ollama_embed(texts, cfg.ollama_base_url)


async def _openai_embed(texts: list[str], api_key: str) -> list[list[float]]:
    client = _AsyncOpenAI(api_key=api_key)
    results: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        resp = await client.embeddings.create(model=_OPENAI_MODEL, input=batch)
        results.extend(d.embedding for d in resp.data)
    return results


async def _ollama_embed(texts: list[str], base_url: str) -> list[list[float]]:
    """Call Ollama's native /api/embeddings endpoint for each text."""
    results: list[list[float]] = []
    async with httpx.AsyncClient(timeout=60) as client:
        for text in texts:
            resp = await client.post(
                f"{base_url}/api/embeddings",
                json={"model": _OLLAMA_MODEL, "prompt": text},
            )
            resp.raise_for_status()
            results.append(resp.json()["embedding"])
    return results
