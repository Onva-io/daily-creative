"""Unit tests for the submission Prompt Date window."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.core.errors import AppError
from app.services.prompts import assert_prompt_within_window
from app.services.streaks import compute_current_streak


def test_window_accepts_today_and_yesterday() -> None:
    today = date(2026, 7, 18)
    assert_prompt_within_window(today, today=today, backdate_days=1)
    assert_prompt_within_window(today - timedelta(days=1), today=today, backdate_days=1)


def test_window_rejects_two_days_old_and_future() -> None:
    today = date(2026, 7, 18)
    with pytest.raises(AppError) as older:
        assert_prompt_within_window(today - timedelta(days=2), today=today, backdate_days=1)
    assert older.value.code == "prompt_date_out_of_window"
    assert older.value.details["earliest_allowed"] == "2026-07-17"
    assert older.value.details["latest_allowed"] == "2026-07-18"

    with pytest.raises(AppError) as future:
        assert_prompt_within_window(today + timedelta(days=1), today=today, backdate_days=1)
    assert future.value.code == "prompt_date_out_of_window"


def test_window_matches_streak_boundary() -> None:
    """submission_backdate_days=1 must agree with compute_current_streak's today/yesterday bound."""
    today = date(2026, 7, 19)
    yesterday = today - timedelta(days=1)
    two_days_ago = today - timedelta(days=2)

    assert_prompt_within_window(today, today=today, backdate_days=1)
    assert_prompt_within_window(yesterday, today=today, backdate_days=1)
    with pytest.raises(AppError):
        assert_prompt_within_window(two_days_ago, today=today, backdate_days=1)

    assert compute_current_streak([today], today=today) == 1
    assert compute_current_streak([yesterday], today=today) == 1
    assert compute_current_streak([two_days_ago], today=today) == 0
