"""Daily Sketch: photograph of an off-phone drawing."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.creative_types.base import (
    ContentResponseBase,
    CreativeTypeHandler,
    MediaUrls,
    StageRule,
    SubmissionContentBase,
)
from app.creative_types.registry import CreativeTypeDefinition
from app.models.enums import CreativeType

STAGE_READY_FOR_PHOTO = "ready_for_photo"
STAGE_UPLOADING = "uploading"


class SketchSubmissionContent(SubmissionContentBase):
    creative_type: Literal["sketch"] = "sketch"
    upload_id: UUID


class SketchContentResponse(ContentResponseBase):
    creative_type: Literal["sketch"] = "sketch"
    image_url: str | None
    thumbnail_url: str | None


class SketchHandler(CreativeTypeHandler):
    def validate(self, content: SubmissionContentBase) -> dict[str, Any]:
        return {}

    def project(
        self,
        *,
        content: dict[str, Any],
        media: MediaUrls,
        is_owner: bool,
        preview: bool,
    ) -> ContentResponseBase:
        return SketchContentResponse(
            image_url=media.image_url,
            thumbnail_url=media.thumbnail_url,
        )


SKETCH_DEFINITION = CreativeTypeDefinition(
    id=CreativeType.sketch,
    content_schema=SketchSubmissionContent,
    response_schema=SketchContentResponse,
    handler=SketchHandler(),
    post_timer_stage=STAGE_READY_FOR_PHOTO,
    stage_rules=(
        StageRule(
            event="photo_step_reached",
            from_stages=frozenset({None, STAGE_READY_FOR_PHOTO}),
            to_stage=STAGE_READY_FOR_PHOTO,
            timestamp_key="photo_step_reached_at",
        ),
        StageRule(
            event="upload_started",
            from_stages=frozenset({STAGE_READY_FOR_PHOTO}),
            to_stage=STAGE_UPLOADING,
            timestamp_key="upload_started_at",
        ),
        StageRule(
            event="upload_completed",
            from_stages=frozenset({STAGE_UPLOADING}),
            to_stage=STAGE_UPLOADING,
            timestamp_key="upload_completed_at",
        ),
    ),
    abandon_forbidden_stages=frozenset({STAGE_UPLOADING}),
    read_expiry_exempt_stages=frozenset({STAGE_READY_FOR_PHOTO, STAGE_UPLOADING}),
    requires_upload=True,
)
