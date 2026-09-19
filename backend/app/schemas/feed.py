"""Community feed API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.feed_shared import FeedPromptSummary, FeedUserSummary
from app.schemas.me import TimerModeSchema
from app.schemas.submissions import CreativeTypeSchema, SubmissionContentResponse


class FeedItem(BaseModel):
    """Feed projection for a published Submission.

    Shared fields are flat; everything type-specific lives under ``content``
    and is shaped by the creative type's response schema in preview mode.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID
    creative_type: CreativeTypeSchema
    caption_preview: str | None = None
    content: SubmissionContentResponse
    user: FeedUserSummary
    prompt: FeedPromptSummary
    timer_mode: TimerModeSchema
    timer_seconds: int | None = None
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
