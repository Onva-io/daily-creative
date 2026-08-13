"""Guest age-declaration routes."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock, get_clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.schemas.policies import GuestAgeDeclarationResponse, SetDateOfBirthRequest
from app.services.policies import PolicyService

router = APIRouter(tags=["guest"])


@router.post("/guest/age-declaration", response_model=GuestAgeDeclarationResponse)
async def declare_guest_age(
    payload: SetDateOfBirthRequest,
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> GuestAgeDeclarationResponse:
    try:
        dob = date.fromisoformat(payload.date_of_birth)
    except ValueError as exc:
        raise AppError(
            code="date_of_birth_invalid",
            message="Date of birth must be an ISO date (YYYY-MM-DD).",
            status_code=422,
        ) from exc
    return await PolicyService(session, clock=clock, settings=settings).declare_guest_age(
        date_of_birth=dob,
    )
