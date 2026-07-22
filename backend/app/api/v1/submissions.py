"""Submission routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user, get_optional_current_user
from app.core.clock import Clock, get_clock
from app.core.settings import Settings, get_settings
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.submissions import CreateSubmissionRequest, SubmissionResponse
from app.services.publications import PublicationService
from app.storage.base import StorageAdapter, get_storage_adapter

router = APIRouter(tags=["submissions"])


@router.post("/submissions", response_model=SubmissionResponse, status_code=201)
async def create_submission(
    payload: CreateSubmissionRequest,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    storage: StorageAdapter = Depends(get_storage_adapter),
    settings: Settings = Depends(get_settings),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> SubmissionResponse:
    body, status_code = await PublicationService(session, clock, storage, settings).create(
        user=user,
        payload=payload,
        idempotency_key=idempotency_key,
    )
    response.status_code = status_code
    return body


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(
    submission_id: UUID,
    viewer: User | None = Depends(get_optional_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    storage: StorageAdapter = Depends(get_storage_adapter),
    settings: Settings = Depends(get_settings),
) -> SubmissionResponse:
    return await PublicationService(session, clock, storage, settings).get(
        submission_id=submission_id,
        viewer=viewer,
    )


@router.delete("/submissions/{submission_id}", status_code=204)
async def delete_submission(
    submission_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    clock: Clock = Depends(get_clock),
    storage: StorageAdapter = Depends(get_storage_adapter),
    settings: Settings = Depends(get_settings),
) -> Response:
    await PublicationService(session, clock, storage, settings).delete(
        user=user,
        submission_id=submission_id,
    )
    return Response(status_code=204)
