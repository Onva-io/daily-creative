"""Story Session persistence helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import TimerMode
from app.models.story_session import StorySession, StorySessionStatus
from app.models.story_session_event import StorySessionEvent, StorySessionEventType


class StorySessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: uuid.UUID) -> StorySession | None:
        result = await self._session.execute(
            select(StorySession).where(StorySession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        prompt_id: uuid.UUID,
        timer_mode: TimerMode,
        selected_timer_seconds: int | None,
        started_at: datetime,
        started_metadata: dict[str, Any] | None = None,
    ) -> StorySession:
        story_session = StorySession(
            id=uuid.uuid4(),
            user_id=user_id,
            prompt_id=prompt_id,
            timer_mode=timer_mode,
            selected_timer_seconds=selected_timer_seconds,
            status=StorySessionStatus.active,
            started_at=started_at,
            paused_total_seconds=0,
        )
        self._session.add(story_session)
        await self._session.flush()

        started_event = StorySessionEvent(
            id=uuid.uuid4(),
            story_session_id=story_session.id,
            event_type=StorySessionEventType.started,
            occurred_at=started_at,
            client_occurred_at=None,
            metadata_json=started_metadata or {},
        )
        self._session.add(started_event)
        await self._session.commit()
        await self._session.refresh(story_session)
        return story_session

    async def add_event(
        self,
        *,
        story_session: StorySession,
        event_type: StorySessionEventType,
        occurred_at: datetime,
        client_occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StorySessionEvent:
        event = StorySessionEvent(
            id=uuid.uuid4(),
            story_session_id=story_session.id,
            event_type=event_type,
            occurred_at=occurred_at,
            client_occurred_at=client_occurred_at,
            metadata_json=metadata or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_latest_event(
        self,
        *,
        story_session_id: uuid.UUID,
        event_type: StorySessionEventType,
    ) -> StorySessionEvent | None:
        result = await self._session.execute(
            select(StorySessionEvent)
            .where(
                StorySessionEvent.story_session_id == story_session_id,
                StorySessionEvent.event_type == event_type,
            )
            .order_by(StorySessionEvent.occurred_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(
        self,
        story_session: StorySession,
        *,
        commit: bool = True,
    ) -> StorySession:
        if commit:
            await self._session.commit()
            await self._session.refresh(story_session)
        else:
            await self._session.flush()
        return story_session
