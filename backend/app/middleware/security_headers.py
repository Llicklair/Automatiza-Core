"""Middleware that adds security headers to every HTTP response."""

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import settings


class SecurityHeadersMiddleware:
    """Pure-ASGI middleware -- adds security headers without buffering the response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.append("X-Content-Type-Options", "nosniff")
                headers.append("X-Frame-Options", "DENY")
                headers.append("X-XSS-Protection", "1; mode=block")
                headers.append("Referrer-Policy", "strict-origin-when-cross-origin")
                if settings.ENVIRONMENT == "production":
                    headers.append(
                        "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)
