"""Shared ORM enums and SQLAlchemy enum type bindings."""

from __future__ import annotations

import enum

from sqlalchemy import Enum


class TimerMode(str, enum.Enum):
    """Remembered Sketch Session timer mode."""

    countdown = "countdown"
    no_timer = "no_timer"


class CreativeType(str, enum.Enum):
    """Creative activity type discriminator."""

    sketch = "sketch"
    story = "story"


# Single shared Postgres enum type so create_all / multiple models do not
# attempt to CREATE TYPE timer_mode more than once.
timer_mode_sa = Enum(TimerMode, name="timer_mode", native_enum=True)
creative_type_sa = Enum(CreativeType, name="creative_type", native_enum=True)
