"""Unit tests for streak calculation."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.streaks import compute_current_streak


def test_streak_empty() -> None:
    assert compute_current_streak([], today=date(2026, 7, 19)) == 0


def test_streak_ends_today() -> None:
    today = date(2026, 7, 19)
    dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
    assert compute_current_streak(dates, today=today) == 3


def test_streak_ends_yesterday() -> None:
    today = date(2026, 7, 19)
    dates = [today - timedelta(days=1), today - timedelta(days=2)]
    assert compute_current_streak(dates, today=today) == 2


def test_streak_broken_gap() -> None:
    today = date(2026, 7, 19)
    dates = [today, today - timedelta(days=2)]
    assert compute_current_streak(dates, today=today) == 1


def test_streak_multiple_same_day_counts_once() -> None:
    today = date(2026, 7, 19)
    dates = [today, today, today - timedelta(days=1), today - timedelta(days=1)]
    assert compute_current_streak(dates, today=today) == 2


def test_streak_too_old_is_zero() -> None:
    today = date(2026, 7, 19)
    dates = [today - timedelta(days=3), today - timedelta(days=4)]
    assert compute_current_streak(dates, today=today) == 0
