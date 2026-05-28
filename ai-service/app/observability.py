"""Langfuse observability — optional LLM tracing.

Usage
-----
    from app.observability import get_tracer

    tracer = get_tracer()
    with tracer.trace("pipeline_name", input={"question": q}) as t:
        with t.span("step_name") as s:
            ...
            s.set_output({"result": value})
        t.set_output({"answer": answer})

When LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are not set, all calls
are no-ops — the application runs normally without any tracing overhead.

Self-hosted Langfuse
--------------------
    docker run -p 3000:3000 langfuse/langfuse   # or use docker-compose
    LANGFUSE_HOST=http://localhost:3000
    LANGFUSE_PUBLIC_KEY=...
    LANGFUSE_SECRET_KEY=...

Cloud (langfuse.com)
--------------------
    LANGFUSE_HOST=https://cloud.langfuse.com  (default — can be omitted)
    LANGFUSE_PUBLIC_KEY=pk-lf-...
    LANGFUSE_SECRET_KEY=sk-lf-...
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Generator

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# No-op stubs — used when Langfuse is not configured
# ---------------------------------------------------------------------------

class _NoopSpan:
    def set_output(self, output: Any) -> None:  # noqa: ANN401
        pass

    def end(self, **kwargs: Any) -> None:
        pass


class _NoopTrace:
    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Generator[_NoopSpan, None, None]:
        yield _NoopSpan()

    def set_output(self, output: Any) -> None:  # noqa: ANN401
        pass

    def update(self, **kwargs: Any) -> None:
        pass


class _NoopTracer:
    @contextmanager
    def trace(self, name: str, **kwargs: Any) -> Generator[_NoopTrace, None, None]:
        yield _NoopTrace()

    def flush(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Real Langfuse wrappers
# ---------------------------------------------------------------------------

class _LangfuseSpan:
    def __init__(self, span: Any) -> None:
        self._span = span

    def set_output(self, output: Any) -> None:  # noqa: ANN401
        self._span.end(output=output)

    def end(self, **kwargs: Any) -> None:
        self._span.end(**kwargs)


class _LangfuseTrace:
    def __init__(self, trace: Any) -> None:
        self._trace = trace

    @contextmanager
    def span(self, name: str, **kwargs: Any) -> Generator[_LangfuseSpan, None, None]:
        s = self._trace.span(name=name, **kwargs)
        wrapped = _LangfuseSpan(s)
        try:
            yield wrapped
        except Exception:
            s.end(level="ERROR")
            raise
        # span.end() is called via set_output() or explicitly; safe to call again
        try:
            s.end()
        except Exception:
            pass

    def set_output(self, output: Any) -> None:  # noqa: ANN401
        self._trace.update(output=output)

    def update(self, **kwargs: Any) -> None:
        self._trace.update(**kwargs)


class _LangfuseTracer:
    def __init__(self, client: Any) -> None:
        self._client = client

    @contextmanager
    def trace(self, name: str, **kwargs: Any) -> Generator[_LangfuseTrace, None, None]:
        t = self._client.trace(name=name, **kwargs)
        wrapped = _LangfuseTrace(t)
        try:
            yield wrapped
        except Exception:
            t.update(level="ERROR")
            raise

    def flush(self) -> None:
        self._client.flush()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_tracer() -> _LangfuseTracer | _NoopTracer:
    """Return a Langfuse tracer if credentials are configured, else a no-op."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")

    if not public_key or not secret_key:
        log.info(
            "Langfuse not configured (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY not set). "
            "Tracing disabled — all pipeline calls are no-ops."
        )
        return _NoopTracer()

    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    try:
        from langfuse import Langfuse  # type: ignore[import-untyped]
        client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
        log.info("Langfuse tracing enabled → %s", host)
        return _LangfuseTracer(client)
    except Exception as exc:
        log.warning("Failed to initialise Langfuse (%s). Tracing disabled.", exc)
        return _NoopTracer()
