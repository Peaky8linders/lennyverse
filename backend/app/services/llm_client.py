"""LLM client for LennyVerse — Anthropic (prod) or Ollama (local dev fallback)."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from app.config import config

logger = logging.getLogger(__name__)

_anthropic_client = None
_ollama_client: httpx.AsyncClient | None = None


def _get_anthropic_client():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        _anthropic_client = anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key,
            timeout=httpx.Timeout(config.llm_timeout, connect=10.0),
        )
    return _anthropic_client


def _get_ollama_client() -> httpx.AsyncClient:
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = httpx.AsyncClient(
            base_url=config.ollama_url,
            timeout=httpx.Timeout(600.0, connect=10.0),
        )
    return _ollama_client


def use_ollama() -> bool:
    return not config.anthropic_api_key


async def llm_generate(
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    """Generate text from the configured LLM backend. Returns raw text."""
    if use_ollama():
        return await _ollama_generate(system, user_message, max_tokens)
    return await _anthropic_generate(system, user_message, max_tokens, model)


async def _anthropic_generate(
    system: str, user_message: str, max_tokens: int, model: str | None
) -> str:
    client = _get_anthropic_client()
    response = await client.messages.create(
        model=model or config.compile_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


async def _ollama_generate(system: str, user_message: str, max_tokens: int) -> str:
    client = _get_ollama_client()
    payload = {
        "model": config.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "format": "json",
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.3,
        },
    }
    resp = await client.post("/api/chat", json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data["message"]["content"].strip()


async def llm_stream(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Stream text from Claude. Yields text chunks. Ollama fallback uses non-streaming."""
    if use_ollama():
        # Ollama fallback — return full response as single chunk
        text = await _ollama_generate(system, user_message, max_tokens)
        yield text
        return

    client = _get_anthropic_client()
    async with client.messages.stream(
        model=model or config.explore_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
