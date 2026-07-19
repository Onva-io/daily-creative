"""Streak calculation helpers."""

from __future__ import annotations

from datetime import date, timedelta


def compute_current_streak(prompt_dates: list[date], *, today: date) -> int:
    """Count consecutive Prompt Dates ending today or yesterday.

    Multiple submissions on the same Prompt Date count once. An empty history
    or a gap that leaves the most recent date older than yesterday yields 0.
    """
    if not prompt_dates:
        return 0

    unique_dates = sorted(set(prompt_dates), reverse=True)
    latest = unique_dates[0]
    yesterday = today - timedelta(days=1)
    if latest not in {today, yesterday}:
        return 0

    streak = 1
    expected = latest - timedelta(days=1)
    for prompt_date in unique_dates[1:]:
        if prompt_date == expected:
            streak += 1
            expected = prompt_date - timedelta(days=1)
            continue
        break
    return streak
