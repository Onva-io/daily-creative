"""Story Session event ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class StorySessionEventType(str, enum.Enum):
    """Story Session lifecycle event type."""

    started = "started"
    paused = "paused"
    resumed = "resumed"
    timer_completed = "timer_completed"
    finished_early = "finished_early"
    writing_started = "writing_started"
    draft_saved = "draft_saved"
    submission_created = "submission_created"
    abandoned = "abandoned"


class StorySessionEvent(Base):
    """Append-only lifecycle event for a Story Session."""

    __tablename__ = "story_session_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("story_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[StorySessionEventType] = mapped_column(
        Enum(StorySessionEventType, name="story_session_event_type", native_enum=True),
        nullable=False,
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    client_occurred_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
