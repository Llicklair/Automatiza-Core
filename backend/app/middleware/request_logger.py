"""Middleware de logging de requests con request_id y metricas."""

import logging
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.observability import record_http_request
from app.core.request_context import set_current_request_id

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

        # Propaga al ContextVar para que el StructuredFormatter, trace_llm_call
        # y cualquier código downstream (services, agents, tools) puedan leerlo
        # sin recibirlo como parámetro explícito.
        set_current_request_id(request_id)

        # scope["state"] must be a plain dict (ASGI standard).
        # Starlette's Request.state does State(scope["state"]), so if scope["state"]
        # is already a State object it creates a nested State where _state is not a
        # dict — causing "TypeError: 'State' object is not subscriptable" on every
        # attribute read (request.state.request_id, etc.).
        if "state" not in scope or not isinstance(scope["state"], dict):
            scope["state"] = {}
        scope["state"]["request_id"] = request_id

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
            if isinstance(state, dict):
                tenant_id = str(state.get("tenant_id", "-") or "-")
            elif state is not None and hasattr(state, "tenant_id"):
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
