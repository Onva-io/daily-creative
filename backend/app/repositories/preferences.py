"""User preferences persistence helpers."""

from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_preferences import AppearancePreference, TimerMode, UserPreferences


class PreferencesRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> UserPreferences | None:
        result = await self._session.execute(
            select(UserPreferences).where(UserPreferences.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_defaults(self, user_id: uuid.UUID) -> UserPreferences:
        prefs = UserPreferences(
            user_id=user_id,
            notifications_enabled=False,
            notification_time_local=None,
            timezone="UTC",
            remember_timer_option=False,
            remembered_timer_mode=None,
            remembered_timer_seconds=None,
            appearance=AppearancePreference.system,
        )
        self._session.add(prefs)
        try:
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            existing = await self.get_by_user_id(user_id)
            if existing is not None:
                return existing
            raise
        await self._session.refresh(prefs)
        return prefs

    async def update(
        self,
        prefs: UserPreferences,
        *,
        notifications_enabled: bool | None = None,
        notification_time_local: time | None | object = ...,
        timezone: str | None = None,
        remember_timer_option: bool | None = None,
        remembered_timer_mode: TimerMode | None | object = ...,
        remembered_timer_seconds: int | None | object = ...,
        appearance: AppearancePreference | None = None,
    ) -> UserPreferences:
        if notifications_enabled is not None:
            prefs.notifications_enabled = notifications_enabled
        if notification_time_local is not ...:
            prefs.notification_time_local = notification_time_local  # type: ignore[assignment]
        if timezone is not None:
            prefs.timezone = timezone
        if remember_timer_option is not None:
            prefs.remember_timer_option = remember_timer_option
        if remembered_timer_mode is not ...:
            prefs.remembered_timer_mode = remembered_timer_mode  # type: ignore[assignment]
        if remembered_timer_seconds is not ...:
            prefs.remembered_timer_seconds = remembered_timer_seconds  # type: ignore[assignment]
        if appearance is not None:
            prefs.appearance = appearance
        await self._session.commit()
        await self._session.refresh(prefs)
        return prefs
