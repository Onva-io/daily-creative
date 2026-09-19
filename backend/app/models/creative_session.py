"""Creative Session ORM model shared by every creative type."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, Uuid, desc, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CreativeType, TimerMode, creative_type_sa, timer_mode_sa


class CreativeSessionStatus(str, enum.Enum):
    """Generic session lifecycle status.

    Type-specific sub-states (e.g. sketch ``ready_for_photo``/``uploading`` or
    story ``writing``) live in ``CreativeSession.stage`` and are declared by
    the creative type definition, not by this enum.
    """

    active = "active"
    paused = "paused"
    completed = "completed"
    abandoned = "abandoned"
    expired = "expired"


TERMINAL_SESSION_STATUSES = frozenset(
    {
        CreativeSessionStatus.completed,
        CreativeSessionStatus.abandoned,
        CreativeSessionStatus.expired,
    }
)


class CreativeSession(Base):
    """Authenticated creative session for one prompt and timer choice."""

    __tablename__ = "creative_sessions"
    __table_args__ = (
        Index("ix_creative_sessions_user_id_created_at", "user_id", desc("created_at")),
        Index("ix_creative_sessions_prompt_id_created_at", "prompt_id", desc("created_at")),
        Index("ix_creative_sessions_creative_type_status", "creative_type", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("daily_prompts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    creative_type: Mapped[CreativeType] = mapped_column(creative_type_sa, nullable=False)
    timer_mode: Mapped[TimerMode] = mapped_column(timer_mode_sa, nullable=False)
    selected_timer_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[CreativeSessionStatus] = mapped_column(
        Enum(CreativeSessionStatus, name="creative_session_status", native_enum=True),
        nullable=False,
        default=CreativeSessionStatus.active,
    )
    stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    stage_timestamps: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paused_total_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timer_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finish_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    abandoned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
