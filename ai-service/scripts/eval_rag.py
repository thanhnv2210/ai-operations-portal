"""RAG evaluation script using RAGAS.

Measures retrieval and answer quality against a golden Q&A dataset.

Prerequisites:
    pip install -r requirements-eval.txt
    python -m app.rag.ingest              # ingest docs first
    export ANTHROPIC_API_KEY=...          # or OPENAI_API_KEY for RAGAS evaluator

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


async def collect_results(qa_pairs: list[dict]) -> list[dict]:
    """Run the RAG chain on every question and collect answers + contexts."""
    from app.rag.chain import query as rag_query

    rows = []
    for i, item in enumerate(qa_pairs, 1):
        question = item["question"]
        ground_truth = item["ground_truth"]
        print(f"  [{i}/{len(qa_pairs)}] {question[:70]}...")

        result = await rag_query(question)
        contexts = [s["chunk_text"] for s in result["sources"]]
        rows.append({
            "question":     question,
            "answer":       result["answer"],
            "contexts":     contexts,
            "ground_truth": ground_truth,
        })
    return rows


def run_ragas(rows: list[dict]) -> None:
    """Evaluate collected results with RAGAS and print a summary."""
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import answer_relevancy, context_recall, faithfulness

    dataset = Dataset.from_list(rows)
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_recall],
    )

    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)
    df = result.to_pandas()
    print(df[["question", "faithfulness", "answer_relevancy", "context_recall"]].to_string(index=False))

    print("\nAGGREGATE SCORES:")
    print(f"  faithfulness    : {df['faithfulness'].mean():.3f}  (target > 0.85)")
    print(f"  answer_relevancy: {df['answer_relevancy'].mean():.3f}")
    print(f"  context_recall  : {df['context_recall'].mean():.3f}  (target > 0.80)")
    print("=" * 60)

    # Write results to docs/rag-eval-results.md
    results_path = Path("../docs/rag-eval-results.md")
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# RAG Evaluation Results\n",
        f"_Last run: {timestamp}_\n\n",
        "## Aggregate Scores\n\n",
        "| Metric | Score | Target |\n",
        "|---|---|---|\n",
        f"| faithfulness    | {df['faithfulness'].mean():.3f}    | > 0.85 |\n",
        f"| answer_relevancy | {df['answer_relevancy'].mean():.3f} | — |\n",
        f"| context_recall  | {df['context_recall'].mean():.3f}   | > 0.80 |\n\n",
        "## Per-Question Results\n\n",
        "| Question | faithfulness | answer_relevancy | context_recall |\n",
        "|---|---|---|---|\n",
    ]
    for _, row in df.iterrows():
        q = row["question"][:60].replace("|", "\\|")
        lines.append(
            f"| {q} | {row['faithfulness']:.3f} | {row['answer_relevancy']:.3f} | {row['context_recall']:.3f} |\n"
        )
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
