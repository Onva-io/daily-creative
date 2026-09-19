"""Unit tests for the photo creative type handler (no database)."""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.creative_types import MediaUrls, get_creative_type_registry
from app.creative_types.photo import (
    PHOTO_DEFINITION,
    PhotoContentResponse,
    PhotoHandler,
    PhotoLocationInput,
    PhotoSubmissionContent,
)
from app.models.enums import CreativeType

MEDIA = MediaUrls(image_url="https://cdn.test/display", thumbnail_url="https://cdn.test/thumb")


def _content(**location: object) -> PhotoSubmissionContent:
    return PhotoSubmissionContent(
        upload_id=uuid.uuid4(),
        location=PhotoLocationInput(**location) if location else None,
    )


def test_photo_is_registered_with_capture_stages() -> None:
    registry = get_creative_type_registry()
    definition = registry.get(CreativeType.photo)
    assert definition is PHOTO_DEFINITION
    assert definition.requires_upload is True
    assert definition.post_timer_stage == "ready_for_photo"
    assert {"photo_step_reached", "upload_started", "upload_completed"} <= definition.client_events
    # Same flow as sketch so the shared capture client can drive both.
    sketch = registry.get(CreativeType.sketch)
    assert definition.stage_rules == sketch.stage_rules


def test_validate_without_location_stores_null() -> None:
    assert PhotoHandler().validate(_content()) == {"location": None}


def test_validate_normalises_label_and_rounds_coordinates() -> None:
    stored = PhotoHandler().validate(
        _content(
            latitude=50.82253012345678,
            longitude=-0.13716398765432,
            label="  Brighton seafront  ",
            source="exif",
            share_exact=True,
        )
    )
    assert stored == {
        "location": {
            "latitude": 50.8225301,
            "longitude": -0.137164,
            "label": "Brighton seafront",
            "source": "exif",
            "share_exact": True,
        }
    }


def test_validate_allows_label_only_location() -> None:
    stored = PhotoHandler().validate(_content(label="Kitchen table"))
    assert stored["location"]["latitude"] is None
    assert stored["location"]["longitude"] is None
    assert stored["location"]["label"] == "Kitchen table"
    assert stored["location"]["share_exact"] is False


def test_validate_rejects_empty_location() -> None:
    with pytest.raises(AppError) as excinfo:
        PhotoHandler().validate(_content(label="   "))
    assert excinfo.value.status_code == 422


def test_validate_rejects_share_exact_without_coordinates() -> None:
    with pytest.raises(AppError) as excinfo:
        PhotoHandler().validate(_content(label="Somewhere", share_exact=True))
    assert excinfo.value.status_code == 422


def test_schema_rejects_half_a_coordinate_pair_and_out_of_range() -> None:
    with pytest.raises(ValidationError):
        PhotoLocationInput(latitude=10.0)
    with pytest.raises(ValidationError):
        PhotoLocationInput(latitude=91.0, longitude=0.0)
    with pytest.raises(ValidationError):
        PhotoLocationInput(latitude=0.0, longitude=181.0)
    with pytest.raises(ValidationError):
        PhotoLocationInput(label="x" * 121)


STORED_PRIVATE = {
    "location": {
        "latitude": 50.8225301,
        "longitude": -0.137164,
        "label": "Brighton seafront",
        "source": "device",
        "share_exact": False,
    }
}


@pytest.mark.parametrize("preview", [True, False])
def test_project_hides_coordinates_from_other_users_when_not_shared(preview: bool) -> None:
    projected = PhotoHandler().project(
        content=STORED_PRIVATE, media=MEDIA, is_owner=False, preview=preview
    )
    assert isinstance(projected, PhotoContentResponse)
    assert projected.image_url == MEDIA.image_url
    assert projected.location is not None
    assert projected.location.label == "Brighton seafront"
    assert projected.location.latitude is None
    assert projected.location.longitude is None
    assert projected.location.exact_shared is False
    # Source never leaves the server.
    assert "source" not in projected.model_dump()["location"]


def test_project_reveals_coordinates_to_the_author() -> None:
    projected = PhotoHandler().project(
        content=STORED_PRIVATE, media=MEDIA, is_owner=True, preview=True
    )
    assert isinstance(projected, PhotoContentResponse)
    assert projected.location is not None
    assert projected.location.latitude == 50.8225301
    assert projected.location.longitude == -0.137164
    assert projected.location.exact_shared is False


def test_project_reveals_coordinates_when_author_opted_in() -> None:
    stored = {"location": {**STORED_PRIVATE["location"], "share_exact": True}}
    projected = PhotoHandler().project(content=stored, media=MEDIA, is_owner=False, preview=True)
    assert isinstance(projected, PhotoContentResponse)
    assert projected.location is not None
    assert projected.location.latitude == 50.8225301
    assert projected.location.exact_shared is True


def test_project_without_location() -> None:
    projected = PhotoHandler().project(
        content={"location": None}, media=MEDIA, is_owner=False, preview=False
    )
    assert isinstance(projected, PhotoContentResponse)
    assert projected.location is None


def test_moderation_screens_only_the_label() -> None:
    assert PhotoHandler().moderation_texts(content=STORED_PRIVATE) == [
        ("photo_location_label", "Brighton seafront")
    ]
    assert PhotoHandler().moderation_texts(content={"location": None}) == []
    unlabelled = {"location": {**STORED_PRIVATE["location"], "label": None}}
    assert PhotoHandler().moderation_texts(content=unlabelled) == []


def test_redact_drops_the_whole_location() -> None:
    assert PhotoHandler().redact(STORED_PRIVATE) == {"location": None}


def test_inspect_shows_label_but_not_coordinates() -> None:
    inspected = PhotoHandler().inspect(STORED_PRIVATE)
    assert inspected == {
        "location": {"label": "Brighton seafront", "has_coordinates": True, "share_exact": False}
    }
    assert PhotoHandler().inspect({"location": None}) == {"location": None}
