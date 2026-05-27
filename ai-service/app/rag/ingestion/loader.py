"""Document loader for RAG ingestion.

Loads Markdown files from the docs/ directory relative to the project root.
New documents can be added to _DOC_PATHS as the corpus grows.
"""

from pathlib import Path

# Paths relative to the ai-service/ working directory (where uvicorn / CLI runs from).
_DOC_PATHS: list[Path] = [
    Path("../docs/database-design.md"),
]


def load_docs() -> list[dict]:
    """Load all configured documents. Returns list of {path, content} dicts."""
    docs: list[dict] = []
    for path in _DOC_PATHS:
        resolved = path.resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Document not found: {resolved}")
        docs.append({"path": path.name, "content": resolved.read_text(encoding="utf-8")})
    return docs
