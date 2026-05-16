"""
Scanner Auth — Middleware para tokens de escáner móvil.

Los tokens de escáner son JWTs de corta vida (2 min) con scope restringido.
Solo permiten acceso a inventario y albaranes — nunca a facturación, RRHH, etc.
"""

import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)

# Rutas protegidas que el scanner tiene permitido acceder
_ALLOWED_PREFIXES = (
    "/api/v1/scanner/",
    "/api/v1/products",
    "/api/v1/albaranes",
)

# Rutas explícitamente bloqueadas para tokens de scanner
_BLOCKED_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/admin",
    "/api/v1/hr",
    "/api/v1/banking",
    "/api/v1/accounting",
    "/api/v1/tenant",
    "/api/v1/recruitment",
)


def create_scanner_token(tenant_id: str, user_id: str, device_name: str = "Scanner") -> dict:
    """Genera un JWT de corta vida con scope de scanner."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.SCANNER_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": "scanner_auth",
        "tenant_id": tenant_id,
        "user_id": user_id,
        "device": device_name,
        "scope": settings.SCANNER_ALLOWED_SCOPES,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {
        "token": token,
        "expires_at": expire.isoformat(),
        "scope": settings.SCANNER_ALLOWED_SCOPES,
    }


def decode_scanner_token(token: str) -> dict:
    """Decodifica y valida un token de scanner. Raises HTTPException on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de scanner expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de scanner inválido"
        )

    if payload.get("sub") != "scanner_auth":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token no es de tipo scanner"
        )

    return payload


async def get_scanner_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    """Dependency que valida tokens de scanner y verifica scope de la ruta."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token requerido")

    payload = decode_scanner_token(credentials.credentials)

    # Verificar que la ruta está permitida
    path = request.url.path
    if any(path.startswith(p) for p in _BLOCKED_PREFIXES):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ruta '{path}' no accesible con token de scanner",
        )

    return payload


def is_scanner_token(request: Request) -> bool:
    """Comprueba si el request usa un token de scanner (sin lanzar excepción)."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("sub") == "scanner_auth"
    except Exception:
        return False
