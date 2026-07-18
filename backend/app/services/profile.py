"""Profile application services."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.usernames import (
    is_reserved_username,
    is_valid_username_format,
    normalize_username,
)
from app.models.user import User, UserStatus
from app.repositories.users import UserRepository
from app.schemas.me import (
    CurrentUserResponse,
    PreferencesSummary,
    PublicUserResponse,
    UpdateMeRequest,
)
from app.services.preferences import PreferencesService


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._users = UserRepository(session)
        self._preferences_service = PreferencesService(session)

    async def get_current_user_response(self, user: User) -> CurrentUserResponse:
        prefs = await self._preferences_service.get_or_create(user.id)
        return CurrentUserResponse.from_user(user, PreferencesSummary.from_orm_prefs(prefs))

    async def update_me(self, user: User, payload: UpdateMeRequest) -> CurrentUserResponse:
        username = payload.username
        username_normalized: str | None = None
        if username is not None:
            stripped = username.strip()
            if not is_valid_username_format(stripped):
                raise AppError(
                    code="username_invalid",
                    message=(
                        "Usernames must be 3–30 characters and use only "
                        "letters, numbers, and underscores."
                    ),
                    status_code=422,
                )
            if is_reserved_username(stripped):
                raise AppError(
                    code="username_reserved",
                    message="That username is reserved.",
                    status_code=422,
                )
            username_normalized = normalize_username(stripped)
            existing = await self._users.get_by_username_normalized(username_normalized)
            if existing is not None and existing.id != user.id:
                raise AppError(
                    code="username_taken",
                    message="That username is already taken.",
                    status_code=409,
                )
            username = stripped

        display_name = payload.display_name
        if display_name is not None:
            display_name = display_name.strip()
            if not display_name:
                raise AppError(
                    code="validation_error",
                    message="Display name cannot be empty.",
                    status_code=422,
                )

        bio_sentinel: object = ...
        if "bio" in payload.model_fields_set:
            bio_sentinel = payload.bio

        effective_username = username if username is not None else user.username
        effective_display = display_name if display_name is not None else user.display_name
        should_complete = (
            effective_username is not None
            and bool(effective_display)
            and user.profile_completed_at is None
        )

        status_update: UserStatus | None = None
        completed_at: datetime | None | object = ...
        if should_complete:
            completed_at = datetime.now(timezone.utc)
            if user.status == UserStatus.incomplete:
                status_update = UserStatus.active

        await self._users.update_profile(
            user,
            username=username,
            username_normalized=username_normalized,
            display_name=display_name,
            bio=bio_sentinel,
            status=status_update,
            profile_completed_at=completed_at,
        )
        return await self.get_current_user_response(user)

    async def get_public_user(self, username: str) -> PublicUserResponse:
        normalized = normalize_username(username)
        user = await self._users.get_by_username_normalized(normalized)
        if (
            user is None
            or user.username is None
            or user.status != UserStatus.active
            or user.profile_completed_at is None
            or user.deleted_at is not None
        ):
            raise AppError(
                code="user_not_found",
                message="The requested profile could not be found.",
                status_code=404,
            )
        return PublicUserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            bio=user.bio,
            avatar_url=None,
        )

    @staticmethod
    def require_complete_profile(user: User) -> None:
        """Guard for publish and other complete-profile-required writes."""
        if user.profile_completed_at is None or user.status == UserStatus.incomplete:
            raise AppError(
                code="profile_incomplete",
                message="Complete your profile before publishing.",
                status_code=403,
            )
