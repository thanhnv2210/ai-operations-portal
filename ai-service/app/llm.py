"""LLM client — Anthropic primary with Ollama fallback.

Usage:
    async for chunk in stream_response(messages):
        yield chunk

    text = await complete(messages)
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator

import anthropic
import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

# Lazy singleton
_anthropic_client: anthropic.AsyncAnthropic | None = None
_semaphore: asyncio.Semaphore | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        cfg = get_settings()
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=cfg.anthropic_api_key,
            timeout=httpx.Timeout(connect=30, read=600, write=30, pool=30),
        )
    return _anthropic_client


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        cfg = get_settings()
        _semaphore = asyncio.Semaphore(cfg.anthropic_concurrency)
    return _semaphore


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from Ollama responses."""
    return re.sub(r"^```[a-z]*\n?|```$", "", text.strip(), flags=re.MULTILINE).strip()


async def _ollama_complete(messages: list[dict], system: str) -> str:
    """Call Ollama's OpenAI-compatible endpoint as a fallback."""
    cfg = get_settings()
    payload = {
        "model": cfg.ollama_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{cfg.ollama_base_url}/v1/chat/completions", json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return _strip_fences(content)


async def _ollama_stream(messages: list[dict], system: str) -> AsyncGenerator[str, None]:
    """Stream from Ollama's OpenAI-compatible endpoint."""
    cfg = get_settings()
    payload = {
        "model": cfg.ollama_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream("POST", f"{cfg.ollama_base_url}/v1/chat/completions", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                data = line[6:]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        yield delta
                except (json.JSONDecodeError, KeyError):
                    continue


async def stream_response(
    messages: list[dict],
    system: str,
) -> AsyncGenerator[str, None]:
    """Stream text chunks. Falls back to Ollama on Anthropic failure."""
    cfg = get_settings()
    async with _get_semaphore():
        try:
            async with _get_client().messages.stream(
                model=cfg.anthropic_model,
                max_tokens=4096,
                system=system,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.BadRequestError as e:
            log.warning("Anthropic BadRequestError (%s), falling back to Ollama", e)
            async for chunk in _ollama_stream(messages, system):
                yield chunk
        except anthropic.AuthenticationError:
            log.warning("Anthropic auth failed, falling back to Ollama")
            async for chunk in _ollama_stream(messages, system):
                yield chunk


async def complete(
    messages: list[dict],
    system: str,
    max_tokens: int = 2048,
) -> str:
    """Non-streaming completion. Falls back to Ollama on Anthropic failure."""
    cfg = get_settings()
    async with _get_semaphore():
        try:
            resp = await _get_client().messages.create(
                model=cfg.anthropic_model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
            return "".join(
                block.text for block in resp.content if block.type == "text"
            )
        except (anthropic.BadRequestError, anthropic.AuthenticationError) as e:
            log.warning("Anthropic error (%s), falling back to Ollama", e)
            return await _ollama_complete(messages, system)
