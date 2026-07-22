"""Sketch submission detail ORM model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class SketchSubmission(Base):
    """Typed sketch publication payload linked 1:1 to a creative publication."""

    __tablename__ = "sketch_submissions"

    publication_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("creative_publications.id", ondelete="CASCADE"),
        primary_key=True,
    )
    sketch_session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sketch_sessions.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("uploads.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
