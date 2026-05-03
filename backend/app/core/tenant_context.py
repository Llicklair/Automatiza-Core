"""Tenant context — fuente de verdad única del tenant activo en el contexto async.

Lo setea el middleware FastAPI desde el JWT en cada request, y se propaga a
workers Celery y agentes LangGraph en sus puntos de entrada. Es leído por:
  - El listener SQLAlchemy (Fase 3 RLS) que ejecuta SET LOCAL app.current_tenant
  - Código de la capa servicios que necesita scoping implícito de tenant
  - El decorador `enforce_tenant` en `app.agents.tenant_context` que protege
    las tools de LangChain contra prompt injection del LLM

Diseño: ContextVar de stdlib. asyncio garantiza que cada Task hereda una copia
del contexto al crearse, por lo que requests concurrentes no se contaminan.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

_current_tenant_ctx: ContextVar[str | None] = ContextVar(
    "current_tenant", default=None
)

# Bandera para queries de sistema que deben ver datos de todos los tenants
# (scheduler, jobs de mantenimiento, migraciones). Se setea explícitamente
# y el listener RLS la respeta saltándose la inyección de policy.
_system_ctx: ContextVar[bool] = ContextVar("system_context", default=False)


def set_current_tenant(tenant_id: str | None) -> None:
    """Setea el tenant activo para el resto del contexto async actual."""
    _current_tenant_ctx.set(tenant_id)


def get_current_tenant() -> str | None:
    """Devuelve el tenant activo o None si no se ha seteado."""
    return _current_tenant_ctx.get()


def require_current_tenant() -> str:
    """Devuelve el tenant activo. Lanza RuntimeError si no hay contexto.

    Útil en el listener SQLAlchemy y en código que NO debe ejecutarse fuera
    de un request o de un `tenant_context(...)` explícito.
    """
    tid = _current_tenant_ctx.get()
    if tid is None:
        raise RuntimeError(
            "No tenant in current context. "
            "Did the request reach TenantContextMiddleware, "
            "or did the worker/agent entry point call set_current_tenant()?"
        )
    return tid


@contextmanager
def tenant_context(tenant_id: str) -> Iterator[None]:
    """Context manager para scoping explícito.

    Usado por jobs programados (APScheduler) o tareas de mantenimiento que
    iteran sobre múltiples tenants:

        for t in active_tenants:
            with tenant_context(t.id):
                await do_something(db)
    """
    token = _current_tenant_ctx.set(tenant_id)
    try:
        yield
    finally:
        _current_tenant_ctx.reset(token)


def is_system_context() -> bool:
    """Devuelve True si el código actual está dentro de un `system_context()`."""
    return _system_ctx.get()


@contextmanager
def system_context() -> Iterator[None]:
    """Context manager que indica al listener RLS que esta sesión es de sistema
    y debe ver datos de todos los tenants.

    Uso restringido: bootstrap de scheduler, jobs de mantenimiento global,
    consultas administrativas. NUNCA en código de aplicación que sirva un
    request de usuario.

        async with AsyncSessionLocal() as db, system_context():
            workflows = await get_active_scheduled_workflows(db)
            for wf in workflows:
                with tenant_context(str(wf.tenant_id)):
                    ...
    """
    token = _system_ctx.set(True)
    try:
        yield
    finally:
        _system_ctx.reset(token)
