"""Story Session API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.story_session import StorySession
from app.schemas.me import TimerModeSchema


class StorySessionStatusSchema(str, Enum):
    active = "active"
    paused = "paused"
    writing = "writing"
    completed = "completed"
    abandoned = "abandoned"
    expired = "expired"


class StorySessionEventTypeSchema(str, Enum):
    started = "started"
    paused = "paused"
    resumed = "resumed"
    timer_completed = "timer_completed"
    finished_early = "finished_early"
    writing_started = "writing_started"
    draft_saved = "draft_saved"
    submission_created = "submission_created"
    abandoned = "abandoned"


class CreateStorySessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_id: UUID
    timer_mode: TimerModeSchema
    selected_timer_seconds: int | None = None
    client_timezone: str | None = None
    client_session_id: str | None = Field(default=None, max_length=128)


class StorySessionEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: StorySessionEventTypeSchema
    client_occurred_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class StorySessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    user_id: UUID
    prompt_id: UUID
    timer_mode: TimerModeSchema
    selected_timer_seconds: int | None
    status: StorySessionStatusSchema
    started_at: datetime
    paused_total_seconds: int
    timer_completed_at: datetime | None
    finish_requested_at: datetime | None
    completed_at: datetime | None
    abandoned_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm(cls, session: StorySession) -> StorySessionResponse:
        return cls(
            id=session.id,
            user_id=session.user_id,
            prompt_id=session.prompt_id,
            timer_mode=TimerModeSchema(session.timer_mode.value),
            selected_timer_seconds=session.selected_timer_seconds,
            status=StorySessionStatusSchema(session.status.value),
            started_at=session.started_at,
            paused_total_seconds=session.paused_total_seconds,
            timer_completed_at=session.timer_completed_at,
            finish_requested_at=session.finish_requested_at,
            completed_at=session.completed_at,
            abandoned_at=session.abandoned_at,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )
