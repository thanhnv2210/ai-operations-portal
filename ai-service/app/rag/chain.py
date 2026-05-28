"""RAG chain.

Pipeline:
  1. Embed the user question.
  2. Hybrid retrieval → top-6 chunks (BM25 + vector + RRF).
  3. Grounding guard — if best vector similarity < threshold, return early.
  4. Build augmented prompt with numbered context blocks.
  5. Claude answers grounded in the retrieved context, citing block numbers.
  6. Return {answer, sources}.

This is a non-streaming chain — the full answer is returned at once.
"""

import logging

from app.llm import complete
from app.observability import get_tracer
from app.rag.embedder import embed
from app.rag.retriever import SIMILARITY_THRESHOLD, retrieve

log = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
You are a technical assistant for an AI operations portal.
Answer questions about the system's database schema and architecture
using ONLY the numbered context blocks provided.

Rules:
- Cite context block numbers inline, e.g. [1], [2], when you use information from them.
- If the answer cannot be found in the context, say "The context does not contain enough information to answer this question."
- Never invent column names, table names, or relationships not present in the context.
- Do not include PII field values in your answer.
- Be concise and precise — this is a technical reference, not a conversation.
"""

_NO_CONTEXT_ANSWER = "Not enough relevant context found in the knowledge base to answer this question."


def _build_prompt(question: str, chunks: list[dict]) -> str:
    context_blocks = "\n\n".join(
        f"[{i + 1}] Section: {c['section_title']}\nSource: {c['source_file']}\n\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    return (
        f"Context:\n{context_blocks}\n\n"
        f"Question: {question}"
    )


async def query(question: str) -> dict:
    """Run the full RAG chain and return {answer, sources}.

    sources is a list of:
      {chunk_text, section_title, source_file, vector_score, rrf_score}
    """
    tracer = get_tracer()

    with tracer.trace(
        "rag_query",
        input={"question": question},
        metadata={"pipeline": "rag"},
    ) as trace:

        # Step 1: embed
        with trace.span("embed_question") as span:
            embeddings = await embed([question])
            question_embedding = embeddings[0]
            span.set_output({"embedding_dim": len(question_embedding)})

        # Step 2: retrieve
        with trace.span("hybrid_retrieve", input={"question": question}) as span:
            chunks, best_score = await retrieve(question, question_embedding)
            span.set_output({
                "chunk_count": len(chunks),
                "best_vector_score": round(best_score, 4),
                "sections": [c["section_title"] for c in chunks],
            })

        log.info(
            "RAG retrieve: question=%r chunks=%d best_vector_score=%.3f",
            question[:80],
            len(chunks),
            best_score,
        )

        # Step 3: grounding guard
        with trace.span("grounding_guard") as span:
            grounded = bool(chunks) and best_score >= SIMILARITY_THRESHOLD
            span.set_output({"grounded": grounded, "best_score": round(best_score, 4), "threshold": SIMILARITY_THRESHOLD})

        if not grounded:
            trace.set_output({"answer": _NO_CONTEXT_ANSWER, "grounded": False})
            return {"answer": _NO_CONTEXT_ANSWER, "sources": []}

        # Step 4 + 5: build prompt and call Claude
        prompt = _build_prompt(question, chunks)
        with trace.span("claude_answer", input={"chunk_count": len(chunks)}) as span:
            answer = await complete(
                messages=[{"role": "user", "content": prompt}],
                system=_SYSTEM_PROMPT,
                max_tokens=1024,
            )
            span.set_output({"answer_length": len(answer)})

        # Step 6: return answer + sources
        sources = [
            {
                "chunk_text":    c["text"],
                "section_title": c["section_title"],
                "source_file":   c["source_file"],
                "vector_score":  c.get("vector_score", 0.0),
                "rrf_score":     c.get("rrf_score", 0.0),
            }
            for c in chunks
        ]

        trace.set_output({
            "answer": answer.strip()[:200],
            "sources_count": len(sources),
            "best_vector_score": round(best_score, 4),
        })

        return {"answer": answer.strip(), "sources": sources}
