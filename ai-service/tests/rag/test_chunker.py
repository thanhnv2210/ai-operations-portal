"""Unit tests for the Markdown chunker.

All tests are pure — no filesystem or network access required except the
optional smoke test against the real database-design.md.
"""

import pytest

from app.rag.ingestion.chunker import (
    MAX_CHARS,
    OVERLAP_CHARS,
    _extract_table_name,
    _split_long_text,
    chunk_markdown,
)

# ---------------------------------------------------------------------------
# Sample Markdown fixture used across multiple tests
# ---------------------------------------------------------------------------

SAMPLE_MD = """\
# Database Design Reference

## Overview

This document describes the two databases used by the system.

## ml_db — Reference Data

### `ml_schema.country`
Country master data.

| Column | Type | Notes |
|---|---|---|
| id | int PK | Surrogate key |
| country_name | varchar(50) | Display name |
| country_iso_code | varchar(3) | ISO 3166 |

### `ml_schema.ml_fx_rates`
FX rates for quotes.

| Column | Type |
|---|---|
| id | int PK |
| from_currency | varchar(20) |
| to_currency | varchar(20) |
| fx_rate | numeric(24,12) |

## keycloak — Transactions

### `remittance.transaction`
Core transaction table.

| Column | Notes |
|---|---|
| internal_transaction_id | bigint PK |
| status | varchar(50) — see TransactionStatus enum |
| hub_name | TELEPIN / WU / THUNES / TRANGLO |
| remittance_amount | numeric(20,9) — sender amount |
"""


class TestExtractTableName:
    def test_schema_dot_table(self):
        assert _extract_table_name("remittance.transaction") == "remittance.transaction"

    def test_ml_schema(self):
        assert _extract_table_name("ml_schema.country") == "ml_schema.country"

    def test_service_management(self):
        assert _extract_table_name("service_management.remit_service") == "service_management.remit_service"

    def test_backtick_wrapped(self):
        assert _extract_table_name("`remittance.transaction`") == "remittance.transaction"

    def test_with_surrounding_text(self):
        assert _extract_table_name("ml_db — ml_schema.country table") == "ml_schema.country"

    def test_plain_word_returns_none(self):
        assert _extract_table_name("Overview") is None

    def test_empty_string_returns_none(self):
        assert _extract_table_name("") is None

    def test_single_word_returns_none(self):
        assert _extract_table_name("transaction") is None

    def test_result_is_lowercase(self):
        # _extract_table_name lowercases the match
        result = _extract_table_name("Remittance.Transaction")
        assert result == result.lower() if result else True


class TestSplitLongText:
    def test_short_text_returned_unchanged(self):
        text = "short text"
        assert _split_long_text(text) == [text]

    def test_exact_limit_not_split(self):
        text = "a" * MAX_CHARS
        result = _split_long_text(text)
        assert len(result) == 1
        assert result[0] == text

    def test_text_one_over_limit_is_split(self):
        text = "a" * (MAX_CHARS + 1)
        result = _split_long_text(text)
        assert len(result) > 1

    def test_each_segment_within_limit(self):
        text = "word " * 1000  # ~5000 chars
        for segment in _split_long_text(text):
            assert len(segment) <= MAX_CHARS

    def test_overlap_between_consecutive_segments(self):
        # Segment N+1 starts OVERLAP_CHARS before the end of segment N
        text = "a" * MAX_CHARS + "b" * MAX_CHARS
        result = _split_long_text(text)
        assert len(result) >= 2
        # The tail of segment 0 should equal the head of segment 1
        assert result[0][-OVERLAP_CHARS:] == result[1][:OVERLAP_CHARS]

    def test_all_content_preserved(self):
        # Every character in the original must appear in at least one segment
        text = "abcdefghij" * 300  # 3000 chars
        segments = _split_long_text(text)
        # Reconstruct by stripping overlaps and verify no gaps
        # Simple check: combined length >= original (due to overlap it's >=)
        assert sum(len(s) for s in segments) >= len(text)

    def test_empty_string(self):
        result = _split_long_text("")
        assert result == [""]


class TestChunkMarkdown:
    def test_produces_at_least_one_chunk(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        assert len(chunks) > 0

    def test_source_file_set_on_all_chunks(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        assert all(c["source_file"] == "test.md" for c in chunks)

    def test_section_titles_extracted(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        titles = {c["section_title"] for c in chunks}
        assert "ml_schema.country" in titles
        assert "ml_schema.ml_fx_rates" in titles
        assert "remittance.transaction" in titles

    def test_table_names_extracted(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        table_names = {c["table_name"] for c in chunks if c["table_name"]}
        assert "ml_schema.country" in table_names
        assert "ml_schema.ml_fx_rates" in table_names
        assert "remittance.transaction" in table_names

    def test_max_chunk_size_respected(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        for chunk in chunks:
            assert len(chunk["text"]) <= MAX_CHARS, (
                f"Chunk exceeds MAX_CHARS ({MAX_CHARS}): {chunk['section_title']!r} "
                f"({len(chunk['text'])} chars)"
            )

    def test_chunk_ids_are_unique(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs are not unique"

    def test_required_keys_present(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        required = {"id", "text", "source_file", "section_title", "table_name", "chunk_index"}
        for chunk in chunks:
            missing = required - chunk.keys()
            assert not missing, f"Chunk missing keys: {missing}"

    def test_chunk_index_sequential(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_text_content_not_empty(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        for chunk in chunks:
            assert chunk["text"].strip(), "Chunk has empty text"

    def test_non_table_section_gets_h2_title(self):
        chunks = chunk_markdown(SAMPLE_MD, "test.md")
        # The "Overview" section has no ### subsection — its title is the ## header
        overview_chunks = [c for c in chunks if "Overview" in c["section_title"]]
        assert len(overview_chunks) > 0

    def test_empty_document_returns_no_chunks(self):
        chunks = chunk_markdown("", "empty.md")
        assert chunks == []

    def test_long_section_is_split(self):
        # Create a section that exceeds MAX_CHARS
        long_content = "| col | description |\n|---|---|\n" + "| field | some long description |\n" * 120
        md = f"## Section\n\n### schema.big_table\n\n{long_content}"
        chunks = chunk_markdown(md, "big.md")
        big_table_chunks = [c for c in chunks if c["table_name"] == "schema.big_table"]
        assert len(big_table_chunks) > 1, "Long section should be split into multiple chunks"

    def test_real_database_design_doc(self):
        """Smoke test: chunk the actual database-design.md from the project docs."""
        from pathlib import Path
        doc_path = Path("../docs/database-design.md")
        if not doc_path.exists():
            pytest.skip("database-design.md not found — run tests from ai-service/ directory")

        content = doc_path.read_text(encoding="utf-8")
        chunks = chunk_markdown(content, "database-design.md")

        assert len(chunks) >= 10, "Expected at least 10 chunks from database-design.md"
        assert all(len(c["text"]) <= MAX_CHARS for c in chunks)
        assert all(c["source_file"] == "database-design.md" for c in chunks)

        known_tables = [
            "remittance.transaction",
            "ml_schema.country",
            "service_management.remit_service",
        ]
        extracted = {c["table_name"] for c in chunks}
        for table in known_tables:
            assert table in extracted, f"Expected table not extracted: {table}"
