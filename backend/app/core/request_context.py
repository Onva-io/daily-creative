"""Request-scoped context values."""

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Return the current request ID, or an empty string when unset."""
    return request_id_ctx.get()
