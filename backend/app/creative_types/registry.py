"""Registry of supported creative types and the behaviour each contributes."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.errors import AppError
from app.creative_types.base import (
    ContentResponseBase,
    CreativeTypeHandler,
    StageRule,
    SubmissionContentBase,
)
from app.models.creative_session_event import GENERIC_CLIENT_EVENTS
from app.models.enums import CreativeType


@dataclass(frozen=True, slots=True)
class CreativeTypeDefinition:
    """Everything the platform needs to know about one creative type."""

    id: CreativeType
    content_schema: type[SubmissionContentBase]
    response_schema: type[ContentResponseBase]
    handler: CreativeTypeHandler
    # Stage entered when the timer completes or the user finishes early.
    post_timer_stage: str | None
    stage_rules: tuple[StageRule, ...] = ()
    # Stages from which the client may not abandon (e.g. mid-upload).
    abandon_forbidden_stages: frozenset[str] = frozenset()
    # Stages that do not expire on read; the cleanup job still expires them.
    read_expiry_exempt_stages: frozenset[str] = frozenset()
    # Whether publishing consumes an upload (image-based types).
    requires_upload: bool = False
    _stages: frozenset[str] = field(init=False, repr=False, default=frozenset())

    def __post_init__(self) -> None:
        stages = {rule.to_stage for rule in self.stage_rules}
        if self.post_timer_stage is not None:
            stages.add(self.post_timer_stage)
        object.__setattr__(self, "_stages", frozenset(stages))

    @property
    def stages(self) -> frozenset[str]:
        return self._stages

    @property
    def client_events(self) -> frozenset[str]:
        return GENERIC_CLIENT_EVENTS | {rule.event for rule in self.stage_rules}

    def rule_for(self, event: str) -> StageRule | None:
        for rule in self.stage_rules:
            if rule.event == event:
                return rule
        return None


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

    def content_schemas(self) -> tuple[type[SubmissionContentBase], ...]:
        return tuple(definition.content_schema for definition in self._definitions.values())

    def response_schemas(self) -> tuple[type[ContentResponseBase], ...]:
        return tuple(definition.response_schema for definition in self._definitions.values())


def _build_registry() -> CreativeTypeRegistry:
    # Adding a creative type: add its module here and its enum value in
    # app.models.enums.CreativeType (plus the one-line enum migration).
    from app.creative_types.photo import PHOTO_DEFINITION
    from app.creative_types.sketch import SKETCH_DEFINITION
    from app.creative_types.story import STORY_DEFINITION

    definitions = (SKETCH_DEFINITION, STORY_DEFINITION, PHOTO_DEFINITION)
    return CreativeTypeRegistry({definition.id: definition for definition in definitions})


_REGISTRY: CreativeTypeRegistry | None = None


def get_creative_type_registry() -> CreativeTypeRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = _build_registry()
    return _REGISTRY
