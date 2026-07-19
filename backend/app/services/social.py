"""Likes and Reflections application service."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.pagination import decode_reflection_cursor, encode_reflection_cursor
from app.core.settings import Settings, get_settings
from app.models.activity_event import ActivityEventType
from app.models.reflection import Reflection, ReflectionStatus
from app.models.submission import Submission, SubmissionStatus
from app.models.user import User, UserStatus
from app.repositories.activity_events import ActivityEventRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.likes import LikeRepository
from app.repositories.reflections import ReflectionRepository
from app.repositories.submissions import SubmissionRepository
from app.repositories.users import UserRepository
from app.schemas.feed import FeedUserSummary
from app.schemas.social import (
    CreateReflectionRequest,
    LikeState,
    ReflectionListResponse,
    ReflectionResponse,
)
from app.services.profile import ProfileService

CREATE_REFLECTION_ENDPOINT = "POST /api/v1/submissions/{submission_id}/reflections"


class SocialService:
    """Version-one Likes and Reflections."""

    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._likes = LikeRepository(session)
        self._reflections = ReflectionRepository(session)
        self._activity = ActivityEventRepository(session)
        self._submissions = SubmissionRepository(session)
        self._users = UserRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._clock = clock
        self._settings = settings or get_settings()

    async def like(self, *, user: User, submission_id: uuid.UUID) -> LikeState:
        submission = await self._require_visible_submission(submission_id)
        now = self._clock.now()
        inserted = await self._likes.add(
            submission_id=submission.id,
            user_id=user.id,
            created_at=now,
            commit=False,
        )
        if inserted:
            submission.like_count = submission.like_count + 1
            if user.id != submission.user_id:
                await self._activity.add(
                    recipient_user_id=submission.user_id,
                    actor_user_id=user.id,
                    event_type=ActivityEventType.submission_liked,
                    submission_id=submission.id,
                    commit=False,
                )
        await self._session.commit()
        await self._session.refresh(submission)
        return LikeState(liked=True, like_count=submission.like_count)

    async def unlike(self, *, user: User, submission_id: uuid.UUID) -> LikeState:
        submission = await self._require_visible_submission(submission_id)
        deleted = await self._likes.delete(
            submission_id=submission.id,
            user_id=user.id,
            commit=False,
        )
        if deleted:
            submission.like_count = max(0, submission.like_count - 1)
        await self._session.commit()
        await self._session.refresh(submission)
        liked = await self._likes.exists(submission_id=submission.id, user_id=user.id)
        return LikeState(liked=liked, like_count=submission.like_count)

    async def list_reflections(
        self,
        *,
        submission_id: uuid.UUID,
        cursor: str | None = None,
        limit: int = 20,
        viewer: User | None = None,
    ) -> ReflectionListResponse:
        await self._require_visible_submission(submission_id)
        cursor_created_at = None
        cursor_id = None
        if cursor:
            cursor_created_at, cursor_id = decode_reflection_cursor(cursor)

        rows = await self._reflections.list_for_submission(
            submission_id=submission_id,
            limit=limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        page_rows = rows[:limit]
        next_cursor: str | None = None
        if len(rows) > limit:
            last = page_rows[-1].reflection
            next_cursor = encode_reflection_cursor(
                created_at=last.created_at,
                reflection_id=last.id,
            )

        items = [
            self._to_reflection_response(
                reflection=row.reflection,
                author=row.user,
                viewer=viewer,
            )
            for row in page_rows
        ]
        return ReflectionListResponse(items=items, next_cursor=next_cursor)

    async def create_reflection(
        self,
        *,
        user: User,
        submission_id: uuid.UUID,
        payload: CreateReflectionRequest,
        idempotency_key: str | None,
    ) -> tuple[ReflectionResponse, int]:
        ProfileService.require_complete_profile(user)
        body = normalise_reflection_body(payload.body, self._settings.reflection_max_length)
        request_hash = _hash_reflection_request(submission_id=submission_id, body=body)
        endpoint = CREATE_REFLECTION_ENDPOINT.format(submission_id=submission_id)

        if idempotency_key:
            existing = await self._idempotency.get(
                user_id=user.id,
                endpoint=endpoint,
                key=idempotency_key,
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise AppError(
                        code="idempotency_key_conflict",
                        message=("This idempotency key was already used with a different request."),
                        status_code=409,
                    )
                return (
                    ReflectionResponse.model_validate(existing.response_body),
                    existing.response_status,
                )

        submission = await self._require_visible_submission(submission_id)
        reflection = await self._reflections.create(
            submission_id=submission.id,
            user_id=user.id,
            body=body,
            commit=False,
        )
        submission.reflection_count = submission.reflection_count + 1
        if user.id != submission.user_id:
            await self._activity.add(
                recipient_user_id=submission.user_id,
                actor_user_id=user.id,
                event_type=ActivityEventType.reflection_added,
                submission_id=submission.id,
                reflection_id=reflection.id,
                commit=False,
            )
        await self._session.commit()
        await self._session.refresh(reflection)

        response = self._to_reflection_response(
            reflection=reflection,
            author=user,
            viewer=user,
        )
        if idempotency_key:
            await self._idempotency.put(
                user_id=user.id,
                endpoint=endpoint,
                key=idempotency_key,
                request_hash=request_hash,
                response_status=201,
                response_body=response.model_dump(mode="json"),
                expires_at=self._clock.now() + timedelta(days=7),
            )
        return response, 201

    async def delete_reflection(self, *, user: User, reflection_id: uuid.UUID) -> None:
        reflection = await self._reflections.get_by_id(reflection_id)
        if (
            reflection is None
            or reflection.status == ReflectionStatus.deleted
            or reflection.deleted_at is not None
        ):
            raise AppError(
                code="reflection_not_found",
                message="The requested reflection could not be found.",
                status_code=404,
            )
        if reflection.user_id != user.id:
            raise AppError(
                code="reflection_forbidden",
                message="You can only delete your own reflection.",
                status_code=403,
            )

        submission = await self._submissions.get_by_id(reflection.submission_id)
        now = self._clock.now()
        transitioned = await self._reflections.soft_delete(
            reflection,
            deleted_at=now,
            commit=False,
        )
        if transitioned and submission is not None:
            submission.reflection_count = max(0, submission.reflection_count - 1)
        await self._session.commit()

    async def _require_visible_submission(self, submission_id: uuid.UUID) -> Submission:
        submission = await self._submissions.get_by_id(submission_id)
        if (
            submission is None
            or submission.status != SubmissionStatus.published
            or submission.deleted_at is not None
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested sketch could not be found.",
                status_code=404,
            )
        author = await self._users.get_by_id(submission.user_id)
        if (
            author is None
            or author.deleted_at is not None
            or author.status
            not in {
                UserStatus.incomplete,
                UserStatus.active,
            }
        ):
            raise AppError(
                code="submission_not_found",
                message="The requested sketch could not be found.",
                status_code=404,
            )
        return submission

    @staticmethod
    def _to_reflection_response(
        *,
        reflection: Reflection,
        author: User,
        viewer: User | None,
    ) -> ReflectionResponse:
        return ReflectionResponse(
            id=reflection.id,
            submission_id=reflection.submission_id,
            user=FeedUserSummary(
                id=author.id,
                username=author.username or "",
                display_name=author.display_name,
                avatar_url=None,
            ),
            body=reflection.body,
            created_at=reflection.created_at,
            is_author=viewer is not None and viewer.id == reflection.user_id,
        )


def normalise_reflection_body(body: str, max_length: int) -> str:
    stripped = body.strip()
    if not stripped:
        raise AppError(
            code="validation_error",
            message="The request could not be validated.",
            status_code=422,
            details={"body": "empty"},
        )
    if len(stripped) > max_length:
        raise AppError(
            code="validation_error",
            message="The request could not be validated.",
            status_code=422,
            details={"body": "too_long"},
        )
    return stripped


def _hash_reflection_request(*, submission_id: uuid.UUID, body: str) -> str:
    canonical = json.dumps(
        {"submission_id": str(submission_id), "body": body},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
