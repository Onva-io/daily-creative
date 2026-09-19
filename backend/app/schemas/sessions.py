"""Creative Session API schemas (shared by every creative type)."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.creative_session import CreativeSession
from app.schemas.me import TimerModeSchema
from app.schemas.submissions import CreativeTypeSchema


class CreativeSessionStatusSchema(str, Enum):
    active = "active"
    paused = "paused"
    completed = "completed"
    abandoned = "abandoned"
    expired = "expired"


class CreateSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: CreativeTypeSchema
    prompt_id: UUID
    timer_mode: TimerModeSchema
    selected_timer_seconds: int | None = None
    client_timezone: str | None = None
    client_session_id: str | None = Field(default=None, max_length=128)
    client_started_at: datetime | None = None


class SessionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Validated against the generic vocabulary plus the creative type's
    # declared stage events, so the contract stays open for new types.
    event_type: str = Field(min_length=1, max_length=64)
    client_occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreativeSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    prompt_id: UUID
    creative_type: CreativeTypeSchema
    timer_mode: TimerModeSchema
    selected_timer_seconds: int | None
    status: CreativeSessionStatusSchema
    stage: str | None
    stage_timestamps: dict[str, datetime]
    started_at: datetime
    paused_total_seconds: int
    timer_completed_at: datetime | None
    finish_requested_at: datetime | None
    completed_at: datetime | None
    abandoned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, session: CreativeSession) -> CreativeSessionResponse:
        return cls(
            id=session.id,
            user_id=session.user_id,
            prompt_id=session.prompt_id,
            creative_type=CreativeTypeSchema(session.creative_type.value),
            timer_mode=TimerModeSchema(session.timer_mode.value),
            selected_timer_seconds=session.selected_timer_seconds,
            status=CreativeSessionStatusSchema(session.status.value),
            stage=session.stage,
            stage_timestamps={
                key: datetime.fromisoformat(value) if isinstance(value, str) else value
                for key, value in (session.stage_timestamps or {}).items()
            },
            started_at=session.started_at,
            paused_total_seconds=session.paused_total_seconds,
            timer_completed_at=session.timer_completed_at,
            finish_requested_at=session.finish_requested_at,
            completed_at=session.completed_at,
            abandoned_at=session.abandoned_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
