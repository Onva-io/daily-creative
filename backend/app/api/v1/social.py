"""Likes and Reflections routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_optional_current_user
from app.core.clock import Clock, get_clock
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.social import (
    CreateReflectionRequest,
    LikeState,
    ReflectionListResponse,
    ReflectionResponse,
)
from app.services.social import SocialService

router = APIRouter(tags=["submissions"])
reflections_router = APIRouter(tags=["reflections"])


@router.put("/submissions/{submission_id}/like", response_model=LikeState)
async def like_submission(
    submission_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> LikeState:
    return await SocialService(session, clock, settings).like(
        user=user,
        submission_id=submission_id,
    )


@router.delete("/submissions/{submission_id}/like", response_model=LikeState)
async def unlike_submission(
    submission_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> LikeState:
    return await SocialService(session, clock, settings).unlike(
        user=user,
        submission_id=submission_id,
    )


@router.get(
    "/submissions/{submission_id}/reflections",
    response_model=ReflectionListResponse,
)
async def list_reflections(
    submission_id: UUID,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    viewer: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> ReflectionListResponse:
    return await SocialService(session, clock, settings).list_reflections(
        submission_id=submission_id,
        cursor=cursor,
        limit=limit,
        viewer=viewer,
    )


@router.post(
    "/submissions/{submission_id}/reflections",
    response_model=ReflectionResponse,
    status_code=201,
)
async def create_reflection(
    submission_id: UUID,
    payload: CreateReflectionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ReflectionResponse:
    body, status_code = await SocialService(session, clock, settings).create_reflection(
        user=user,
        submission_id=submission_id,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    return body


@reflections_router.delete("/reflections/{reflection_id}", status_code=204)
async def delete_reflection(
    reflection_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    settings: Settings = Depends(get_settings),
) -> Response:
    await SocialService(session, clock, settings).delete_reflection(
        user=user,
        reflection_id=reflection_id,
    )
    return Response(status_code=204)
