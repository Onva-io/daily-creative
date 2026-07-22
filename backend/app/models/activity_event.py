"""Activity event ORM model for future inbox/push delivery."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Uuid, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ActivityEventType(str, enum.Enum):
    """Social activity event types recorded in version one."""

    submission_liked = "submission_liked"
    reflection_added = "reflection_added"


class ActivityEvent(Base):
    """Record of a social action for a Submission owner."""

    __tablename__ = "activity_events"
    __table_args__ = (
        Index(
            "ix_activity_events_recipient_user_id_created_at",
            "recipient_user_id",
            desc("created_at"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[ActivityEventType] = mapped_column(
        Enum(ActivityEventType, name="activity_event_type", native_enum=True),
        nullable=False,
    )
    submission_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative_publications.id", ondelete="SET NULL"),
        nullable=True,
    )
    reflection_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("reflections.id", ondelete="SET NULL"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
