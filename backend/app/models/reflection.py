"""Reflection ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, Uuid, asc, desc, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ReflectionStatus(str, enum.Enum):
    """Reflection moderation and lifecycle status."""

    published = "published"
    hidden = "hidden"
    removed = "removed"
    deleted = "deleted"


class Reflection(Base):
    """Public short comment on a Submission."""

    __tablename__ = "reflections"
    __table_args__ = (
        Index(
            "ix_reflections_submission_id_created_at_id",
            "submission_id",
            asc("created_at"),
            asc("id"),
        ),
        Index("ix_reflections_user_id_created_at", "user_id", desc("created_at")),
        Index(
            "ix_reflections_active",
            "submission_id",
            asc("created_at"),
            asc("id"),
            postgresql_where=text("status = 'published' AND deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative_publications.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ReflectionStatus] = mapped_column(
        Enum(ReflectionStatus, name="reflection_status", native_enum=True),
        nullable=False,
        default=ReflectionStatus.published,
    )
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
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
