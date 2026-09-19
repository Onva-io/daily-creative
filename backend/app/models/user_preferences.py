"""User preferences ORM model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

__all__ = [
    "AppearancePreference",
    "UserPreferences",
]


class AppearancePreference(str, enum.Enum):
    """Preferred colour appearance."""

    system = "system"
    light = "light"
    dark = "dark"


class UserPreferences(Base):
    """Account-wide preferences shared by every app.

    Per-app preferences (timer memory, daily reminder) live in
    ``creative_type_preferences``.
    """

    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="UTC")
    appearance: Mapped[AppearancePreference] = mapped_column(
        Enum(AppearancePreference, name="appearance", native_enum=True),
        nullable=False,
        default=AppearancePreference.system,
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
