"""Injectable clock abstraction for authoritative server time."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Protocol


class Clock(Protocol):
    """Clock used for Prompt Date, sessions, uploads, streaks, and tests."""

    def now(self) -> datetime:
        """Return the current UTC instant."""
        ...

    def today(self) -> date:
        """Return the current UTC calendar date (Prompt Date boundary)."""
        ...


class SystemClock:
    """Production clock backed by the system UTC clock."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()


def get_clock() -> Clock:
    """FastAPI dependency that returns the system clock."""
    return SystemClock()
