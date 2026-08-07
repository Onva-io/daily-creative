"""Unit tests for OpenAI moderation adapter (no network)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.core.settings import Settings
from app.moderation.base import ModerationTier, get_moderation_adapter
from app.moderation.openai import OpenAIModerationAdapter


class _FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, payload: dict[str, Any], *, status_code: int = 200) -> None:
        self._payload = payload
        self._status_code = status_code
        self.calls = 0

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        return httpx.Response(
            self._status_code,
            request=request,
            content=json.dumps(self._payload).encode("utf-8"),
            headers={"content-type": "application/json"},
        )


@pytest.mark.asyncio
async def test_openai_adapter_blocks_high_score() -> None:
    transport = _FakeTransport(
        {
            "results": [
                {
                    "flagged": True,
                    "category_scores": {"hate": 0.95, "harassment": 0.1},
                }
            ]
        }
    )
    client = httpx.AsyncClient(transport=transport)
    settings = Settings(
        OPENAI_API_KEY="test-key",  # pragma: allowlist secret
        OPENAI_MODERATION_BLOCK_THRESHOLD=0.8,
        OPENAI_MODERATION_QUEUE_THRESHOLD=0.4,
    )
    adapter = OpenAIModerationAdapter(settings, client=client)
    result = await adapter.screen_text(text="bad", context="caption")
    assert result.tier == ModerationTier.block
    assert "hate" in result.categories
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_adapter_queues_medium_score() -> None:
    transport = _FakeTransport(
        {
            "results": [
                {
                    "flagged": False,
                    "category_scores": {"profanity": 0.55},
                }
            ]
        }
    )
    client = httpx.AsyncClient(transport=transport)
    settings = Settings(
        OPENAI_API_KEY="test-key",  # pragma: allowlist secret
        OPENAI_MODERATION_BLOCK_THRESHOLD=0.8,
        OPENAI_MODERATION_QUEUE_THRESHOLD=0.4,
    )
    adapter = OpenAIModerationAdapter(settings, client=client)
    result = await adapter.screen_text(text="borderline", context="reflection")
    assert result.tier == ModerationTier.queue
    await client.aclose()


@pytest.mark.asyncio
async def test_openai_adapter_fails_closed_to_queue() -> None:
    transport = _FakeTransport({}, status_code=500)
    client = httpx.AsyncClient(transport=transport)
    settings = Settings(OPENAI_API_KEY="test-key")  # pragma: allowlist secret
    adapter = OpenAIModerationAdapter(settings, client=client)
    result = await adapter.screen_image(data=b"abc", content_type="image/jpeg")
    assert result.tier == ModerationTier.queue
    assert "provider_error" in result.categories
    await client.aclose()


def test_get_moderation_adapter_openai() -> None:
    settings = Settings(
        MODERATION_PROVIDER="openai",
        OPENAI_API_KEY="test-key",  # pragma: allowlist secret
    )
    adapter = get_moderation_adapter(settings)
    assert isinstance(adapter, OpenAIModerationAdapter)


def test_get_moderation_adapter_defaults_heuristic() -> None:
    settings = Settings(MODERATION_PROVIDER="heuristic")
    adapter = get_moderation_adapter(settings)
    assert adapter.__class__.__name__ == "HeuristicModerationAdapter"
