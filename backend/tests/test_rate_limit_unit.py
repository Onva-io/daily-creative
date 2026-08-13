"""Unit tests for rate-limit client keying."""

from __future__ import annotations

from app.core.rate_limit import _client_key


def _scope(*, headers: list[tuple[bytes, bytes]], client: tuple[str, int] | None = None) -> dict:
    scope: dict[str, object] = {"type": "http", "headers": headers}
    if client is not None:
        scope["client"] = client
    return scope


def test_client_key_prefers_bearer_token_over_proxy_peer() -> None:
    scope = _scope(
        headers=[(b"authorization", b"Bearer user-one-token")],
        client=("10.0.0.1", 12345),
    )
    other = _scope(
        headers=[(b"authorization", b"Bearer user-two-token")],
        client=("10.0.0.1", 12345),
    )
    assert _client_key(scope).startswith("token:")
    assert _client_key(scope) != _client_key(other)


def test_client_key_uses_first_forwarded_hop_when_anonymous() -> None:
    scope = _scope(
        headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.1")],
        client=("10.0.0.1", 12345),
    )
    assert _client_key(scope) == "fwd:203.0.113.10"


def test_client_key_falls_back_to_socket_peer() -> None:
    scope = _scope(headers=[], client=("127.0.0.1", 9))
    assert _client_key(scope) == "ip:127.0.0.1"
