from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.security import decode_token
from app.core.tenant_context import set_current_tenant
from app.db.base import get_db
from app.db.models.crm import Client
from app.db.models.models import Tenant, User
from app.services import tenant_service

# auto_error=False: si falta la cabecera Authorization devolvemos 401 (no el 403
# por defecto de HTTPBearer). 401 es lo correcto en REST para credenciales
# ausentes y lo que esperan los tests *_requiere_auth.
bearer_scheme = HTTPBearer(auto_error=False)

# Rol "employee": solo accede al portal del empleado, su propio perfil,
# auth (refresh/logout) y datos básicos del tenant. Cualquier otro path → 403.
_EMPLOYEE_ALLOWED_PREFIXES = (
    "/api/v1/portal/",
    "/api/v1/auth/",
)
_EMPLOYEE_ALLOWED_EXACT = frozenset({
    "/api/v1/users/me",
    "/api/v1/tenant/me",
})


def _employee_can_access(path: str) -> bool:
    if path in _EMPLOYEE_ALLOWED_EXACT:
        return True
    return any(path.startswith(p) for p in _EMPLOYEE_ALLOWED_PREFIXES)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise credentials_exception
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Eager-load tenant: get_current_tenant() accede a user.tenant; sin esto la
    # relación lazy dispara un segundo SELECT (o MissingGreenlet en async) en
    # cada request autenticado.
    result = await db.execute(
        select(User).where(User.id == UUID(user_id)).options(joinedload(User.tenant))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception

    if user.role == "employee" and not _employee_can_access(request.url.path):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso restringido al portal del empleado",
        )

    # Fija el tenant activo en el ContextVar para el resto del request.
    # Lo leen el listener SQLAlchemy (Fase 3 RLS), agentes LangGraph y el
    # decorador enforce_tenant que protege las tools del LLM.
    set_current_tenant(str(user.tenant_id))
    return user


async def get_current_tenant(current_user: User = Depends(get_current_user)) -> Tenant:
    return current_user.tenant


async def get_tenant_or_404(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Tenant:
    """FastAPI dependency: resolve current user's tenant or raise 404."""
    try:
        return await tenant_service.get_tenant(db, current_user.tenant_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant no encontrado")


async def get_current_client_portal(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Client:
    """Dependencia para endpoints del portal de clientes externo."""
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de portal inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise exc
    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "client_portal":
        raise exc
    client_id: str | None = payload.get("sub")
    tenant_id: str | None = payload.get("tenant_id")
    if not client_id or not tenant_id:
        raise exc
    result = await db.execute(select(Client).where(Client.id == UUID(client_id)))
    client = result.scalar_one_or_none()
    if client is None or str(client.tenant_id) != tenant_id:
        raise exc
    # Fija el tenant del portal en el ContextVar para que la RLS ancle las
    # consultas posteriores del request a este tenant (igual que get_current_user).
    set_current_tenant(tenant_id)
    return client


def require_role(*roles: str):
    """Decorador de dependencia para control de acceso por rol."""

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere uno de los roles: {', '.join(roles)}",
            )
        return current_user

    return role_checker
