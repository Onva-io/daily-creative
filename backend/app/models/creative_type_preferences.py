"""Creative-type-specific user preferences ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CreativeType, TimerMode, creative_type_sa, timer_mode_sa


class CreativeTypePreferences(Base):
    """Per-creative-type preferences for timer defaults."""

    __tablename__ = "creative_type_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    creative_type: Mapped[CreativeType] = mapped_column(
        creative_type_sa,
        primary_key=True,
    )
    remember_timer_option: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remembered_timer_mode: Mapped[TimerMode | None] = mapped_column(
        timer_mode_sa,
        nullable=True,
    )
    remembered_timer_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
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
