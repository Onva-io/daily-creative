"""Creative Session event ORM model shared by every creative type."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class GenericSessionEvent:
    """Event names every creative type shares.

    Type-specific events (upload lifecycle, draft saves, ...) are declared by
    the creative type definition and validated against it at runtime, so the
    column is free text rather than a Postgres enum.
    """

    started = "started"
    paused = "paused"
    resumed = "resumed"
    timer_completed = "timer_completed"
    finished_early = "finished_early"
    submission_created = "submission_created"
    abandoned = "abandoned"


# Events a client may post directly. ``started`` and ``submission_created``
# are recorded server-side only.
GENERIC_CLIENT_EVENTS = frozenset(
    {
        GenericSessionEvent.paused,
        GenericSessionEvent.resumed,
        GenericSessionEvent.timer_completed,
        GenericSessionEvent.finished_early,
        GenericSessionEvent.abandoned,
    }
)


class CreativeSessionEvent(Base):
    """Append-only lifecycle event for a creative session."""

    __tablename__ = "creative_session_events"
    __table_args__ = (Index("ix_creative_session_events_session_id", "session_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
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
