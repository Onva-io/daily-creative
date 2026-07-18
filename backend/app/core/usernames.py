"""Username normalisation, format validation, and reserved names.

Assumption (Phase 3): usernames match ``^[A-Za-z0-9_]{3,30}$``. Specs require
case-insensitive uniqueness and reserved names but do not define the format.
"""

from __future__ import annotations

import re

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,30}$")

RESERVED_USERNAMES: frozenset[str] = frozenset(
    {
        "about",
        "admin",
        "administrator",
        "api",
        "auth",
        "dailysketch",
        "help",
        "home",
        "login",
        "logout",
        "me",
        "moderator",
        "null",
        "official",
        "profile",
        "root",
        "settings",
        "signup",
        "support",
        "system",
        "undefined",
        "users",
    }
)


def normalize_username(username: str) -> str:
    """Trim and lowercase a username for uniqueness comparisons."""
    return username.strip().lower()


def is_valid_username_format(username: str) -> bool:
    """Return True when the display username matches the Phase 3 format rule."""
    return bool(USERNAME_PATTERN.fullmatch(username.strip()))


def is_reserved_username(username: str) -> bool:
    """Return True when the normalised username is reserved."""
    return normalize_username(username) in RESERVED_USERNAMES
