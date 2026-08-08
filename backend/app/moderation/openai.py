"""OpenAI omni-moderation adapter for text and image screening."""

from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from app.core.settings import Settings
from app.moderation.base import ModerationResult, ModerationTier

_OPENAI_MODERATIONS_URL = "https://api.openai.com/v1/moderations"


class OpenAIModerationAdapter:
    """Screens text and images via OpenAI omni-moderation."""

    provider_name = "openai"

    def __init__(self, settings: Settings, *, client: httpx.AsyncClient | None = None) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when MODERATION_PROVIDER=openai")
        self._settings = settings
        self._api_key = settings.openai_api_key
        self._model = settings.openai_moderation_model
        self._block_threshold = settings.openai_moderation_block_threshold
        self._queue_threshold = settings.openai_moderation_queue_threshold
        self._client = client

    async def screen_text(self, *, text: str, context: str) -> ModerationResult:
        if not text.strip():
            return ModerationResult(
                tier=ModerationTier.allow,
                confidence=0.0,
                categories=(),
                provider=self.provider_name,
            )
        return await self._moderate(
            input_payload=[{"type": "text", "text": text}],
            context=context,
        )

    async def screen_image(self, *, data: bytes, content_type: str) -> ModerationResult:
        mime = content_type or "application/octet-stream"
        encoded = base64.b64encode(data).decode("ascii")
        data_url = f"data:{mime};base64,{encoded}"
        return await self._moderate(
            input_payload=[{"type": "image_url", "image_url": {"url": data_url}}],
            context="image",
        )

    async def _moderate(
        self,
        *,
        input_payload: list[dict[str, Any]],
        context: str,
    ) -> ModerationResult:
        try:
            response_json = await self._post(input_payload)
        except Exception as exc:  # noqa: BLE001 — fail closed to queue
            return ModerationResult(
                tier=ModerationTier.queue,
                confidence=0.5,
                categories=("provider_error",),
                provider=self.provider_name,
                provider_response=f"error:{type(exc).__name__};context={context}",
            )

        results = response_json.get("results")
        if not isinstance(results, list) or not results:
            return ModerationResult(
                tier=ModerationTier.queue,
                confidence=0.5,
                categories=("provider_error",),
                provider=self.provider_name,
                provider_response=f"empty_results;context={context}",
            )

        first = results[0]
        category_scores = first.get("category_scores") or {}
        if not isinstance(category_scores, dict):
            category_scores = {}

        flagged_categories: list[tuple[str, float]] = []
        max_score = 0.0
        for name, score in category_scores.items():
            try:
                value = float(score)
            except TypeError, ValueError:
                continue
            max_score = max(max_score, value)
            if value >= self._queue_threshold:
                flagged_categories.append((str(name), value))

        flagged_categories.sort(key=lambda item: item[1], reverse=True)
        categories = tuple(name for name, _ in flagged_categories)
        provider_response = json.dumps(
            {"context": context, "flagged": first.get("flagged"), "scores": category_scores}
        )

        if max_score >= self._block_threshold:
            return ModerationResult(
                tier=ModerationTier.block,
                confidence=max_score,
                categories=categories or ("flagged",),
                provider=self.provider_name,
                provider_response=provider_response,
            )
        if max_score >= self._queue_threshold or first.get("flagged") is True:
            return ModerationResult(
                tier=ModerationTier.queue,
                confidence=max_score if max_score > 0 else 0.6,
                categories=categories or ("flagged",),
                provider=self.provider_name,
                provider_response=provider_response,
            )
        return ModerationResult(
            tier=ModerationTier.allow,
            confidence=max_score,
            categories=(),
            provider=self.provider_name,
            provider_response=provider_response,
        )

    async def _post(self, input_payload: list[dict[str, Any]]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {"model": self._model, "input": input_payload}
        if self._client is not None:
            response = await self._client.post(
                _OPENAI_MODERATIONS_URL,
                headers=headers,
                json=body,
                timeout=30.0,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("OpenAI moderation response must be a JSON object")
            return payload

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                _OPENAI_MODERATIONS_URL,
                headers=headers,
                json=body,
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise TypeError("OpenAI moderation response must be a JSON object")
            return payload
