"""Session stages shared by image-capture creative types (sketch, photo).

The flow is: optional timer → capture/pick an image → upload → publish. The
client emits the same three stage events for every capture type, so the
rules live here once and each type's definition reuses them.
"""

from __future__ import annotations

from app.creative_types.base import StageRule

STAGE_READY_FOR_PHOTO = "ready_for_photo"
STAGE_UPLOADING = "uploading"

CAPTURE_STAGE_RULES: tuple[StageRule, ...] = (
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
)

CAPTURE_ABANDON_FORBIDDEN_STAGES: frozenset[str] = frozenset({STAGE_UPLOADING})
CAPTURE_READ_EXPIRY_EXEMPT_STAGES: frozenset[str] = frozenset(
    {STAGE_READY_FOR_PHOTO, STAGE_UPLOADING}
)
