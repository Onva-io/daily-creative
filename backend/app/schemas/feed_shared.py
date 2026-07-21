"""Shared feed/user prompt summary schemas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FeedUserSummary(BaseModel):
    """Compact public user projection embedded in feed items."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None


class FeedPromptSummary(BaseModel):
    """Compact Prompt projection embedded in feed items."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    prompt_date: date
    word_1: str
    word_2: str
    word_3: str
