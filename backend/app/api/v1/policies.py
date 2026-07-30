"""Public policy document and consent routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user_identity
from app.core.clock import Clock, get_clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.policy import PolicyKind
from app.models.user import User
from app.schemas.me import CurrentUserResponse
from app.schemas.policies import (
    AcceptPoliciesRequest,
    AcceptPoliciesResponse,
    ConsentState,
    CurrentPoliciesResponse,
    SetDateOfBirthRequest,
)
from app.services.policies import PolicyService
from app.services.profile import ProfileService
from app.storage.base import StorageAdapter, get_storage_adapter
from app.models.enums import CreativeType

router = APIRouter(tags=["policies"])


@router.get("/policies/current", response_model=CurrentPoliciesResponse)
async def get_current_policies(
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> CurrentPoliciesResponse:
    return await PolicyService(session, clock=clock, settings=settings).current_policies()


@router.get("/policies/{kind}/html", response_class=Response, include_in_schema=False)
async def get_policy_html(
    kind: str,
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> Response:
    try:
        policy_kind = PolicyKind(kind)
    except ValueError as exc:
        raise AppError(
            code="policy_not_found",
            message="Unknown policy kind.",
            status_code=404,
        ) from exc
    html = await PolicyService(session, clock=clock, settings=settings).render_html(policy_kind)
    return Response(content=html, media_type="text/html; charset=utf-8")


@router.post("/me/policies/accept", response_model=AcceptPoliciesResponse)
async def accept_policies(
    payload: AcceptPoliciesRequest,
    user: User = Depends(get_current_user_identity),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> AcceptPoliciesResponse:
    return await PolicyService(session, clock=clock, settings=settings).accept(user, payload)


@router.post("/me/date-of-birth", response_model=CurrentUserResponse)
async def set_date_of_birth(
    payload: SetDateOfBirthRequest,
    user: User = Depends(get_current_user_identity),
    creative_type: CreativeType = Query(...),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    storage: StorageAdapter = Depends(get_storage_adapter),
    settings: Settings = Depends(get_settings),
) -> CurrentUserResponse:
    try:
        dob = date.fromisoformat(payload.date_of_birth)
    except ValueError as exc:
        raise AppError(
            code="date_of_birth_invalid",
            message="Date of birth must be an ISO date (YYYY-MM-DD).",
            status_code=422,
        ) from exc
    updated = await PolicyService(session, clock=clock, settings=settings).set_date_of_birth(
        user,
        date_of_birth=dob,
    )
    return await ProfileService(
        session,
        clock=clock,
        storage=storage,
        settings=settings,
    ).get_current_user_response(updated, creative_type=creative_type)


@router.get("/me/consent", response_model=ConsentState)
async def get_consent_state(
    user: User = Depends(get_current_user_identity),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> ConsentState:
    return await PolicyService(session, clock=clock, settings=settings).consent_state(user)
