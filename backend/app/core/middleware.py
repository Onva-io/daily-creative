"""HTTP middleware for request correlation and structured access logging."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.request_context import request_id_ctx
from app.core.settings import Settings

REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode("latin-1")

logger = logging.getLogger("app.access")


class RequestIDMiddleware:
    """Attach a request ID to every request and response.

    Implemented as pure ASGI middleware so FastAPI exception handlers can
    convert failures into responses without BaseHTTPMiddleware interference.

    Note: handlers registered for ``Exception`` run in ServerErrorMiddleware,
    which sits outside user middleware. Those handlers must set
    ``X-Request-ID`` themselves; this middleware skips duplicates.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self._settings = settings

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        incoming = headers.get("x-request-id", "").strip()
        request_id = incoming or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        state = scope.setdefault("state", {})
        if not isinstance(state, dict):
            state = {}
            scope["state"] = state
        state["request_id"] = request_id

        started = time.perf_counter()
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                raw_headers = list(message.get("headers", []))
                already_set = any(key == REQUEST_ID_HEADER_BYTES for key, _ in raw_headers)
                if not already_set:
                    raw_headers.append((REQUEST_ID_HEADER_BYTES, request_id.encode("latin-1")))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "route": scope.get("path", ""),
                    "status": 500,
                    "latency_ms": round(latency_ms, 2),
                    "environment": self._settings.app_env,
                    "release_version": self._settings.release_version,
                },
            )
            raise
        else:
            latency_ms = (time.perf_counter() - started) * 1000
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "route": scope.get("path", ""),
                    "status": status_code,
                    "latency_ms": round(latency_ms, 2),
                    "environment": self._settings.app_env,
                    "release_version": self._settings.release_version,
                },
            )
        finally:
            request_id_ctx.reset(token)
