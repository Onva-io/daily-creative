"""Creative publication anchor ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Uuid, desc, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CreativeType, creative_type_sa


class PublicationVisibility(str, enum.Enum):
    """Publication visibility. Version one supports public only."""

    public = "public"


class PublicationStatus(str, enum.Enum):
    """Publication lifecycle status."""

    processing = "processing"
    published = "published"
    hidden = "hidden"
    removed = "removed"
    deleted = "deleted"


# Backward-compatible aliases used across services and API schemas.
SubmissionVisibility = PublicationVisibility
SubmissionStatus = PublicationStatus


class CreativePublication(Base):
    """Published creative work anchor for social and feed indexing."""

    __tablename__ = "creative_publications"
    __table_args__ = (
        Index("ix_creative_publications_creative_type", "creative_type"),
        Index(
            "ix_creative_publications_user_id_published_at",
            "user_id",
            desc("published_at"),
        ),
        Index(
            "ix_creative_publications_published_at_id",
            desc("published_at"),
            desc("id"),
        ),
        Index(
            "ix_creative_publications_user_id_published_at_id",
            "user_id",
            desc("published_at"),
            desc("id"),
        ),
        Index(
            "ix_creative_publications_prompt_id_published_at_id",
            "prompt_id",
            desc("published_at"),
            desc("id"),
        ),
        Index(
            "ix_creative_publications_published_active",
            desc("published_at"),
            desc("id"),
            postgresql_where=text("status = 'published' AND deleted_at IS NULL"),
        ),
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
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    visibility: Mapped[PublicationVisibility] = mapped_column(
        Enum(PublicationVisibility, name="submission_visibility", native_enum=True),
        nullable=False,
        default=PublicationVisibility.public,
    )
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, name="submission_status", native_enum=True),
        nullable=False,
        default=PublicationStatus.published,
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


# Backward-compatible alias for incremental refactors.
Submission = CreativePublication
