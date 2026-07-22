"""Registry of supported creative types and their platform metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.errors import AppError
from app.models.enums import CreativeType

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class CreativeTypeDefinition:
    """Platform metadata for one creative type."""

    id: CreativeType
    session_table: str
    submission_detail_table: str
    session_expiry_setting: str
    required_submission_fields: frozenset[str]
    optional_submission_fields: frozenset[str]
    cleans_up_upload_on_delete: bool


class CreativeTypeRegistry:
    """Lookup table for creative type behaviour."""

    def __init__(self, definitions: dict[CreativeType, CreativeTypeDefinition]) -> None:
        self._definitions = definitions

    def get(self, creative_type: CreativeType) -> CreativeTypeDefinition:
        try:
            return self._definitions[creative_type]
        except KeyError as exc:
            raise AppError(
                code="validation_error",
                message="Unsupported creative type.",
                status_code=422,
            ) from exc

    def all(self) -> tuple[CreativeTypeDefinition, ...]:
        return tuple(self._definitions.values())

    def ids(self) -> frozenset[CreativeType]:
        return frozenset(self._definitions.keys())


def _build_registry() -> CreativeTypeRegistry:
    from app.creative_types.sketch import SKETCH_DEFINITION
    from app.creative_types.story import STORY_DEFINITION

    return CreativeTypeRegistry(
        {
            CreativeType.sketch: SKETCH_DEFINITION,
            CreativeType.story: STORY_DEFINITION,
        }
    )


_REGISTRY: CreativeTypeRegistry | None = None


def get_creative_type_registry() -> CreativeTypeRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY
