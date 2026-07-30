"""Apply automated content screening with tiered outcomes."""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.models.moderation_action import ModerationActionType
from app.models.report import ReportTargetType
from app.moderation.base import (
    ModerationAdapter,
    ModerationResult,
    ModerationTier,
    get_moderation_adapter,
)
from app.observability.metrics import send_alert
from app.repositories.moderation_actions import ModerationActionRepository
from app.repositories.moderation_reviews import ModerationReviewRepository


class ContentModerationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        adapter: ModerationAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._adapter = adapter or get_moderation_adapter(self._settings)
        self._actions = ModerationActionRepository(session)
        self._reviews = ModerationReviewRepository(session)

    async def screen_text(
        self,
        *,
        text: str,
        context: str,
        target_type: ReportTargetType,
        target_id: uuid.UUID,
        user_id: uuid.UUID | None,
        commit: bool = False,
    ) -> ModerationResult:
        result = await self._adapter.screen_text(text=text, context=context)
        await self._apply_result(
            result=result,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            commit=commit,
        )
        return result

    async def screen_image(
        self,
        *,
        data: bytes,
        content_type: str,
        target_type: ReportTargetType,
        target_id: uuid.UUID,
        user_id: uuid.UUID | None,
        commit: bool = False,
    ) -> ModerationResult:
        result = await self._adapter.screen_image(data=data, content_type=content_type)
        await self._apply_result(
            result=result,
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            commit=commit,
        )
        return result

    async def _apply_result(
        self,
        *,
        result: ModerationResult,
        target_type: ReportTargetType,
        target_id: uuid.UUID,
        user_id: uuid.UUID | None,
        commit: bool,
    ) -> None:
        if result.tier == ModerationTier.allow:
            return

        categories = ",".join(result.categories)
        provider_blob = result.provider_response
        if result.tier == ModerationTier.block:
            await self._actions.record(
                operator_identity=f"auto:{result.provider}",
                action=ModerationActionType.auto_block_content,
                target_type=target_type,
                target_id=target_id,
                reason=f"Blocked ({categories or 'objectionable'}) confidence={result.confidence:.2f}",
                commit=commit,
            )
            raise AppError(
                code="content_rejected",
                message=(
                    "This content couldn't be published because it appears to violate "
                    "our community guidelines."
                ),
                status_code=422,
                details={
                    "categories": list(result.categories),
                    "confidence": result.confidence,
                },
            )

        # Medium confidence: publish path continues, but queue for operator review.
        await self._reviews.enqueue(
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            confidence=result.confidence,
            categories=categories,
            provider=result.provider,
            provider_response=provider_blob,
            commit=commit,
        )
        await self._actions.record(
            operator_identity=f"auto:{result.provider}",
            action=ModerationActionType.auto_queue_review,
            target_type=target_type,
            target_id=target_id,
            reason=f"Queued ({categories or 'sensitive'}) confidence={result.confidence:.2f}",
            commit=commit,
        )
        await send_alert(
            self._settings,
            title="Content queued for moderation review",
            detail=json.dumps(
                {
                    "target_type": target_type.value,
                    "target_id": str(target_id),
                    "user_id": str(user_id) if user_id else None,
                    "confidence": result.confidence,
                    "categories": list(result.categories),
                    "provider": result.provider,
                }
            ),
        )
