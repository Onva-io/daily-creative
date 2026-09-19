"""Creative-type-specific user preferences ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Time, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.enums import CreativeType, TimerMode, creative_type_sa, timer_mode_sa


class CreativeTypePreferences(Base):
    """Preferences scoped to one app (creative type).

    Anything a user sets inside Daily Sketch must not leak into Daily Story.
    Only preferences that describe the account holder (timezone, appearance,
    profile) stay on ``user_preferences``.
    """

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
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notification_time_local: Mapped[time | None] = mapped_column(Time, nullable=True)
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
