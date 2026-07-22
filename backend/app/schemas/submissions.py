"""Submission API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, Tag

from app.models.creative_publication import CreativePublication
from app.models.daily_prompt import DailyPrompt
from app.models.enums import TimerMode
from app.models.sketch_session import SketchSession
from app.models.story_session import StorySession
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


class SketchSubmissionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: Literal["sketch"] = "sketch"
    upload_id: UUID
    caption: str | None = Field(default=None, max_length=280)


class StorySubmissionContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: Literal["story"] = "story"
    body: str = Field(min_length=1, max_length=10000)
    caption: str | None = Field(default=None, max_length=280)


SubmissionContent = Annotated[
    Union[
        Annotated[SketchSubmissionContent, Tag("sketch")],
        Annotated[StorySubmissionContent, Tag("story")],
    ],
    Field(discriminator="creative_type"),
]


class CreateSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: CreativeTypeSchema
    session_id: UUID
    content: SubmissionContent


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
    session_id: UUID
    upload_id: UUID | None
    published_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_parts(
        cls,
        *,
        publication: CreativePublication,
        user: User,
        prompt: DailyPrompt,
        sketch_session: SketchSession | None = None,
        story_session: StorySession | None = None,
        image_url: str | None = None,
        thumbnail_url: str | None = None,
        body: str | None = None,
        caption: str | None = None,
        upload_id: UUID | None = None,
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
            id=publication.id,
            creative_type=CreativeTypeSchema(publication.creative_type.value),
            caption=caption,
            body=body,
            visibility=SubmissionVisibilitySchema(publication.visibility.value),
            status=SubmissionStatusSchema(publication.status.value),
            timer_mode=timer_mode,
            timer_seconds=timer_seconds,
            like_count=publication.like_count,
            reflection_count=publication.reflection_count,
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
            session_id=publication.session_id,
            upload_id=upload_id,
            published_at=publication.published_at,
            created_at=publication.created_at,
            updated_at=publication.updated_at,
        )
