"""Sketch creative type plugin metadata."""

from app.creative_types.registry import CreativeTypeDefinition
from app.models.enums import CreativeType

SKETCH_DEFINITION = CreativeTypeDefinition(
    id=CreativeType.sketch,
    session_table="sketch_sessions",
    submission_detail_table="sketch_submissions",
    session_expiry_setting="creative_session_expiry_seconds",
    required_submission_fields=frozenset({"upload_id"}),
    optional_submission_fields=frozenset({"caption"}),
    cleans_up_upload_on_delete=True,
)
