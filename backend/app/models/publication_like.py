"""Publication Like ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Uuid, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PublicationLike(Base):
    """One Like by one user on one creative publication."""

    __tablename__ = "publication_likes"
    __table_args__ = (
        Index("ix_publication_likes_user_id_created_at", "user_id", desc("created_at")),
    )

    publication_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative_publications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


# Backward-compatible alias.
SubmissionLike = PublicationLike
