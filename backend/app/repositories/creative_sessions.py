"""Creative Session persistence helpers."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative_session import CreativeSession, CreativeSessionStatus
from app.models.creative_session_event import CreativeSessionEvent, GenericSessionEvent
from app.models.enums import CreativeType, TimerMode


class CreativeSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, session_id: uuid.UUID) -> CreativeSession | None:
        result = await self._session.execute(
            select(CreativeSession).where(CreativeSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        prompt_id: uuid.UUID,
        creative_type: CreativeType,
        timer_mode: TimerMode,
        selected_timer_seconds: int | None,
        started_at: datetime,
        started_metadata: dict[str, Any] | None = None,
    ) -> CreativeSession:
        creative_session = CreativeSession(
            id=uuid.uuid4(),
            user_id=user_id,
            prompt_id=prompt_id,
            creative_type=creative_type,
            timer_mode=timer_mode,
            selected_timer_seconds=selected_timer_seconds,
            status=CreativeSessionStatus.active,
            stage=None,
            stage_timestamps={},
            started_at=started_at,
            paused_total_seconds=0,
        )
        self._session.add(creative_session)
        await self._session.flush()

        started_event = CreativeSessionEvent(
            id=uuid.uuid4(),
            session_id=creative_session.id,
            event_type=GenericSessionEvent.started,
            occurred_at=started_at,
            client_occurred_at=None,
            metadata_json=started_metadata or {},
        )
        self._session.add(started_event)
        await self._session.commit()
        await self._session.refresh(creative_session)
        return creative_session

    async def add_event(
        self,
        *,
        creative_session: CreativeSession,
        event_type: str,
        occurred_at: datetime,
        client_occurred_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CreativeSessionEvent:
        event = CreativeSessionEvent(
            id=uuid.uuid4(),
            session_id=creative_session.id,
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
        session_id: uuid.UUID,
        event_type: str,
    ) -> CreativeSessionEvent | None:
        result = await self._session.execute(
            select(CreativeSessionEvent)
            .where(
                CreativeSessionEvent.session_id == session_id,
                CreativeSessionEvent.event_type == event_type,
            )
            .order_by(CreativeSessionEvent.occurred_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def save(
        self,
        creative_session: CreativeSession,
        *,
        commit: bool = True,
    ) -> CreativeSession:
        if commit:
            await self._session.commit()
            await self._session.refresh(creative_session)
        else:
            await self._session.flush()
        return creative_session
