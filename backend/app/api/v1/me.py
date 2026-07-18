"""Current-user and preferences routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.me import (
    CurrentUserResponse,
    PreferencesSummary,
    PreferencesUpdateRequest,
    UpdateMeRequest,
)
from app.services.preferences import PreferencesService
from app.services.profile import ProfileService

router = APIRouter(tags=["me"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    return await ProfileService(session).get_current_user_response(user)


@router.patch("/me", response_model=CurrentUserResponse)
async def update_me(
    payload: UpdateMeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUserResponse:
    return await ProfileService(session).update_me(user, payload)


@router.get("/me/preferences", response_model=PreferencesSummary)
async def get_my_preferences(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PreferencesSummary:
    return await PreferencesService(session).get_summary(user.id)


@router.patch("/me/preferences", response_model=PreferencesSummary)
async def update_my_preferences(
    payload: PreferencesUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PreferencesSummary:
    return await PreferencesService(session).update(user.id, payload)
