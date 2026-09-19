"""Daily Story: a short piece of writing typed in the app."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from app.core.errors import AppError
from app.creative_types.base import (
    ContentResponseBase,
    CreativeTypeHandler,
    MediaUrls,
    StageRule,
    SubmissionContentBase,
    truncate_preview,
)
from app.creative_types.registry import CreativeTypeDefinition
from app.models.enums import CreativeType

STAGE_WRITING = "writing"
REDACTED_BODY = ""


class StorySubmissionContent(SubmissionContentBase):
    creative_type: Literal["story"] = "story"
    body: str = Field(min_length=1, max_length=10000)


class StoryContentResponse(ContentResponseBase):
    creative_type: Literal["story"] = "story"
    # Full body on detail; None on list surfaces where body_preview is used.
    body: str | None
    body_preview: str | None
    word_count: int


class StoryHandler(CreativeTypeHandler):
    def validate(self, content: SubmissionContentBase) -> dict[str, Any]:
        assert isinstance(content, StorySubmissionContent)
        body = content.body.strip()
        if not body:
            raise AppError(
                code="validation_error",
                message="body is required for story submissions.",
                status_code=422,
            )
        return {"body": body}

    def project(
        self,
        *,
        content: dict[str, Any],
        media: MediaUrls,
        is_owner: bool,
        preview: bool,
    ) -> ContentResponseBase:
        body = str(content.get("body", ""))
        return StoryContentResponse(
            body=None if preview else body,
            body_preview=truncate_preview(body),
            word_count=len(body.split()),
        )

    def moderation_texts(self, *, content: dict[str, Any]) -> list[tuple[str, str]]:
        return [("story_body", str(content.get("body", "")))]

    def redact(self, content: dict[str, Any]) -> dict[str, Any]:
        return {**content, "body": REDACTED_BODY}


STORY_DEFINITION = CreativeTypeDefinition(
    id=CreativeType.story,
    content_schema=StorySubmissionContent,
    response_schema=StoryContentResponse,
    handler=StoryHandler(),
    post_timer_stage=STAGE_WRITING,
    stage_rules=(
        # Clients emit this after `finished_early`/`timer_completed` already moved
        # the session into the writing stage, so the transition is idempotent.
        StageRule(
            event="writing_started",
            from_stages=frozenset({None, STAGE_WRITING}),
            to_stage=STAGE_WRITING,
        ),
        StageRule(
            event="draft_saved",
            from_stages=frozenset({STAGE_WRITING}),
            to_stage=STAGE_WRITING,
        ),
    ),
)
