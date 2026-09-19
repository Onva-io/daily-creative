"""Submission API schemas.

The type-specific ``content`` unions are assembled from the creative type
registry, so adding a creative type never touches this module.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.creative_types import (
    ContentResponseBase,
    SubmissionContentBase,
    get_creative_type_registry,
)
from app.models.creative_publication import CreativePublication
from app.models.creative_session import CreativeSession
from app.models.daily_prompt import DailyPrompt
from app.models.enums import TimerMode
from app.models.user import User
from app.schemas.feed_shared import FeedPromptSummary, FeedUserSummary
from app.schemas.me import TimerModeSchema


class CreativeTypeSchema(str, Enum):
    sketch = "sketch"
    story = "story"
    photo = "photo"


class SubmissionVisibilitySchema(str, Enum):
    public = "public"


class SubmissionStatusSchema(str, Enum):
    processing = "processing"
    published = "published"
    hidden = "hidden"
    removed = "removed"
    deleted = "deleted"


if TYPE_CHECKING:
    # Static view: the common base. Runtime view: a discriminated union of
    # every registered type's schema, so pydantic validates/serialises the
    # concrete shape.
    SubmissionContent = SubmissionContentBase
    SubmissionContentResponse = ContentResponseBase
else:
    _registry = get_creative_type_registry()
    SubmissionContent = Annotated[
        Union[_registry.content_schemas()],  # noqa: UP007
        Field(discriminator="creative_type"),
    ]
    SubmissionContentResponse = Annotated[
        Union[_registry.response_schemas()],  # noqa: UP007
        Field(discriminator="creative_type"),
    ]


class CreateSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    creative_type: CreativeTypeSchema
    session_id: UUID
    prompt_id: UUID
    content: SubmissionContent


def timer_fields(session: CreativeSession | None) -> tuple[TimerModeSchema, int | None]:
    if session is None:
        return TimerModeSchema.no_timer, None
    timer_mode = TimerModeSchema(session.timer_mode.value)
    if session.timer_mode == TimerMode.no_timer:
        return timer_mode, None
    return timer_mode, session.selected_timer_seconds


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    creative_type: CreativeTypeSchema
    caption: str | None
    content: SubmissionContentResponse
    visibility: SubmissionVisibilitySchema
    status: SubmissionStatusSchema
    timer_mode: TimerModeSchema
    timer_seconds: int | None
    like_count: int
    reflection_count: int
    viewer_has_liked: bool
    is_owner: bool
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
        session: CreativeSession | None,
        content: ContentResponseBase,
        is_owner: bool,
        viewer_has_liked: bool = False,
        avatar_url: str | None = None,
    ) -> SubmissionResponse:
        timer_mode, timer_seconds = timer_fields(session)
        return cls(
            id=publication.id,
            creative_type=CreativeTypeSchema(publication.creative_type.value),
            caption=publication.caption,
            content=content,
            visibility=SubmissionVisibilitySchema(publication.visibility.value),
            status=SubmissionStatusSchema(publication.status.value),
            timer_mode=timer_mode,
            timer_seconds=timer_seconds,
            like_count=publication.like_count,
            reflection_count=publication.reflection_count,
            viewer_has_liked=viewer_has_liked,
            is_owner=is_owner,
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
            upload_id=publication.upload_id,
            published_at=publication.published_at,
            created_at=publication.created_at,
            updated_at=publication.updated_at,
        )
