"""Daily Sketch: photograph of an off-phone drawing."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from app.creative_types.base import (
    ContentResponseBase,
    CreativeTypeHandler,
    MediaUrls,
    SubmissionContentBase,
)
from app.creative_types.capture import (
    CAPTURE_ABANDON_FORBIDDEN_STAGES,
    CAPTURE_READ_EXPIRY_EXEMPT_STAGES,
    CAPTURE_STAGE_RULES,
    STAGE_READY_FOR_PHOTO,
)
from app.creative_types.registry import CreativeTypeDefinition
from app.models.enums import CreativeType


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
    stage_rules=CAPTURE_STAGE_RULES,
    abandon_forbidden_stages=CAPTURE_ABANDON_FORBIDDEN_STAGES,
    read_expiry_exempt_stages=CAPTURE_READ_EXPIRY_EXEMPT_STAGES,
    requires_upload=True,
)
