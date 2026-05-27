"""RAG ingestion CLI.

Usage (from ai-service/ directory):
    python -m app.rag.ingest

What it does:
  1. Loads docs from docs/database-design.md (and any other configured paths).
  2. Chunks each document by Markdown headers.
  3. Embeds all chunks (OpenAI or Ollama — depends on OPENAI_API_KEY env var).
  4. Upserts into ChromaDB collection 'ai_ops_portal_docs'.
  5. Rebuilds the in-memory BM25 index (for the running API server, if any).
  6. Writes rag_data/meta.json with last_ingested_at timestamp.

Re-running is idempotent — ChromaDB upserts by ID, so duplicate chunks are updated in place.
"""

import asyncio
import logging
import os
import sys

# Must set APP_ENV before importing app modules so config loads correctly.
if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "local"

from app.rag.ingestion.chunker import chunk_markdown
from app.rag.ingestion.loader import load_docs
from app.rag.embedder import embed
from app.rag.store import get_collection, record_ingestion

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
log = logging.getLogger(__name__)


async def run() -> None:
    log.info("Loading documents...")
    docs = load_docs()
    log.info("Loaded %d document(s)", len(docs))

    all_chunks: list[dict] = []
    for doc in docs:
        chunks = chunk_markdown(doc["content"], doc["path"])
        log.info("  %s → %d chunks", doc["path"], len(chunks))
        all_chunks.extend(chunks)

    if not all_chunks:
        log.warning("No chunks produced — nothing to ingest.")
        return

    log.info("Total chunks: %d", len(all_chunks))

    log.info("Embedding %d chunks...", len(all_chunks))
    texts = [c["text"] for c in all_chunks]
    embeddings = await embed(texts)
    log.info("Embeddings done (%d vectors, dim=%d)", len(embeddings), len(embeddings[0]) if embeddings else 0)

    log.info("Upserting into ChromaDB...")
    collection = get_collection()
    collection.upsert(
        ids=[c["id"] for c in all_chunks],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "source_file":    c["source_file"],
                "section_title":  c["section_title"],
                "table_name":     c["table_name"],
                "chunk_index":    c["chunk_index"],
            }
            for c in all_chunks
        ],
    )
    log.info("Upserted %d chunks into collection '%s'", len(all_chunks), collection.name)

    record_ingestion()
    log.info("Ingestion complete. Run the API server to query the knowledge base.")


if __name__ == "__main__":
    asyncio.run(run())
