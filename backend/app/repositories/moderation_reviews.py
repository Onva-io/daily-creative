"""Moderation review queue repository."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.moderation_review import ModerationReviewItem, ModerationReviewStatus
from app.models.report import ReportTargetType


class ModerationReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def enqueue(
        self,
        *,
        target_type: ReportTargetType,
        target_id: uuid.UUID,
        user_id: uuid.UUID | None,
        confidence: float,
        categories: str,
        provider: str,
        provider_response: str | None = None,
        commit: bool = True,
    ) -> ModerationReviewItem:
        row = ModerationReviewItem(
            id=uuid.uuid4(),
            target_type=target_type,
            target_id=target_id,
            user_id=user_id,
            status=ModerationReviewStatus.open,
            confidence=confidence,
            categories=categories,
            provider=provider,
            provider_response=provider_response,
        )
        self._session.add(row)
        if commit:
            await self._session.commit()
            await self._session.refresh(row)
        else:
            await self._session.flush()
        return row

    async def list_open(self, *, limit: int = 50) -> list[ModerationReviewItem]:
        result = await self._session.execute(
            select(ModerationReviewItem)
            .where(ModerationReviewItem.status == ModerationReviewStatus.open)
            .order_by(ModerationReviewItem.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def resolve(
        self,
        item: ModerationReviewItem,
        *,
        status: ModerationReviewStatus,
        resolved_at: datetime,
        commit: bool = True,
    ) -> ModerationReviewItem:
        item.status = status
        item.resolved_at = resolved_at
        if commit:
            await self._session.commit()
            await self._session.refresh(item)
        else:
            await self._session.flush()
        return item
