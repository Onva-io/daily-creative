"""Submission API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.daily_prompt import DailyPrompt
from app.models.enums import TimerMode
from app.models.sketch_session import SketchSession
from app.models.story_session import StorySession
from app.models.submission import Submission
from app.models.user import User
from app.schemas.feed_shared import FeedPromptSummary, FeedUserSummary
from app.schemas.me import TimerModeSchema


class CreativeTypeSchema(str, Enum):
    sketch = "sketch"
    story = "story"


class SubmissionVisibilitySchema(str, Enum):
    public = "public"


class SubmissionStatusSchema(str, Enum):
    processing = "processing"
    published = "published"
    hidden = "hidden"
    removed = "removed"
    deleted = "deleted"


class CreateSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: CreativeTypeSchema
    sketch_session_id: UUID | None = None
    story_session_id: UUID | None = None
    upload_id: UUID | None = None
    body: str | None = Field(default=None, max_length=10000)
    caption: str | None = Field(default=None, max_length=280)


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    creative_type: CreativeTypeSchema
    caption: str | None
    body: str | None
    visibility: SubmissionVisibilitySchema
    status: SubmissionStatusSchema
    timer_mode: TimerModeSchema
    timer_seconds: int | None
    like_count: int
    reflection_count: int
    viewer_has_liked: bool
    is_owner: bool
    image_url: str | None
    thumbnail_url: str | None
    user: FeedUserSummary
    prompt: FeedPromptSummary
    sketch_session_id: UUID | None
    story_session_id: UUID | None
    upload_id: UUID | None
    published_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_parts(
        cls,
        *,
        submission: Submission,
        user: User,
        prompt: DailyPrompt,
        sketch_session: SketchSession | None = None,
        story_session: StorySession | None = None,
        image_url: str | None = None,
        thumbnail_url: str | None = None,
        body: str | None = None,
        is_owner: bool,
        viewer_has_liked: bool = False,
        avatar_url: str | None = None,
    ) -> SubmissionResponse:
        session = sketch_session or story_session
        if session is not None:
            timer_mode = TimerModeSchema(session.timer_mode.value)
            if session.timer_mode == TimerMode.no_timer:
                timer_seconds = None
            else:
                timer_seconds = session.selected_timer_seconds
        else:
            timer_mode = TimerModeSchema.no_timer
            timer_seconds = None

        return cls(
            id=submission.id,
            creative_type=CreativeTypeSchema(submission.creative_type.value),
            caption=submission.caption,
            body=body if body is not None else submission.body,
            visibility=SubmissionVisibilitySchema(submission.visibility.value),
            status=SubmissionStatusSchema(submission.status.value),
            timer_mode=timer_mode,
            timer_seconds=timer_seconds,
            like_count=submission.like_count,
            reflection_count=submission.reflection_count,
            viewer_has_liked=viewer_has_liked,
            is_owner=is_owner,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            user=FeedUserSummary(
                id=user.id,
                username=user.username or "",
                display_name=user.display_name,
                avatar_url=avatar_url,
            ),
            prompt=FeedPromptSummary(
                id=prompt.id,
                prompt_date=prompt.prompt_date,
                word_1=prompt.word_1,
                word_2=prompt.word_2,
                word_3=prompt.word_3,
            ),
            sketch_session_id=submission.sketch_session_id,
            story_session_id=submission.story_session_id,
            upload_id=submission.upload_id,
            published_at=submission.published_at,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
        )
