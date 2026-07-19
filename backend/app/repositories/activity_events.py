"""Activity event repository."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_event import ActivityEvent, ActivityEventType


class ActivityEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        *,
        recipient_user_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        event_type: ActivityEventType,
        submission_id: uuid.UUID | None = None,
        reflection_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> ActivityEvent:
        event = ActivityEvent(
            id=uuid.uuid4(),
            recipient_user_id=recipient_user_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            submission_id=submission_id,
            reflection_id=reflection_id,
        )
        self._session.add(event)
        if commit:
            await self._session.commit()
            await self._session.refresh(event)
        else:
            await self._session.flush()
        return event
