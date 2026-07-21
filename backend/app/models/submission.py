"""Submission ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CreativeType, creative_type_sa


class SubmissionVisibility(str, enum.Enum):
    """Submission visibility. Version one supports public only."""

    public = "public"


class SubmissionStatus(str, enum.Enum):
    """Submission lifecycle status."""

    processing = "processing"
    published = "published"
    hidden = "hidden"
    removed = "removed"
    deleted = "deleted"


class Submission(Base):
    """Published sketch linked to a Prompt, Sketch Session, and Upload."""

    __tablename__ = "submissions"

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
    sketch_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sketch_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    story_session_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("story_sessions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    upload_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("uploads.id", ondelete="RESTRICT"),
        nullable=True,
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[SubmissionVisibility] = mapped_column(
        Enum(SubmissionVisibility, name="submission_visibility", native_enum=True),
        nullable=False,
        default=SubmissionVisibility.public,
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status", native_enum=True),
        nullable=False,
        default=SubmissionStatus.published,
    )
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reflection_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
