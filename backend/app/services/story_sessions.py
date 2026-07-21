"""Story Session application service."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.models.enums import TimerMode
from app.models.story_session import StorySession, StorySessionStatus
from app.models.story_session_event import StorySessionEventType
from app.models.user import User
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.prompts import PromptRepository
from app.repositories.story_sessions import StorySessionRepository
from app.schemas.story_sessions import (
    CreateStorySessionRequest,
    StorySessionEventRequest,
    StorySessionEventTypeSchema,
    StorySessionResponse,
)
from app.services.preferences import ALLOWED_TIMER_SECONDS

CREATE_ENDPOINT = "POST /api/v1/story-sessions"

CLIENT_EVENTS = frozenset(
    {
        StorySessionEventType.paused,
        StorySessionEventType.resumed,
        StorySessionEventType.timer_completed,
        StorySessionEventType.finished_early,
        StorySessionEventType.writing_started,
        StorySessionEventType.draft_saved,
        StorySessionEventType.abandoned,
    }
)

TERMINAL_STATUSES = frozenset(
    {
        StorySessionStatus.completed,
        StorySessionStatus.abandoned,
        StorySessionStatus.expired,
    }
)


class StorySessionService:
    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        settings: Settings | None = None,
    ) -> None:
        self._sessions = StorySessionRepository(session)
        self._prompts = PromptRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._clock = clock
        self._settings = settings or get_settings()

    async def create(
        self,
        *,
        user: User,
        payload: CreateStorySessionRequest,
        idempotency_key: str | None,
    ) -> tuple[StorySessionResponse, int]:
        request_hash = _hash_create_request(payload)
        if idempotency_key:
            existing = await self._idempotency.get(
                user_id=user.id,
                endpoint=CREATE_ENDPOINT,
                key=idempotency_key,
            )
            if existing is not None:
                if existing.request_hash != request_hash:
                    raise AppError(
                        code="idempotency_key_conflict",
                        message="This idempotency key was already used with a different request.",
                        status_code=409,
                    )
                return StorySessionResponse.model_validate(
                    existing.response_body
                ), existing.response_status

        prompt = await self._prompts.get_published_by_id(payload.prompt_id)
        if prompt is None:
            raise AppError(
                code="prompt_not_found",
                message="The requested prompt could not be found.",
                status_code=404,
            )

        timer_mode = TimerMode(payload.timer_mode.value)
        validate_timer_selection(timer_mode, payload.selected_timer_seconds)

        now = self._clock.now()
        metadata: dict[str, Any] = {}
        if payload.client_timezone:
            metadata["client_timezone"] = payload.client_timezone
        if payload.client_session_id:
            metadata["client_session_id"] = payload.client_session_id

        story_session = await self._sessions.create_session(
            user_id=user.id,
            prompt_id=payload.prompt_id,
            timer_mode=timer_mode,
            selected_timer_seconds=payload.selected_timer_seconds,
            started_at=now,
            started_metadata=metadata or None,
        )
        response = StorySessionResponse.from_orm(story_session)

        if idempotency_key:
            expires_at = now + timedelta(days=7)
            await self._idempotency.put(
                user_id=user.id,
                endpoint=CREATE_ENDPOINT,
                key=idempotency_key,
                request_hash=request_hash,
                response_status=201,
                response_body=response.model_dump(mode="json"),
                expires_at=expires_at,
            )

        return response, 201

    async def get(self, *, user: User, session_id: uuid.UUID) -> StorySessionResponse:
        story_session = await self._require_owned_session(user=user, session_id=session_id)
        story_session = await self._maybe_expire(story_session)
        return StorySessionResponse.from_orm(story_session)

    async def record_event(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        payload: StorySessionEventRequest,
    ) -> StorySessionResponse:
        story_session = await self._require_owned_session(user=user, session_id=session_id)
        story_session = await self._maybe_expire(story_session)

        event_type = StorySessionEventType(payload.event_type.value)
        if event_type not in CLIENT_EVENTS:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={"event_type": event_type.value, "status": story_session.status.value},
            )

        if event_type == StorySessionEventType.abandoned:
            return await self.abandon(user=user, session_id=session_id)

        self._assert_transition_allowed(story_session, event_type)

        now = self._clock.now()
        await self._sessions.add_event(
            story_session=story_session,
            event_type=event_type,
            occurred_at=now,
            client_occurred_at=payload.client_occurred_at,
            metadata=payload.metadata,
        )
        await self._apply_event_side_effects(story_session, event_type, now)
        story_session = await self._sessions.save(story_session)
        return StorySessionResponse.from_orm(story_session)

    async def abandon(self, *, user: User, session_id: uuid.UUID) -> StorySessionResponse:
        story_session = await self._require_owned_session(user=user, session_id=session_id)
        if story_session.status == StorySessionStatus.abandoned:
            return StorySessionResponse.from_orm(story_session)

        if story_session.status in {
            StorySessionStatus.completed,
            StorySessionStatus.expired,
        }:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={
                    "event_type": StorySessionEventTypeSchema.abandoned.value,
                    "status": story_session.status.value,
                },
            )

        now = self._clock.now()
        await self._sessions.add_event(
            story_session=story_session,
            event_type=StorySessionEventType.abandoned,
            occurred_at=now,
        )
        story_session.status = StorySessionStatus.abandoned
        story_session.abandoned_at = now
        story_session = await self._sessions.save(story_session)
        return StorySessionResponse.from_orm(story_session)

    async def _require_owned_session(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
    ) -> StorySession:
        story_session = await self._sessions.get_by_id(session_id)
        if story_session is None or story_session.user_id != user.id:
            raise AppError(
                code="session_not_found",
                message="The requested story session could not be found.",
                status_code=404,
            )
        return story_session

    async def _maybe_expire(self, story_session: StorySession) -> StorySession:
        if story_session.status in TERMINAL_STATUSES:
            return story_session
        expiry_seconds = self._settings.sketch_session_expiry_seconds
        age = self._clock.now() - story_session.started_at
        if age.total_seconds() < expiry_seconds:
            return story_session

        story_session.status = StorySessionStatus.expired
        return await self._sessions.save(story_session)

    def _assert_transition_allowed(
        self,
        story_session: StorySession,
        event_type: StorySessionEventType,
    ) -> None:
        status = story_session.status
        allowed = False
        if status == StorySessionStatus.active:
            allowed = event_type in {
                StorySessionEventType.paused,
                StorySessionEventType.timer_completed,
                StorySessionEventType.finished_early,
                StorySessionEventType.writing_started,
            }
            if event_type == StorySessionEventType.timer_completed:
                allowed = story_session.timer_mode == TimerMode.countdown
        elif status == StorySessionStatus.paused:
            allowed = event_type == StorySessionEventType.resumed
        elif status == StorySessionStatus.writing:
            allowed = event_type in {
                StorySessionEventType.draft_saved,
                StorySessionEventType.submission_created,
            }

        if not allowed:
            raise AppError(
                code="invalid_session_transition",
                message="That lifecycle event is not valid for the current session state.",
                status_code=422,
                details={"event_type": event_type.value, "status": status.value},
            )

    async def _apply_event_side_effects(
        self,
        story_session: StorySession,
        event_type: StorySessionEventType,
        now: Any,
    ) -> None:
        if event_type == StorySessionEventType.paused:
            story_session.status = StorySessionStatus.paused
            return

        if event_type == StorySessionEventType.resumed:
            paused_event = await self._sessions.get_latest_event(
                story_session_id=story_session.id,
                event_type=StorySessionEventType.paused,
            )
            if paused_event is not None:
                delta = int((now - paused_event.occurred_at).total_seconds())
                if delta > 0:
                    story_session.paused_total_seconds += delta
            story_session.status = StorySessionStatus.active
            return

        if event_type == StorySessionEventType.timer_completed:
            story_session.timer_completed_at = now
            story_session.status = StorySessionStatus.writing
            return

        if event_type == StorySessionEventType.finished_early:
            story_session.finish_requested_at = now
            story_session.status = StorySessionStatus.writing
            return

        if event_type == StorySessionEventType.writing_started:
            story_session.status = StorySessionStatus.writing
            return

        if event_type == StorySessionEventType.draft_saved:
            return

        if event_type == StorySessionEventType.submission_created:
            story_session.completed_at = now
            story_session.status = StorySessionStatus.completed


def validate_timer_selection(mode: TimerMode, seconds: int | None) -> None:
    """Validate Story Session timer mode/seconds combination."""
    if mode == TimerMode.no_timer:
        if seconds is not None:
            raise AppError(
                code="invalid_timer_selection",
                message="Timer mode and selected seconds are inconsistent.",
                status_code=422,
            )
        return
    if mode == TimerMode.countdown:
        if seconds not in ALLOWED_TIMER_SECONDS:
            raise AppError(
                code="invalid_timer_selection",
                message="Timer mode and selected seconds are inconsistent.",
                status_code=422,
            )
        return
    raise AppError(
        code="invalid_timer_selection",
        message="Timer mode and selected seconds are inconsistent.",
        status_code=422,
    )


def _hash_create_request(payload: CreateStorySessionRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
