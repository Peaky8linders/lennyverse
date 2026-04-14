"""Claude API client for LennyVerse — compilation and exploration."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator

import httpx

from app.config import config

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key,
            timeout=httpx.Timeout(config.llm_timeout, connect=10.0),
        )
    return _client


async def llm_generate(
    system: str,
    user_message: str,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    """Generate text from Claude. Returns the raw text response."""
    client = _get_client()
    response = await client.messages.create(
        model=model or config.compile_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text.strip()


async def llm_stream(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Stream text from Claude. Yields text chunks."""
    client = _get_client()
    async with client.messages.stream(
        model=model or config.explore_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
