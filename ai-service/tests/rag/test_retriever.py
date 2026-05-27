"""Unit tests for the RAG retriever.

Tests cover:
  - _rrf_merge: Reciprocal Rank Fusion merging logic
  - rebuild_bm25 + _bm25_search: in-memory BM25 index behaviour
  - _tokenize: text tokenisation

No ChromaDB or network access — vector search is not tested here
(it requires an embedded model and populated store).
"""

import pytest

from app.rag.retriever import (
    _FINAL_TOP_K,
    _RRF_K,
    _bm25_search,
    _rrf_merge,
    _tokenize,
    rebuild_bm25,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_chunk(chunk_id: str, text: str = "", vector_score: float = 0.8) -> dict:
    return {
        "id": chunk_id,
        "text": text or f"content for chunk {chunk_id}",
        "source_file": "test.md",
        "section_title": chunk_id,
        "table_name": "",
        "vector_score": vector_score,
    }


# ---------------------------------------------------------------------------
# _tokenize
# ---------------------------------------------------------------------------

class TestTokenize:
    def test_lowercases(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_splits_on_whitespace(self):
        assert _tokenize("a b c") == ["a", "b", "c"]

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_single_word(self):
        assert _tokenize("transaction") == ["transaction"]

    def test_multiple_spaces(self):
        assert _tokenize("a  b") == ["a", "b"]


# ---------------------------------------------------------------------------
# _rrf_merge
# ---------------------------------------------------------------------------

class TestRrfMerge:
    def test_combines_results_from_both_lists(self):
        vector = [make_chunk("a"), make_chunk("b")]
        bm25 = [make_chunk("c"), make_chunk("d")]
        result = _rrf_merge(vector, bm25)
        ids = {r["id"] for r in result}
        assert {"a", "b", "c", "d"} == ids

    def test_deduplicates_chunk_appearing_in_both_lists(self):
        vector = [make_chunk("a"), make_chunk("b")]
        bm25 = [make_chunk("a"), make_chunk("c")]
        result = _rrf_merge(vector, bm25)
        ids = [r["id"] for r in result]
        assert ids.count("a") == 1

    def test_chunk_in_both_lists_scores_higher(self):
        # "shared" appears rank-1 in both lists → highest RRF score
        vector = [make_chunk("shared"), make_chunk("v_only")]
        bm25 = [make_chunk("shared"), make_chunk("b_only")]
        result = _rrf_merge(vector, bm25)
        assert result[0]["id"] == "shared"

    def test_top_ranked_item_comes_first(self):
        # "a" is rank 1 in vector, rank 2 in bm25
        # "b" is rank 2 in vector, rank 1 in bm25
        # "a" and "b" have similar scores but "a" is slightly better overall
        # We only assert the merge produces something sensible
        vector = [make_chunk("a"), make_chunk("b"), make_chunk("c")]
        bm25 = [make_chunk("b"), make_chunk("a"), make_chunk("c")]
        result = _rrf_merge(vector, bm25)
        assert result[0]["id"] in {"a", "b"}  # either could be first depending on exact scores

    def test_respects_final_top_k(self):
        vector = [make_chunk(f"v{i}") for i in range(8)]
        bm25 = [make_chunk(f"b{i}") for i in range(8)]
        result = _rrf_merge(vector, bm25)
        assert len(result) <= _FINAL_TOP_K

    def test_rrf_score_added_to_each_result(self):
        vector = [make_chunk("a"), make_chunk("b")]
        bm25 = [make_chunk("c")]
        result = _rrf_merge(vector, bm25)
        for r in result:
            assert "rrf_score" in r
            assert r["rrf_score"] > 0

    def test_rrf_score_is_positive(self):
        vector = [make_chunk("a")]
        bm25 = [make_chunk("b")]
        result = _rrf_merge(vector, bm25)
        assert all(r["rrf_score"] > 0 for r in result)

    def test_both_empty_returns_empty(self):
        assert _rrf_merge([], []) == []

    def test_only_vector_results(self):
        vector = [make_chunk("a"), make_chunk("b")]
        result = _rrf_merge(vector, [])
        assert len(result) == 2
        assert {r["id"] for r in result} == {"a", "b"}

    def test_only_bm25_results(self):
        bm25 = [make_chunk("x"), make_chunk("y")]
        result = _rrf_merge([], bm25)
        assert {r["id"] for r in result} == {"x", "y"}

    def test_rrf_formula_correctness(self):
        # Item at rank 0 in a single list: score = 1 / (0 + 1 + k) = 1 / (k + 1)
        vector = [make_chunk("only")]
        result = _rrf_merge(vector, [])
        expected_score = 1.0 / (1 + _RRF_K)
        assert abs(result[0]["rrf_score"] - round(expected_score, 6)) < 1e-6


# ---------------------------------------------------------------------------
# rebuild_bm25 + _bm25_search
# ---------------------------------------------------------------------------

class TestBm25:
    CHUNKS = [
        {
            "id": "tx",
            "text": "remittance transaction status lifecycle payment failed error_code hub_name",
            "source_file": "db.md",
            "section_title": "remittance.transaction",
            "table_name": "remittance.transaction",
        },
        {
            "id": "country",
            "text": "country reference data ISO code currency sending receiving",
            "source_file": "db.md",
            "section_title": "ml_schema.country",
            "table_name": "ml_schema.country",
        },
        {
            "id": "fx",
            "text": "FX rates exchange currency from_currency to_currency retail rate",
            "source_file": "db.md",
            "section_title": "ml_schema.ml_fx_rates",
            "table_name": "ml_schema.ml_fx_rates",
        },
        {
            "id": "pii",
            "text": "PII columns sender_msisdn recipient_fullname sender_dob masked logs never",
            "source_file": "db.md",
            "section_title": "PII Reference",
            "table_name": "",
        },
    ]

    def setup_method(self):
        rebuild_bm25(self.CHUNKS)

    def test_returns_results_for_matching_query(self):
        results = _bm25_search("transaction status")
        assert len(results) > 0

    def test_most_relevant_chunk_ranks_first(self):
        results = _bm25_search("transaction payment status")
        assert results[0]["id"] == "tx"

    def test_fx_query_retrieves_fx_chunk(self):
        results = _bm25_search("exchange rate from_currency")
        assert results[0]["id"] == "fx"

    def test_pii_query_retrieves_pii_chunk(self):
        results = _bm25_search("sender_msisdn PII masked")
        assert results[0]["id"] == "pii"

    def test_country_query_retrieves_country_chunk(self):
        results = _bm25_search("country ISO currency")
        assert results[0]["id"] == "country"

    def test_results_respect_top_n_limit(self):
        results = _bm25_search("the")
        assert len(results) <= 8  # _BM25_TOP_N

    def test_zero_score_results_excluded(self):
        # A query with no matching terms should return no results
        results = _bm25_search("xyzzy_nonexistent_term_12345")
        for r in results:
            assert r.get("bm25_score", 0) > 0

    def test_results_contain_required_fields(self):
        results = _bm25_search("transaction")
        for r in results:
            assert "id" in r
            assert "text" in r
            assert "bm25_score" in r

    def test_empty_index_returns_no_results(self):
        rebuild_bm25([])
        results = _bm25_search("transaction payment status")
        assert results == []

    def test_rebuild_replaces_previous_index(self):
        # Build with finance chunks, then rebuild with geography chunks
        rebuild_bm25(self.CHUNKS)
        results_before = _bm25_search("transaction payment")
        assert len(results_before) > 0

        geo_chunks = [
            {"id": "geo1", "text": "Singapore latitude longitude city state",
             "source_file": "geo.md", "section_title": "Geography", "table_name": ""},
        ]
        rebuild_bm25(geo_chunks)
        results_after = _bm25_search("transaction payment")
        # After rebuild, finance-related query should find nothing in geography corpus
        assert all(r.get("bm25_score", 0) == 0 or r["id"] not in {"tx", "pii", "fx", "country"}
                   for r in results_after)

    def test_small_corpus_top_match(self):
        # BM25 Okapi IDF requires ≥3 docs for positive score when df=1
        # (with 2 docs, idf = log(1.5) - log(1.5) = 0, filtered out)
        rebuild_bm25([
            {"id": "target", "text": "remittance transaction lifecycle payment error_code",
             "source_file": "f.md", "section_title": "Target", "table_name": ""},
            {"id": "other1", "text": "geography country city latitude longitude",
             "source_file": "f.md", "section_title": "Other1", "table_name": ""},
            {"id": "other2", "text": "customer beneficiary recipient service",
             "source_file": "f.md", "section_title": "Other2", "table_name": ""},
        ])
        results = _bm25_search("remittance transaction")
        assert len(results) >= 1
        assert results[0]["id"] == "target"
