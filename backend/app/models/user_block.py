"""User block ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class UserBlock(Base):
    """Private blocker → blocked relationship."""

    __tablename__ = "user_blocks"
    __table_args__ = (
        CheckConstraint(
            "blocker_user_id <> blocked_user_id",
            name="not_self",
        ),
        Index("ix_user_blocks_blocker_user_id", "blocker_user_id"),
        Index("ix_user_blocks_blocked_user_id", "blocked_user_id"),
    )

    blocker_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    blocked_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
