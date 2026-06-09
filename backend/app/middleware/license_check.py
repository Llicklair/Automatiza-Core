"""Middleware que bloquea peticiones si la licencia no es válida."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

_ALLOWED_PREFIXES = (
    "/health",
    "/ready",
    "/metrics",
    "/lifecycle/",
    "/api/v1/license",
    "/api/v1/auth",
    "/docs",
    "/openapi.json",
)


class LicenseCheckMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Rutas siempre accesibles
        if any(path == p or path.startswith(p) for p in _ALLOWED_PREFIXES):
            return await call_next(request)

        if not getattr(request.app.state, "license_valid", True):
            return JSONResponse(
                {
                    "detail": "Licencia no válida. Ve a Configuración → Licencia para activarla.",
                    "type": "license_required",
                },
                status_code=402,
            )

        return await call_next(request)
