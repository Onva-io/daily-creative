"""Daily Photo: a photograph taken for today's words, optionally with a place.

Location is explicit and author-controlled. The client seeds it from the
image's EXIF data or the device, the author may override it (search or pin)
and give it a title, and decides per post whether exact coordinates are
published. Nothing is derived server-side: no reverse geocoding, no
clustering, no place index. When exact sharing is off, other users only ever
see the author's own label.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from uuid import UUID

from app.core.errors import AppError
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

LOCATION_LABEL_MAX_LENGTH = 120
# Stored precision (~1 cm). Anything finer is device noise, not intent.
COORDINATE_DECIMALS = 7

LocationSource = Literal["exif", "device", "search", "pin"]


class PhotoLocationInput(BaseModel):
    """Where the photo was taken, as confirmed by the author."""

    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    label: str | None = Field(default=None, max_length=LOCATION_LABEL_MAX_LENGTH)
    # How the coordinates were obtained. Kept for audit/debugging only; never
    # returned to any client.
    source: LocationSource | None = None
    # Publish exact coordinates to other users. Off by default.
    share_exact: bool = False

    @model_validator(mode="after")
    def _coordinates_come_as_a_pair(self) -> PhotoLocationInput:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self


class PhotoSubmissionContent(SubmissionContentBase):
    creative_type: Literal["photo"] = "photo"
    upload_id: UUID
    location: PhotoLocationInput | None = None


class PhotoLocationResponse(BaseModel):
    """Location as other users see it. Coordinates are null unless the author
    opted in to exact sharing (the author always sees their own)."""

    model_config = ConfigDict(extra="forbid")

    label: str | None
    latitude: float | None
    longitude: float | None
    exact_shared: bool


class PhotoContentResponse(ContentResponseBase):
    creative_type: Literal["photo"] = "photo"
    image_url: str | None
    thumbnail_url: str | None
    location: PhotoLocationResponse | None


class PhotoHandler(CreativeTypeHandler):
    def validate(self, content: SubmissionContentBase) -> dict[str, Any]:
        assert isinstance(content, PhotoSubmissionContent)
        location = content.location
        if location is None:
            return {"location": None}

        label = (location.label or "").strip() or None
        has_coordinates = location.latitude is not None and location.longitude is not None
        if not has_coordinates and label is None:
            raise AppError(
                code="validation_error",
                message="A photo location needs coordinates, a label, or both.",
                status_code=422,
            )
        if location.share_exact and not has_coordinates:
            raise AppError(
                code="validation_error",
                message="share_exact requires coordinates.",
                status_code=422,
            )

        stored: dict[str, Any] = {
            "latitude": (
                round(location.latitude, COORDINATE_DECIMALS)
                if location.latitude is not None
                else None
            ),
            "longitude": (
                round(location.longitude, COORDINATE_DECIMALS)
                if location.longitude is not None
                else None
            ),
            "label": label,
            "source": location.source,
            "share_exact": bool(location.share_exact),
        }
        return {"location": stored}

    def project(
        self,
        *,
        content: dict[str, Any],
        media: MediaUrls,
        is_owner: bool,
        preview: bool,
    ) -> ContentResponseBase:
        raw = content.get("location")
        location: PhotoLocationResponse | None = None
        if isinstance(raw, dict):
            exact_shared = bool(raw.get("share_exact", False))
            reveal = exact_shared or is_owner
            location = PhotoLocationResponse(
                label=raw.get("label"),
                latitude=raw.get("latitude") if reveal else None,
                longitude=raw.get("longitude") if reveal else None,
                exact_shared=exact_shared,
            )
        return PhotoContentResponse(
            image_url=media.image_url,
            thumbnail_url=media.thumbnail_url,
            location=location,
        )

    def moderation_texts(self, *, content: dict[str, Any]) -> list[tuple[str, str]]:
        raw = content.get("location")
        if isinstance(raw, dict) and raw.get("label"):
            return [("photo_location_label", str(raw["label"]))]
        return []

    def redact(self, content: dict[str, Any]) -> dict[str, Any]:
        # Coordinates are personal data too; drop the whole location.
        return {**content, "location": None}

    def inspect(self, content: dict[str, Any]) -> dict[str, Any]:
        # Moderators review the author-written label, not where they were.
        raw = content.get("location")
        if not isinstance(raw, dict):
            return {"location": None}
        return {
            "location": {
                "label": raw.get("label"),
                "has_coordinates": raw.get("latitude") is not None,
                "share_exact": bool(raw.get("share_exact", False)),
            }
        }


PHOTO_DEFINITION = CreativeTypeDefinition(
    id=CreativeType.photo,
    content_schema=PhotoSubmissionContent,
    response_schema=PhotoContentResponse,
    handler=PhotoHandler(),
    post_timer_stage=STAGE_READY_FOR_PHOTO,
    stage_rules=CAPTURE_STAGE_RULES,
    abandon_forbidden_stages=CAPTURE_ABANDON_FORBIDDEN_STAGES,
    read_expiry_exempt_stages=CAPTURE_READ_EXPIRY_EXEMPT_STAGES,
    requires_upload=True,
)
