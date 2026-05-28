"""Shim: allows the short form `python -m app.rag.ingest` as an alias for
`python -m app.rag.ingestion.ingest`.

Usage (from ai-service/ directory):
    python -m app.rag.ingest
"""

import asyncio

from app.rag.ingestion.ingest import run

if __name__ == "__main__":
    asyncio.run(run())
