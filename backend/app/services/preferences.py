"""Preferences application services."""

from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.user_preferences import AppearancePreference, TimerMode, UserPreferences
from app.repositories.preferences import PreferencesRepository
from app.schemas.me import PreferencesSummary, PreferencesUpdateRequest

ALLOWED_TIMER_SECONDS = frozenset({60, 180, 300, 600})


class PreferencesService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = PreferencesRepository(session)

    async def get_or_create(self, user_id: uuid.UUID) -> UserPreferences:
        existing = await self._repo.get_by_user_id(user_id)
        if existing is not None:
            return existing
        return await self._repo.create_defaults(user_id)

    async def get_summary(self, user_id: uuid.UUID) -> PreferencesSummary:
        prefs = await self.get_or_create(user_id)
        return PreferencesSummary.from_orm_prefs(prefs)

    async def update(
        self,
        user_id: uuid.UUID,
        payload: PreferencesUpdateRequest,
    ) -> PreferencesSummary:
        prefs = await self.get_or_create(user_id)

        notification_time: time | None | object = ...
        if "notification_time_local" in payload.model_fields_set:
            if payload.notification_time_local is None:
                notification_time = None
            else:
                notification_time = _parse_local_time(payload.notification_time_local)

        remembered_mode: TimerMode | None | object = ...
        if "remembered_timer_mode" in payload.model_fields_set:
            if payload.remembered_timer_mode is None:
                remembered_mode = None
            else:
                remembered_mode = TimerMode(payload.remembered_timer_mode.value)

        remembered_seconds: int | None | object = ...
        if "remembered_timer_seconds" in payload.model_fields_set:
            remembered_seconds = payload.remembered_timer_seconds

        appearance: AppearancePreference | None = None
        if payload.appearance is not None:
            appearance = AppearancePreference(payload.appearance.value)

        # Validate the effective timer combination after applying the patch.
        effective_mode = (
            remembered_mode if remembered_mode is not ... else prefs.remembered_timer_mode
        )
        effective_seconds = (
            remembered_seconds if remembered_seconds is not ... else prefs.remembered_timer_seconds
        )
        _validate_timer_preference(effective_mode, effective_seconds)

        updated = await self._repo.update(
            prefs,
            notifications_enabled=payload.notifications_enabled,
            notification_time_local=notification_time,
            timezone=payload.timezone,
            remember_timer_option=payload.remember_timer_option,
            remembered_timer_mode=remembered_mode,
            remembered_timer_seconds=remembered_seconds,
            appearance=appearance,
        )
        return PreferencesSummary.from_orm_prefs(updated)


def validate_timer_preference(
    mode: TimerMode | None,
    seconds: int | None,
) -> None:
    """Public helper for unit tests and callers outside the service."""
    _validate_timer_preference(mode, seconds)


def _validate_timer_preference(
    mode: TimerMode | None | object,
    seconds: int | None | object,
) -> None:
    if mode is None and seconds is None:
        return
    if mode == TimerMode.no_timer:
        if seconds is not None:
            raise AppError(
                code="invalid_timer_preference",
                message="Timer preference mode and seconds are inconsistent.",
                status_code=422,
            )
        return
    if mode == TimerMode.countdown:
        if not isinstance(seconds, int) or seconds not in ALLOWED_TIMER_SECONDS:
            raise AppError(
                code="invalid_timer_preference",
                message="Timer preference mode and seconds are inconsistent.",
                status_code=422,
            )
        return
    if mode is None and seconds is not None:
        raise AppError(
            code="invalid_timer_preference",
            message="Timer preference mode and seconds are inconsistent.",
            status_code=422,
        )


def _parse_local_time(value: str) -> time:
    parts = value.strip().split(":")
    if len(parts) not in {2, 3}:
        raise AppError(
            code="validation_error",
            message="The request could not be validated.",
            status_code=422,
            details={"field": "notification_time_local"},
        )
    try:
        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0
        return time(hour=hour, minute=minute, second=second)
    except ValueError as exc:
        raise AppError(
            code="validation_error",
            message="The request could not be validated.",
            status_code=422,
            details={"field": "notification_time_local"},
        ) from exc
