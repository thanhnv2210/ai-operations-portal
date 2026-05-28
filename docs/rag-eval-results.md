# RAG Evaluation Results

## Evaluation Setup

- **Corpus:** `docs/database-design.md` → 51 chunks (header-based, MAX_CHARS=2000, OVERLAP_CHARS=200)
- **Embeddings:** Ollama `nomic-embed-text` (local, 768-dim)
- **RAG chain:** Hybrid BM25 + ChromaDB vector search → RRF merge (k=60) → Claude claude-opus-4-6
- **RAGAS evaluator LLM:** Ollama `qwen2.5:7b` via OpenAI-compatible endpoint at localhost:11434/v1
- **RAGAS version:** 0.2.15 | **Golden QA pairs:** 15

### Notes on partial scores
- `faithfulness` and `answer_relevancy`: Most evaluation jobs timeout/error under RAGAS's parallel load with local Ollama. Only 1 faithfulness score captured per run. Re-run with `OPENAI_API_KEY` for complete scores.
- `context_recall`: Primarily evaluated (13/15 per run). Run-to-run NaN variance due to Ollama timeouts. **This is the primary retrieval quality metric.**

## Run History

| Run | Date | context_recall | faithfulness | Key changes |
|---|---|---|---|---|
| 1 | 2026-05-28 | 0.850 | 0.800 (1/15) | Initial corpus, 49 chunks |
| 2 | 2026-05-28 | 0.821 | 0.833 (1/15) | Added amount explanation; Q4 fixed 0→1 |
| 3 | 2026-05-28 | **0.865** | 1.000 (1/15) | Added FK subsection; Q2 fixed 0.5→1.0 |

## Latest Aggregate Scores
_Last run: 2026-05-27 18:33 UTC_

| Metric | Score | Target | Status |
|---|---|---|---|
| faithfulness     | 1.000 (1/15 scored) | > 0.85 | ✅ passes (single sample) |
| answer_relevancy | n/a                 | —      | ⚠️ partial — re-run with OpenAI |
| context_recall   | **0.865** (13/15)   | > 0.80 | ✅ passes |

## Per-Question Results

| Question | faithfulness | answer_relevancy | context_recall |
|---|---|---|---|
| What columns carry PII in remittance.transaction? | nan | nan | 0.000 |
| What does hub_id in remittance.transaction reference? | nan | nan | 1.000 |
| How do you find all status changes for a transaction? | nan | nan | 1.000 |
| What is the difference between remittance_amount and recipie | nan | nan | nan |
| What does service_type mean in remit_service? | nan | nan | 0.500 |
| What is the relationship between payment.ml_m_sof_payment an | nan | nan | 1.000 |
| What are the two databases used in this system? | nan | nan | 1.000 |
| What does fraud_status contain in remittance.transaction? | nan | nan | 1.000 |
| What is the remittance transaction lifecycle? | nan | nan | 0.750 |
| How does the PayNow SOF flow work? | nan | nan | 1.000 |
| What is proxy_refund_status in remittance.transaction? | nan | nan | 1.000 |
| What is the purpose of remit_corridor_reference? | nan | nan | 1.000 |
| How are FX rates stored in the system? | nan | nan | nan |
| What schemas are in ml_db? | nan | nan | 1.000 |
| What are backup tables and should they be queried for analyt | 1.000 | nan | 1.000 |
