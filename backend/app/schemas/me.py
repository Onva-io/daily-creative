"""API schemas for current-user, preferences, and public profile endpoints."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.creative_type_preferences import CreativeTypePreferences
from app.models.user import User
from app.models.user_preferences import UserPreferences


class UserStatusSchema(str, Enum):
    incomplete = "incomplete"
    active = "active"
    suspended = "suspended"
    pending_deletion = "pending_deletion"
    deleted = "deleted"


class TimerModeSchema(str, Enum):
    countdown = "countdown"
    no_timer = "no_timer"


class AppearancePreferenceSchema(str, Enum):
    system = "system"
    light = "light"
    dark = "dark"


class PreferencesSummary(BaseModel):
    """Server-backed preferences projection."""

    model_config = ConfigDict(extra="forbid")

    notifications_enabled: bool = False
    notification_time_local: str | None = None
    timezone: str = "UTC"
    remember_timer_option: bool = False
    remembered_timer_mode: TimerModeSchema | None = None
    remembered_timer_seconds: int | None = None
    appearance: AppearancePreferenceSchema = AppearancePreferenceSchema.system

    @classmethod
    def from_orm_prefs(
        cls,
        prefs: UserPreferences,
        type_prefs: CreativeTypePreferences | None = None,
    ) -> PreferencesSummary:
        time_value: str | None = None
        if prefs.notification_time_local is not None:
            time_value = prefs.notification_time_local.strftime("%H:%M:%S")
        mode = None
        remembered_seconds = None
        remember_timer_option = False
        if type_prefs is not None:
            remember_timer_option = type_prefs.remember_timer_option
            mode = (
                TimerModeSchema(type_prefs.remembered_timer_mode.value)
                if type_prefs.remembered_timer_mode is not None
                else None
            )
            remembered_seconds = type_prefs.remembered_timer_seconds
        return cls(
            notifications_enabled=prefs.notifications_enabled,
            notification_time_local=time_value,
            timezone=prefs.timezone,
            remember_timer_option=remember_timer_option,
            remembered_timer_mode=mode,
            remembered_timer_seconds=remembered_seconds,
            appearance=AppearancePreferenceSchema(prefs.appearance.value),
        )


class PreferencesUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notifications_enabled: bool | None = None
    notification_time_local: str | None = None
    timezone: str | None = None
    remember_timer_option: bool | None = None
    remembered_timer_mode: TimerModeSchema | None = None
    remembered_timer_seconds: int | None = None
    appearance: AppearancePreferenceSchema | None = None


class UpdateMeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=3, max_length=30)
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    bio: str | None = Field(default=None, max_length=280)
    avatar_upload_id: UUID | None = None


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    username: str | None
    display_name: str
    profile_completed: bool
    status: UserStatusSchema
    avatar_url: str | None
    preferences: PreferencesSummary

    @classmethod
    def from_user(
        cls,
        user: User,
        preferences: PreferencesSummary | None = None,
        *,
        avatar_url: str | None = None,
    ) -> CurrentUserResponse:
        return cls(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            profile_completed=user.profile_completed_at is not None,
            status=UserStatusSchema(user.status.value),
            avatar_url=avatar_url,
            preferences=preferences or PreferencesSummary(),
        )


class PublicUserResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    username: str
    display_name: str
    bio: str | None
    avatar_url: str | None
    submission_count: int = Field(ge=0)
    current_streak: int = Field(ge=0)
    is_self: bool = False
