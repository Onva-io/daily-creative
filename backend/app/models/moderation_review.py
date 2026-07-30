"""Operator review queue for medium-confidence automated moderation hits."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String, Text, Uuid, desc, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.report import ReportTargetType


class ModerationReviewStatus(str, enum.Enum):
    """Lifecycle for an automated-filter review queue item."""

    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class ModerationReviewItem(Base):
    """Content flagged at medium confidence pending operator triage."""

    __tablename__ = "moderation_review_items"
    __table_args__ = (
        Index("ix_moderation_review_items_status_created", "status", desc("created_at")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[ReportTargetType] = mapped_column(
        Enum(ReportTargetType, name="report_target_type", native_enum=True, create_type=False),
        nullable=False,
    )
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ModerationReviewStatus] = mapped_column(
        Enum(ModerationReviewStatus, name="moderation_review_status", native_enum=True),
        nullable=False,
        default=ModerationReviewStatus.open,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    categories: Mapped[str] = mapped_column(Text, nullable=False, default="")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
