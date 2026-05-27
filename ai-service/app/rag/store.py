"""ChromaDB vector store singleton.

Persists to ./rag_data/ (relative to the working directory where uvicorn runs).
Run from ai-service/ so the path resolves to ai-service/rag_data/.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import chromadb
from chromadb.api import ClientAPI

log = logging.getLogger(__name__)

_COLLECTION_NAME = "ai_ops_portal_docs"
_DATA_DIR = Path("./rag_data")
_META_FILE = _DATA_DIR / "meta.json"

_client: ClientAPI | None = None
_collection: chromadb.Collection | None = None


def get_client() -> ClientAPI:
    global _client
    if _client is None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_DATA_DIR))
        log.info("ChromaDB client initialised at %s", _DATA_DIR.resolve())
    return _client


def get_collection() -> chromadb.Collection:
    global _collection
    if _collection is None:
        _collection = get_client().get_or_create_collection(
            _COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def record_ingestion() -> None:
    """Write last_ingested_at timestamp to meta.json after a successful ingest run."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"last_ingested_at": datetime.now(timezone.utc).isoformat()}
    _META_FILE.write_text(json.dumps(meta))


def get_status() -> dict:
    """Return collection stats for the /api/v1/rag/status endpoint."""
    col = get_collection()
    doc_count = col.count()

    last_ingested_at = None
    if _META_FILE.exists():
        try:
            last_ingested_at = json.loads(_META_FILE.read_text()).get("last_ingested_at")
        except Exception:
            pass

    return {
        "collection_name": _COLLECTION_NAME,
        "doc_count": doc_count,
        "last_ingested_at": last_ingested_at,
    }
