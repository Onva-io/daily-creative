"""Unit tests for username normalisation and reserved names."""

from __future__ import annotations

from app.core.usernames import (
    is_reserved_username,
    is_valid_username_format,
    normalize_username,
)


def test_normalize_username_trims_and_lowercases() -> None:
    assert normalize_username("  Sketchy_Matt ") == "sketchy_matt"


def test_valid_username_format() -> None:
    assert is_valid_username_format("abc")
    assert is_valid_username_format("Sketchy_Matt")
    assert is_valid_username_format("a" * 30)
    assert not is_valid_username_format("ab")
    assert not is_valid_username_format("a" * 31)
    assert not is_valid_username_format("bad-name")
    assert not is_valid_username_format("has space")


def test_reserved_usernames_rejected() -> None:
    assert is_reserved_username("admin")
    assert is_reserved_username("Admin")
    assert is_reserved_username("  ME ")
    assert is_reserved_username("dailysketch")
    assert not is_reserved_username("sketchy_matt")
