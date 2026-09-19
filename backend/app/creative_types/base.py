"""Building blocks every creative type plugs into.

A creative type contributes exactly four things to the platform:

* a request content schema (what the client sends when publishing),
* a response content schema (what feed/detail return under ``content``),
* a handful of session stages and the client events that move between them,
* a handler with four hooks: validate, project, moderation_texts, redact.

Everything else (sessions, publications, feed, moderation flow, deletion,
cleanup) is generic and never branches on the type.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

PREVIEW_MAX_LENGTH = 140


class SubmissionContentBase(BaseModel):
    """Base for the type-specific ``content`` object in a publish request.

    Subclasses must narrow ``creative_type`` to a ``Literal`` so pydantic can
    discriminate the union built by the registry.
    """

    model_config = ConfigDict(extra="forbid")

    creative_type: str
    caption: str | None = Field(default=None, max_length=280)


class ContentResponseBase(BaseModel):
    """Base for the type-specific ``content`` object in feed/detail responses."""

    model_config = ConfigDict(extra="forbid")

    creative_type: str


@dataclass(frozen=True, slots=True)
class MediaUrls:
    """Signed URLs for a publication's upload, if it has one."""

    image_url: str | None = None
    thumbnail_url: str | None = None


@dataclass(frozen=True, slots=True)
class StageRule:
    """One client event that moves a session between type-owned stages.

    ``from_stages`` may contain ``None`` to mean "an active session that has
    not entered any stage yet". Rules only apply while the generic status is
    ``active``; paused and terminal sessions reject stage events.
    """

    event: str
    from_stages: frozenset[str | None]
    to_stage: str
    timestamp_key: str | None = None


class CreativeTypeHandler(ABC):
    """Type-specific behaviour hooks called by the generic services."""

    @abstractmethod
    def validate(self, content: SubmissionContentBase) -> dict[str, Any]:
        """Validate and normalise request content.

        Returns the JSON-serialisable dict stored in ``creative_publications.content``.
        Shared fields (``caption``, ``upload_id``) are handled generically and
        must not be included. Raise ``AppError`` for invalid content.
        """

    @abstractmethod
    def project(
        self,
        *,
        content: dict[str, Any],
        media: MediaUrls,
        is_owner: bool,
        preview: bool,
    ) -> ContentResponseBase:
        """Shape stored content for a response.

        ``preview`` is true for list surfaces (feed, profile gallery) and false
        for the detail endpoint. Anything that should never reach other users
        must be filtered here.
        """

    def moderation_texts(self, *, content: dict[str, Any]) -> list[tuple[str, str]]:
        """Extra ``(context, text)`` pairs to screen at publish time.

        The caption is screened generically; return only type-specific text.
        """
        return []

    def redact(self, content: dict[str, Any]) -> dict[str, Any]:
        """Strip user-authored text from stored content (account deletion)."""
        return content

    def inspect(self, content: dict[str, Any]) -> dict[str, Any]:
        """Fields shown to moderators when inspecting a reported publication."""
        return dict(content)


def truncate_preview(text: str | None, max_length: int = PREVIEW_MAX_LENGTH) -> str | None:
    """Trim text for list surfaces; returns None for blank input."""
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= max_length:
        return stripped
    return f"{stripped[: max_length - 1]}…"
