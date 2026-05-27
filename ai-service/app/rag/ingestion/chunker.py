"""Markdown chunker for RAG ingestion.

Strategy:
  - Split on ## (H2) and ### (H3) Markdown headers.
  - Each ### section becomes a base chunk (one table = one chunk).
  - ## sections with no ### subsections are kept as their own chunk.
  - Chunks exceeding MAX_CHARS are split into sub-chunks with OVERLAP_CHARS overlap.
  - Metadata per chunk: source_file, section_title, table_name (if header matches schema.table pattern).

Token estimation: 1 token ≈ 4 chars (no tiktoken dependency required).
Target: 500 tokens ≈ 2000 chars.  Overlap: 50 tokens ≈ 200 chars.
"""

import re
import uuid

MAX_CHARS = 2000
OVERLAP_CHARS = 200

# Matches `schema.table` or `schema.table` patterns in section titles.
_TABLE_RE = re.compile(r"`?([a-z_]+\.[a-z_]+)`?", re.IGNORECASE)


def _extract_table_name(title: str) -> str | None:
    """Extract schema.table from a section title if present."""
    m = _TABLE_RE.search(title)
    return m.group(1).lower() if m else None


def _split_long_text(text: str) -> list[str]:
    """Split text into segments of at most MAX_CHARS with OVERLAP_CHARS overlap."""
    if len(text) <= MAX_CHARS:
        return [text]

    segments: list[str] = []
    start = 0
    while start < len(text):
        end = start + MAX_CHARS
        segments.append(text[start:end])
        if end >= len(text):
            break
        start = end - OVERLAP_CHARS  # step back for overlap
    return segments


def _make_chunk(
    text: str,
    source_file: str,
    section_title: str,
    chunk_index: int,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "source_file": source_file,
        "section_title": section_title,
        "table_name": _extract_table_name(section_title) or "",
        "chunk_index": chunk_index,
    }


def chunk_markdown(content: str, source_file: str) -> list[dict]:
    """Parse Markdown content into chunks with metadata.

    Returns a list of chunk dicts:
      { id, text, source_file, section_title, table_name, chunk_index }
    """
    chunks: list[dict] = []
    chunk_index = 0

    current_h2 = ""
    current_h3 = ""
    buffer: list[str] = []

    def flush(h2: str, h3: str, buf: list[str]) -> None:
        nonlocal chunk_index
        text = "\n".join(buf).strip()
        if not text:
            return
        title = f"{h3}" if h3 else h2
        for segment in _split_long_text(text):
            if segment.strip():
                chunks.append(_make_chunk(segment.strip(), source_file, title, chunk_index))
                chunk_index += 1

    lines = content.split("\n")
    for line in lines:
        if line.startswith("### "):
            flush(current_h2, current_h3, buffer)
            current_h3 = line[4:].strip().lstrip("`").rstrip("`")
            buffer = [line]
        elif line.startswith("## "):
            flush(current_h2, current_h3, buffer)
            current_h2 = line[3:].strip()
            current_h3 = ""
            buffer = [line]
        else:
            buffer.append(line)

    flush(current_h2, current_h3, buffer)
    return chunks
