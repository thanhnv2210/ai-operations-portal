"""RAG evaluation script using RAGAS.

Measures retrieval and answer quality against a golden Q&A dataset.

Prerequisites:
    pip install -r requirements-eval.txt
    python -m app.rag.ingestion.ingest     # ingest docs first
    ANTHROPIC_API_KEY must be set          # used both by RAG chain and RAGAS evaluator

LLM used for RAGAS evaluation:
    Uses Ollama (qwen2.5:7b) via the OpenAI-compatible API at localhost:11434/v1.
    Requires Ollama to be running locally with qwen2.5:7b pulled.
    Override with RAGAS_OLLAMA_MODEL env var.

Usage (from ai-service/ directory):
    python scripts/eval_rag.py

Metrics reported:
    faithfulness      — does the answer stay grounded in the retrieved context?
    answer_relevance  — is the answer relevant to the question asked?
    context_recall    — are the relevant facts present in the retrieved chunks?

Targets (per TODO-proposed.md):
    faithfulness   > 0.85
    context_recall > 0.80
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure ai-service/ is on sys.path when run as scripts/eval_rag.py
sys.path.insert(0, str(Path(__file__).parent.parent))

if "APP_ENV" not in os.environ:
    os.environ["APP_ENV"] = "local"


def _make_ragas_llm():
    """Build a RAGAS-compatible LLM using Ollama's OpenAI-compatible endpoint."""
    from langchain_openai import ChatOpenAI
    from ragas.llms.base import LangchainLLMWrapper

    model = os.environ.get("RAGAS_OLLAMA_MODEL", "qwen2.5:7b")
    lc_llm = ChatOpenAI(
        model=model,
        base_url="http://localhost:11434/v1",
        api_key="ollama",          # Ollama ignores the key but langchain requires it non-empty
        temperature=0,
    )
    return LangchainLLMWrapper(lc_llm)


def _make_ragas_embeddings():
    """Build a RAGAS-compatible embeddings using Ollama's OpenAI-compatible endpoint."""
    from langchain_openai import OpenAIEmbeddings
    from ragas.embeddings.base import LangchainEmbeddingsWrapper

    lc_emb = OpenAIEmbeddings(
        model="nomic-embed-text",
        base_url="http://localhost:11434/v1",
        api_key="ollama",
    )
    return LangchainEmbeddingsWrapper(lc_emb)


async def collect_results(qa_pairs: list[dict]) -> list[dict]:
    """Run the RAG chain on every question and collect answers + contexts."""
    # BM25 index is normally built in FastAPI lifespan — load it explicitly here.
    from app.rag.retriever import load_bm25_from_store
    load_bm25_from_store()

    from app.rag.chain import query as rag_query

    rows = []
    for i, item in enumerate(qa_pairs, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]
        print(f"  [{i}/{len(qa_pairs)}] {question[:70]}...")

        result = await rag_query(question)
        contexts = [s["chunk_text"] for s in result["sources"]]
        # RAGAS 0.2.x field names
        rows.append({
            "user_input":         question,
            "response":           result["answer"],
            "retrieved_contexts": contexts,
            "reference":          ground_truth,
        })
    return rows


def run_ragas(rows: list[dict]) -> None:
    """Evaluate collected results with RAGAS and print a summary."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_recall, faithfulness

    ragas_llm = _make_ragas_llm()
    ragas_emb = _make_ragas_embeddings()

    # Inject custom LLM + embeddings into each metric
    metrics = [faithfulness, answer_relevancy, context_recall]
    for m in metrics:
        m.llm = ragas_llm
        if hasattr(m, "embeddings"):
            m.embeddings = ragas_emb

    dataset = Dataset.from_list(rows)
    result = evaluate(
        dataset,
        metrics=metrics,
    )

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)
    df = result.to_pandas()

    # RAGAS 0.2.x uses user_input / response / retrieved_contexts / reference
    score_cols = [c for c in ["faithfulness", "answer_relevancy", "context_recall"] if c in df.columns]
    disp_cols = ["user_input"] + score_cols
    print(df[disp_cols].to_string(index=False))

    print("\nAGGREGATE SCORES:")
    faith  = df["faithfulness"].mean()    if "faithfulness"    in df.columns else float("nan")
    relev  = df["answer_relevancy"].mean() if "answer_relevancy" in df.columns else float("nan")
    recall = df["context_recall"].mean()  if "context_recall"  in df.columns else float("nan")
    print(f"  faithfulness    : {faith:.3f}   (target > 0.85)")
    print(f"  answer_relevancy: {relev:.3f}")
    print(f"  context_recall  : {recall:.3f}  (target > 0.80)")
    print("=" * 60)

    # Write results to docs/rag-eval-results.md
    results_path = Path("../docs/rag-eval-results.md")
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# RAG Evaluation Results\n",
        f"_Last run: {timestamp}_\n\n",
        "## Aggregate Scores\n\n",
        "| Metric | Score | Target |\n",
        "|---|---|---|\n",
        f"| faithfulness     | {faith:.3f}  | > 0.85 |\n",
        f"| answer_relevancy | {relev:.3f}  | — |\n",
        f"| context_recall   | {recall:.3f} | > 0.80 |\n\n",
        "## Per-Question Results\n\n",
        "| Question | faithfulness | answer_relevancy | context_recall |\n",
        "|---|---|---|---|\n",
    ]
    for _, row in df.iterrows():
        q = str(row.get("user_input", ""))[:60].replace("|", "\\|")
        f_val = f"{row['faithfulness']:.3f}"    if "faithfulness"    in df.columns else "n/a"
        r_val = f"{row['answer_relevancy']:.3f}" if "answer_relevancy" in df.columns else "n/a"
        c_val = f"{row['context_recall']:.3f}"  if "context_recall"  in df.columns else "n/a"
        lines.append(f"| {q} | {f_val} | {r_val} | {c_val} |\n")
    results_path.write_text("".join(lines))
    print(f"\nResults written to {results_path.resolve()}")


async def main() -> None:
    golden_path = Path("tests/rag/golden_qa.json")
    if not golden_path.exists():
        print(f"ERROR: golden Q&A file not found at {golden_path.resolve()}")
        sys.exit(1)

    qa_pairs = json.loads(golden_path.read_text())
    print(f"Loaded {len(qa_pairs)} Q&A pairs from {golden_path}")

    print("Running RAG chain on all questions...")
    rows = await collect_results(qa_pairs)

    print("Running RAGAS evaluation...")
    run_ragas(rows)


if __name__ == "__main__":
    asyncio.run(main())
