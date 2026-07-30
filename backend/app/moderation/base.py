"""Provider-agnostic content moderation adapter."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.core.settings import Settings, get_settings


class ModerationTier(str, Enum):
    """Tiered outcome for automated content screening."""

    allow = "allow"
    queue = "queue"
    block = "block"


@dataclass(frozen=True, slots=True)
class ModerationResult:
    """Outcome of screening a single piece of content."""

    tier: ModerationTier
    confidence: float
    categories: tuple[str, ...]
    provider: str
    provider_response: str | None = None


class ModerationAdapter(Protocol):
    """Screens text and images for objectionable material."""

    async def screen_text(self, *, text: str, context: str) -> ModerationResult:
        """Screen free-form text (captions, reflections, bios, usernames)."""
        ...

    async def screen_image(self, *, data: bytes, content_type: str) -> ModerationResult:
        """Screen image bytes before or during upload processing."""
        ...


# Conservative wordlist for offline / local / CI hermetic screening.
_BLOCK_TERMS = frozenset(
    {
        "childporn",
        "child_porn",
        "csam",
        "nigger",
        "faggot",
        "kill yourself",
        "kys",
    }
)
_QUEUE_TERMS = frozenset(
    {
        "porn",
        "nude",
        "nudes",
        "sex",
        "fuck",
        "shit",
        "bitch",
        "asshole",
        "rape",
        "suicide",
        "self-harm",
        "selfharm",
    }
)


class HeuristicModerationAdapter:
    """Offline keyword heuristic used for local/CI and as a safe default."""

    provider_name = "heuristic"

    async def screen_text(self, *, text: str, context: str) -> ModerationResult:
        lowered = " ".join(text.lower().split())
        if not lowered:
            return ModerationResult(
                tier=ModerationTier.allow,
                confidence=0.0,
                categories=(),
                provider=self.provider_name,
            )
        for term in _BLOCK_TERMS:
            if term in lowered:
                return ModerationResult(
                    tier=ModerationTier.block,
                    confidence=0.99,
                    categories=("prohibited",),
                    provider=self.provider_name,
                    provider_response=f"matched_block:{term};context={context}",
                )
        matched_queue = [term for term in _QUEUE_TERMS if term in lowered]
        if matched_queue:
            return ModerationResult(
                tier=ModerationTier.queue,
                confidence=0.7,
                categories=("profanity_or_sensitive",),
                provider=self.provider_name,
                provider_response=f"matched_queue:{','.join(matched_queue)};context={context}",
            )
        return ModerationResult(
            tier=ModerationTier.allow,
            confidence=0.05,
            categories=(),
            provider=self.provider_name,
        )

    async def screen_image(self, *, data: bytes, content_type: str) -> ModerationResult:
        # Offline default: allow images (technical validation still applies).
        # Production deployments should configure a third-party provider.
        _ = (data, content_type)
        return ModerationResult(
            tier=ModerationTier.allow,
            confidence=0.0,
            categories=(),
            provider=self.provider_name,
            provider_response="noop_image",
        )


def get_moderation_adapter(settings: Settings | None = None) -> ModerationAdapter:
    """Return the configured moderation adapter (heuristic by default)."""
    cfg = settings or get_settings()
    provider = (cfg.moderation_provider or "heuristic").lower()
    if provider == "heuristic":
        return HeuristicModerationAdapter()
    # Unknown providers fall back to hermetic heuristic so misconfig never bypasses screening.
    return HeuristicModerationAdapter()
