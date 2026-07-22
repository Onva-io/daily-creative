"""Unit tests for timer preference validation and profile completion guard."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from app.core.errors import AppError
from app.models.user import User, UserStatus
from app.models.enums import TimerMode
from app.services.preferences import validate_timer_preference
from app.services.profile import ProfileService


def test_countdown_requires_allowed_seconds() -> None:
    validate_timer_preference(TimerMode.countdown, 60)
    validate_timer_preference(TimerMode.countdown, 180)
    validate_timer_preference(TimerMode.countdown, 300)
    validate_timer_preference(TimerMode.countdown, 600)
    with pytest.raises(AppError) as exc:
        validate_timer_preference(TimerMode.countdown, 120)
    assert exc.value.code == "invalid_timer_preference"
    with pytest.raises(AppError) as exc:
        validate_timer_preference(TimerMode.countdown, None)
    assert exc.value.code == "invalid_timer_preference"


def test_no_timer_requires_null_seconds() -> None:
    validate_timer_preference(TimerMode.no_timer, None)
    with pytest.raises(AppError) as exc:
        validate_timer_preference(TimerMode.no_timer, 300)
    assert exc.value.code == "invalid_timer_preference"


def test_cleared_timer_preference_allowed() -> None:
    validate_timer_preference(None, None)


def test_require_complete_profile_rejects_incomplete() -> None:
    user = User(
        id=uuid.uuid4(),
        descope_subject="descope|incomplete",
        display_name="New sketcher",
        status=UserStatus.incomplete,
        profile_completed_at=None,
    )
    with pytest.raises(AppError) as exc:
        ProfileService.require_complete_profile(user)
    assert exc.value.code == "profile_incomplete"
    assert exc.value.status_code == 403


def test_require_complete_profile_allows_active_complete() -> None:
    user = User(
        id=uuid.uuid4(),
        descope_subject="descope|active",
        display_name="Matt",
        username="matt",
        status=UserStatus.active,
        profile_completed_at=datetime.now(timezone.utc),
    )
    ProfileService.require_complete_profile(user)
