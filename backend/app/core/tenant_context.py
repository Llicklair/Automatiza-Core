"""Tenant context — fuente de verdad única del tenant activo en el contexto async.

Lo setea la dependencia `get_current_user` desde el JWT en cada request, y se
propaga a workers y agentes LangGraph en sus puntos de entrada. Es leído por:
  - El listener SQLAlchemy de `app.db.rls` (SEC.RLS), que ejecuta
    `SET LOCAL app.current_tenant` en cada statement de cada sesión
  - Código de la capa servicios que necesita scoping implícito de tenant
  - El decorador `enforce_tenant` en `app.agents.tenant_context` que protege
    las tools de LangChain contra prompt injection del LLM

Diseño: ContextVar de stdlib. asyncio garantiza que cada Task hereda una copia
del contexto al crearse, por lo que requests concurrentes no se contaminan.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_current_tenant_ctx: ContextVar[str | None] = ContextVar(
    "current_tenant", default=None
)

# Task activo (paralelo a tenant). Lo setea el TaskRunner del orquestador
# antes de invocar agentes, para que tools que necesiten scoping por task
# (e.g. dedup cross-dispatcher de documentos) puedan consultarlo sin
# tener que recibir task_id como argumento explícito desde el LLM.
_current_task_ctx: ContextVar[str | None] = ContextVar(
    "current_task", default=None
)

# Bypass explícito de la RLS (SEC.RLS fail-closed). Cuando es True, el listener
# de `app.db.rls` setea `app.rls_bypass = 'on'` y la policy de Postgres deja
# pasar TODAS las filas. Reservado para los flujos legítimos sin tenant en
# contexto: autenticación (lookup de usuario PRE-tenant), portal de cliente
# (lookup por token), webhooks externos (sin JWT) y la lectura cross-tenant
# inicial del scheduler. NUNCA debe envolver lógica de negocio de un tenant.
_rls_bypass_ctx: ContextVar[bool] = ContextVar("rls_bypass", default=False)


def set_current_tenant(tenant_id: str | None) -> None:
    """Setea el tenant activo para el resto del contexto async actual."""
    _current_tenant_ctx.set(tenant_id)


def get_current_tenant() -> str | None:
    """Devuelve el tenant activo o None si no se ha seteado."""
    return _current_tenant_ctx.get()


def set_current_task(task_id: str | None) -> None:
    """Setea la task activa para el resto del contexto async actual."""
    _current_task_ctx.set(task_id)


def get_current_task() -> str | None:
    """Devuelve la task activa o None si no se ha seteado."""
    return _current_task_ctx.get()


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


def is_rls_bypass() -> bool:
    """True si hay un bypass de RLS activo en el contexto async actual."""
    return _rls_bypass_ctx.get()


@contextmanager
def rls_bypass() -> Iterator[None]:
    """Desactiva la RLS para los flujos legítimos sin tenant (fail-closed).

    Bajo RLS fail-closed, una sesión sin tenant en contexto NO ve ninguna fila
    de las tablas con `tenant_id`. Esto es lo correcto por defecto, pero rompe
    cuatro flujos de infraestructura que consultan ANTES de conocer el tenant o
    de forma deliberadamente global:

      - **Auth**: el lookup del `User` por email/id ocurre antes de fijar tenant.
      - **Portal de cliente**: el lookup del `Client`/token es pre-tenant.
      - **Webhooks externos** (telegram, autofirma, OAuth): sin JWT.
      - **Scheduler**: la SELECT inicial cross-tenant que enumera qué tenants
        procesar (el trabajo por-tenant SÍ va dentro de `tenant_context(t)`).

    Uso::

        with rls_bypass():
            user = await db.scalar(select(User).where(User.email == email))

    Es un context manager re-entrante seguro (restaura el valor previo al salir).
    """
    token = _rls_bypass_ctx.set(True)
    try:
        yield
    finally:
        _rls_bypass_ctx.reset(token)


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
