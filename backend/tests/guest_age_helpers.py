"""Helpers for minting guest age tokens in API tests."""

from __future__ import annotations

from app.auth.guest_age import mint_guest_age_token
from app.core.settings import Settings


def guest_age_headers(settings: Settings | None = None) -> dict[str, str]:
    resolved = settings or Settings(_env_file=None)  # type: ignore[call-arg]
    token, _ = mint_guest_age_token(resolved, minimum_age=13)
    return {"X-Guest-Age-Token": token}
