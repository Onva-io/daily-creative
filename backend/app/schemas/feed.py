"""Community feed API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feed_shared import FeedPromptSummary, FeedUserSummary
from app.schemas.me import TimerModeSchema
from app.schemas.submissions import CreativeTypeSchema


class FeedItem(BaseModel):
    """Forward-compatible feed projection for a published Submission."""

    model_config = ConfigDict(extra="forbid")

    id: UUID
    creative_type: CreativeTypeSchema
    image_url: str | None
    thumbnail_url: str | None
    user: FeedUserSummary
    prompt: FeedPromptSummary
    timer_mode: TimerModeSchema
    timer_seconds: int | None = None
    caption_preview: str | None = None
    body_preview: str | None = None
    word_count: int | None = None
    like_count: int = Field(ge=0)
    reflection_count: int = Field(ge=0)
    viewer_has_liked: bool
    is_owner: bool
    published_at: datetime


class RecentFeedResponse(BaseModel):
    """Cursor-paginated recent community feed page."""

    model_config = ConfigDict(extra="forbid")

    items: list[FeedItem]
    next_cursor: str | None = None
