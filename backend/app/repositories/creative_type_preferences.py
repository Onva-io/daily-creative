"""Creative-type preferences persistence helpers."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative_type_preferences import CreativeTypePreferences
from app.models.enums import CreativeType, TimerMode


class CreativeTypePreferencesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(
        self,
        *,
        user_id: uuid.UUID,
        creative_type: CreativeType,
    ) -> CreativeTypePreferences | None:
        result = await self._session.execute(
            select(CreativeTypePreferences).where(
                CreativeTypePreferences.user_id == user_id,
                CreativeTypePreferences.creative_type == creative_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_defaults(
        self,
        *,
        user_id: uuid.UUID,
        creative_type: CreativeType,
    ) -> CreativeTypePreferences:
        existing = await self.get(user_id=user_id, creative_type=creative_type)
        if existing is not None:
            return existing
        prefs = CreativeTypePreferences(
            user_id=user_id,
            creative_type=creative_type,
            remember_timer_option=False,
            remembered_timer_mode=None,
            remembered_timer_seconds=None,
        )
        self._session.add(prefs)
        await self._session.commit()
        await self._session.refresh(prefs)
        return prefs

    async def update(
        self,
        prefs: CreativeTypePreferences,
        *,
        remember_timer_option: bool | None = None,
        remembered_timer_mode: TimerMode | None | object = ...,
        remembered_timer_seconds: int | None | object = ...,
    ) -> CreativeTypePreferences:
        if remember_timer_option is not None:
            prefs.remember_timer_option = remember_timer_option
        if remembered_timer_mode is not ...:
            prefs.remembered_timer_mode = remembered_timer_mode  # type: ignore[assignment]
        if remembered_timer_seconds is not ...:
            prefs.remembered_timer_seconds = remembered_timer_seconds  # type: ignore[assignment]
        await self._session.commit()
        await self._session.refresh(prefs)
        return prefs
