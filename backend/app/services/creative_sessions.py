"""Creative Session application service shared by every creative type.

The generic lifecycle (start, pause, resume, timer complete, finish early,
abandon, expire) lives here once. Type-specific sub-states are ``stage``
values declared by the creative type definition, and the only type-specific
input this service reads is that definition.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.clock import Clock
from app.core.errors import AppError
from app.core.settings import Settings, get_settings
from app.creative_types import CreativeTypeDefinition, get_creative_type_registry
from app.models.creative_session import (
    TERMINAL_SESSION_STATUSES,
    CreativeSession,
    CreativeSessionStatus,
)
from app.models.creative_session_event import GenericSessionEvent
from app.models.enums import CreativeType, TimerMode
from app.models.user import User
from app.repositories.creative_sessions import CreativeSessionRepository
from app.repositories.idempotency import IdempotencyRepository
from app.repositories.prompts import PromptRepository
from app.schemas.sessions import (
    CreateSessionRequest,
    CreativeSessionResponse,
    SessionEventRequest,
)
from app.services.preferences import ALLOWED_TIMER_SECONDS
from app.services.prompts import assert_prompt_within_window

CREATE_ENDPOINT = "POST /api/v1/sessions"


class CreativeSessionService:
    def __init__(
        self,
        session: AsyncSession,
        clock: Clock,
        settings: Settings | None = None,
    ) -> None:
        self._sessions = CreativeSessionRepository(session)
        self._prompts = PromptRepository(session)
        self._idempotency = IdempotencyRepository(session)
        self._clock = clock
        self._settings = settings or get_settings()
        self._registry = get_creative_type_registry()

    async def create(
        self,
        *,
        user: User,
        payload: CreateSessionRequest,
        idempotency_key: str | None,
    ) -> tuple[CreativeSessionResponse, int]:
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
                return (
                    CreativeSessionResponse.model_validate(existing.response_body),
                    existing.response_status,
                )

        creative_type = CreativeType(payload.creative_type.value)
        self._registry.get(creative_type)

        prompt = await self._prompts.get_published_by_id(payload.prompt_id)
        if prompt is None:
            raise AppError(
                code="prompt_not_found",
                message="The requested prompt could not be found.",
                status_code=404,
            )
        assert_prompt_within_window(
            prompt.prompt_date,
            today=self._clock.today(),
            backdate_days=self._settings.submission_backdate_days,
        )

        timer_mode = TimerMode(payload.timer_mode.value)
        validate_timer_selection(timer_mode, payload.selected_timer_seconds)

        now = self._clock.now()
        metadata: dict[str, Any] = {}
        if payload.client_timezone:
            metadata["client_timezone"] = payload.client_timezone
        if payload.client_session_id:
            metadata["client_session_id"] = payload.client_session_id
        if payload.client_started_at is not None:
            metadata["client_started_at"] = payload.client_started_at.isoformat()

        creative_session = await self._sessions.create_session(
            user_id=user.id,
            prompt_id=payload.prompt_id,
            creative_type=creative_type,
            timer_mode=timer_mode,
            selected_timer_seconds=payload.selected_timer_seconds,
            started_at=now,
            started_metadata=metadata or None,
        )
        response = CreativeSessionResponse.from_orm(creative_session)

        if idempotency_key:
            await self._idempotency.put(
                user_id=user.id,
                endpoint=CREATE_ENDPOINT,
                key=idempotency_key,
                request_hash=request_hash,
                response_status=201,
                response_body=response.model_dump(mode="json"),
                expires_at=now + timedelta(days=7),
            )

        return response, 201

    async def get(self, *, user: User, session_id: uuid.UUID) -> CreativeSessionResponse:
        creative_session = await self._require_owned_session(user=user, session_id=session_id)
        creative_session = await self._maybe_expire(creative_session)
        return CreativeSessionResponse.from_orm(creative_session)

    async def record_event(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
        payload: SessionEventRequest,
    ) -> CreativeSessionResponse:
        creative_session = await self._require_owned_session(user=user, session_id=session_id)
        creative_session = await self._maybe_expire(creative_session)
        definition = self._registry.get(creative_session.creative_type)

        event_type = payload.event_type
        if event_type not in definition.client_events:
            raise _invalid_transition(event_type, creative_session)

        if event_type == GenericSessionEvent.abandoned:
            return await self.abandon(user=user, session_id=session_id)

        now = self._clock.now()
        self._assert_transition_allowed(definition, creative_session, event_type)
        await self._sessions.add_event(
            creative_session=creative_session,
            event_type=event_type,
            occurred_at=now,
            client_occurred_at=payload.client_occurred_at,
            metadata=payload.metadata,
        )
        await self._apply_event(definition, creative_session, event_type, now)
        creative_session = await self._sessions.save(creative_session)
        return CreativeSessionResponse.from_orm(creative_session)

    async def abandon(self, *, user: User, session_id: uuid.UUID) -> CreativeSessionResponse:
        creative_session = await self._require_owned_session(user=user, session_id=session_id)
        if creative_session.status == CreativeSessionStatus.abandoned:
            return CreativeSessionResponse.from_orm(creative_session)

        definition = self._registry.get(creative_session.creative_type)
        if creative_session.status in {
            CreativeSessionStatus.completed,
            CreativeSessionStatus.expired,
        } or (
            creative_session.stage is not None
            and creative_session.stage in definition.abandon_forbidden_stages
        ):
            raise _invalid_transition(GenericSessionEvent.abandoned, creative_session)

        now = self._clock.now()
        await self._sessions.add_event(
            creative_session=creative_session,
            event_type=GenericSessionEvent.abandoned,
            occurred_at=now,
        )
        creative_session.status = CreativeSessionStatus.abandoned
        creative_session.abandoned_at = now
        creative_session = await self._sessions.save(creative_session)
        return CreativeSessionResponse.from_orm(creative_session)

    async def complete_for_publication(
        self,
        creative_session: CreativeSession,
        *,
        now: datetime,
    ) -> None:
        """Mark a session completed after its publication is created (no commit)."""
        await self._sessions.add_event(
            creative_session=creative_session,
            event_type=GenericSessionEvent.submission_created,
            occurred_at=now,
        )
        creative_session.status = CreativeSessionStatus.completed
        creative_session.completed_at = now
        await self._sessions.save(creative_session, commit=False)

    async def _require_owned_session(
        self,
        *,
        user: User,
        session_id: uuid.UUID,
    ) -> CreativeSession:
        creative_session = await self._sessions.get_by_id(session_id)
        if creative_session is None or creative_session.user_id != user.id:
            raise AppError(
                code="session_not_found",
                message="The requested session could not be found.",
                status_code=404,
            )
        return creative_session

    async def _maybe_expire(self, creative_session: CreativeSession) -> CreativeSession:
        if creative_session.status in TERMINAL_SESSION_STATUSES:
            return creative_session
        definition = self._registry.get(creative_session.creative_type)
        if (
            creative_session.stage is not None
            and creative_session.stage in definition.read_expiry_exempt_stages
        ):
            return creative_session
        expiry_seconds = self._settings.creative_session_expiry_seconds
        age = self._clock.now() - creative_session.started_at
        if age.total_seconds() < expiry_seconds:
            return creative_session

        creative_session.status = CreativeSessionStatus.expired
        return await self._sessions.save(creative_session)

    def _assert_transition_allowed(
        self,
        definition: CreativeTypeDefinition,
        creative_session: CreativeSession,
        event_type: str,
    ) -> None:
        status = creative_session.status
        stage = creative_session.stage
        allowed = False

        if status == CreativeSessionStatus.paused:
            allowed = event_type == GenericSessionEvent.resumed
        elif status == CreativeSessionStatus.active:
            if stage is None and event_type == GenericSessionEvent.paused:
                allowed = True
            elif stage is None and event_type == GenericSessionEvent.timer_completed:
                allowed = creative_session.timer_mode == TimerMode.countdown
            elif stage is None and event_type == GenericSessionEvent.finished_early:
                allowed = True
            else:
                rule = definition.rule_for(event_type)
                allowed = rule is not None and stage in rule.from_stages

        if not allowed:
            raise _invalid_transition(event_type, creative_session)

    async def _apply_event(
        self,
        definition: CreativeTypeDefinition,
        creative_session: CreativeSession,
        event_type: str,
        now: datetime,
    ) -> None:
        if event_type == GenericSessionEvent.paused:
            creative_session.status = CreativeSessionStatus.paused
            return

        if event_type == GenericSessionEvent.resumed:
            paused_event = await self._sessions.get_latest_event(
                session_id=creative_session.id,
                event_type=GenericSessionEvent.paused,
            )
            if paused_event is not None:
                delta = int((now - paused_event.occurred_at).total_seconds())
                if delta > 0:
                    creative_session.paused_total_seconds += delta
            creative_session.status = CreativeSessionStatus.active
            return

        if event_type == GenericSessionEvent.timer_completed:
            creative_session.timer_completed_at = now
            creative_session.stage = definition.post_timer_stage
            return

        if event_type == GenericSessionEvent.finished_early:
            creative_session.finish_requested_at = now
            creative_session.stage = definition.post_timer_stage
            return

        rule = definition.rule_for(event_type)
        if rule is None:
            return
        creative_session.stage = rule.to_stage
        if rule.timestamp_key is not None:
            timestamps = dict(creative_session.stage_timestamps or {})
            timestamps[rule.timestamp_key] = now.isoformat()
            creative_session.stage_timestamps = timestamps
            flag_modified(creative_session, "stage_timestamps")


def _invalid_transition(event_type: str, creative_session: CreativeSession) -> AppError:
    details: dict[str, Any] = {
        "event_type": event_type,
        "status": creative_session.status.value,
    }
    if creative_session.stage is not None:
        details["stage"] = creative_session.stage
    return AppError(
        code="invalid_session_transition",
        message="That lifecycle event is not valid for the current session state.",
        status_code=422,
        details=details,
    )


def validate_timer_selection(mode: TimerMode, seconds: int | None) -> None:
    """Validate creative session timer mode/seconds combination."""
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


def _hash_create_request(payload: CreateSessionRequest) -> str:
    canonical = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
