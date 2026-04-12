"""Middleware de logging de requests con request_id y metricas."""

import logging
import time
import uuid

from starlette.datastructures import MutableHeaders, State
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.observability import record_http_request

logger = logging.getLogger(__name__)

_SKIP_METRICS_PATHS = frozenset(("/health", "/", "/metrics", "/docs", "/openapi.json", "/ready"))


class RequestLoggerMiddleware:
    """Pure-ASGI middleware — adds X-Request-ID and logs requests without buffering."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())

        # Seed scope["state"] so request.state.request_id is accessible in route handlers
        if "state" not in scope or not isinstance(scope["state"], State):
            scope["state"] = State()
        scope["state"].request_id = request_id  # type: ignore[attr-defined]

        t0 = time.perf_counter()
        status_code = 500

        async def send_wrapper(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers.append("X-Request-ID", request_id)
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_s = time.perf_counter() - t0
        duration_ms = round(duration_s * 1000, 1)
        path: str = scope.get("path", "")
        method: str = scope.get("method", "")

        if path not in _SKIP_METRICS_PATHS:
            record_http_request(method, path, status_code, duration_s)

            tenant_id = "-"
            state = scope.get("state")
            if state is not None and hasattr(state, "tenant_id"):
                tenant_id = str(state.tenant_id)

            logger.info(
                "req=%s method=%s path=%s status=%d duration_ms=%.1f tenant=%s",
                request_id[:8],
                method,
                path,
                status_code,
                duration_ms,
                tenant_id,
            )
