# RAG Evaluation Results
_Last run: 2026-05-27 18:06 UTC_

## Evaluation Setup

- **Corpus:** `docs/database-design.md` → 49 chunks (header-based, MAX_CHARS=2000, OVERLAP_CHARS=200)
- **Embeddings:** Ollama `nomic-embed-text` (local, 768-dim)
- **RAG chain:** Hybrid BM25 + ChromaDB vector search → RRF merge → Claude claude-opus-4-6
- **RAGAS evaluator LLM:** Ollama `qwen2.5:7b` via OpenAI-compatible endpoint
- **RAGAS version:** 0.2.15 | **Golden QA pairs:** 15

### Notes on partial scores
- `faithfulness` and `answer_relevancy`: Most jobs timed out or errored with local Ollama (qwen2.5:7b is slow for RAGAS NLI / embedding tasks). Only 1 faithfulness score was captured. Re-run with `OPENAI_API_KEY` set for complete faithfulness/relevancy scores.
- `context_recall`: Fully evaluated — this metric depends on LLM judgment on chunk relevance and completed for all 15 questions. **This is the most meaningful metric for retrieval quality.**

## Aggregate Scores

| Metric | Score | Target | Status |
|---|---|---|---|
| faithfulness     | 0.800 (1/15 scored) | > 0.85 | ⚠️ partial — re-run with OpenAI |
| answer_relevancy | n/a                 | —      | ⚠️ partial — re-run with OpenAI |
| context_recall   | **0.850** (15/15)   | > 0.80 | ✅ passes |

## Per-Question Results

| Question | faithfulness | answer_relevancy | context_recall |
|---|---|---|---|
| What columns carry PII in remittance.transaction? | nan | nan | 1.000 |
| What does hub_id in remittance.transaction reference? | nan | nan | 0.500 |
| How do you find all status changes for a transaction? | nan | nan | 1.000 |
| What is the difference between remittance_amount and recipie | nan | nan | 0.000 |
| What does service_type mean in remit_service? | nan | nan | 0.500 |
| What is the relationship between payment.ml_m_sof_payment an | nan | nan | 1.000 |
| What are the two databases used in this system? | nan | nan | 1.000 |
| What does fraud_status contain in remittance.transaction? | nan | nan | 1.000 |
| What is the remittance transaction lifecycle? | nan | nan | 0.750 |
| How does the PayNow SOF flow work? | nan | nan | 1.000 |
| What is proxy_refund_status in remittance.transaction? | nan | nan | 1.000 |
| What is the purpose of remit_corridor_reference? | nan | nan | 1.000 |
| How are FX rates stored in the system? | nan | nan | 1.000 |
| What schemas are in ml_db? | nan | nan | 1.000 |
| What are backup tables and should they be queried for analyt | 0.800 | nan | 1.000 |
