"""Story creative type plugin metadata."""

from app.creative_types.registry import CreativeTypeDefinition
from app.models.enums import CreativeType

STORY_DEFINITION = CreativeTypeDefinition(
    id=CreativeType.story,
    session_table="story_sessions",
    submission_detail_table="story_submissions",
    session_expiry_setting="creative_session_expiry_seconds",
    required_submission_fields=frozenset({"body"}),
    optional_submission_fields=frozenset({"caption"}),
    cleans_up_upload_on_delete=False,
)
