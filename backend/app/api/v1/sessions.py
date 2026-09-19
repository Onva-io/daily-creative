"""Creative Session routes (shared by every creative type)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.clock import Clock, get_clock
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.sessions import (
    CreateSessionRequest,
    CreativeSessionResponse,
    SessionEventRequest,
)
from app.services.creative_sessions import CreativeSessionService

router = APIRouter(tags=["sessions"])


@router.post("/sessions", response_model=CreativeSessionResponse, status_code=201)
async def create_session(
    payload: CreateSessionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> CreativeSessionResponse:
    body, status_code = await CreativeSessionService(session, clock).create(
        user=user,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    return body


@router.get("/sessions/{session_id}", response_model=CreativeSessionResponse)
async def get_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> CreativeSessionResponse:
    return await CreativeSessionService(session, clock).get(user=user, session_id=session_id)


@router.post("/sessions/{session_id}/events", response_model=CreativeSessionResponse)
async def post_session_event(
    session_id: UUID,
    payload: SessionEventRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> CreativeSessionResponse:
    return await CreativeSessionService(session, clock).record_event(
        user=user,
        session_id=session_id,
        payload=payload,
    )


@router.post("/sessions/{session_id}/abandon", response_model=CreativeSessionResponse)
async def abandon_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> CreativeSessionResponse:
    return await CreativeSessionService(session, clock).abandon(user=user, session_id=session_id)
