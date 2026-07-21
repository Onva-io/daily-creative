"""Story Session routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.core.clock import Clock, get_clock
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.story_sessions import (
    CreateStorySessionRequest,
    StorySessionEventRequest,
    StorySessionResponse,
)
from app.services.story_sessions import StorySessionService

router = APIRouter(tags=["story-sessions"])


@router.post("/story-sessions", response_model=StorySessionResponse, status_code=201)
async def create_story_session(
    payload: CreateStorySessionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> StorySessionResponse:
    body, status_code = await StorySessionService(session, clock).create(
        user=user,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    return body


@router.get("/story-sessions/{session_id}", response_model=StorySessionResponse)
async def get_story_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> StorySessionResponse:
    return await StorySessionService(session, clock).get(user=user, session_id=session_id)


@router.post(
    "/story-sessions/{session_id}/events",
    response_model=StorySessionResponse,
)
async def post_story_session_event(
    session_id: UUID,
    payload: StorySessionEventRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> StorySessionResponse:
    return await StorySessionService(session, clock).record_event(
        user=user,
        session_id=session_id,
        payload=payload,
    )


@router.post(
    "/story-sessions/{session_id}/abandon",
    response_model=StorySessionResponse,
)
async def abandon_story_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
) -> StorySessionResponse:
    return await StorySessionService(session, clock).abandon(user=user, session_id=session_id)
