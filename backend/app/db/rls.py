"""SQLAlchemy hooks para Row-Level Security Postgres (SEC.RLS).

`install_rls_listener(engine)` registra un listener que, en CADA statement,
ejecuta `set_config('app.current_tenant', <tenant>, true)` (≡ `SET LOCAL`)
leyendo el `ContextVar` de `app.core.tenant_context`. Esto hace que la RLS se
aplique en TODAS las sesiones — no solo en `get_db` (ruta HTTP), sino también en
las ~166 que abren `AsyncSessionLocal()`/`SessionLocal()` directamente (tools,
workers, servicios). Antes este listener NO existía y solo `get_db` aplicaba el
`SET LOCAL`, dejando esas sesiones sin tenant → la policy permisiva devolvía
filas de todos los tenants.

Se re-asserta en cada statement (no solo `after_begin`) porque el tenant puede
fijarse TARDE (en HTTP se conoce tras la SELECT del usuario) o cambiar
MID-transacción (el scheduler itera tenants en una misma sesión).

Para que el listener tenga efecto, el runtime debe conectar con un rol
`NOSUPERUSER NOBYPASSRLS` (`pyme_app`): un superusuario bypassa toda la RLS.
Ver `app.db.security_bootstrap`.

En SQLite (tests) es no-op — RLS es Postgres-only.

Validación de input: `tenant_id` que no parsee como UUID se trata como "sin
tenant" (cadena vacía → fail-open), evitando interpolar valores arbitrarios en
el `SET LOCAL`.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import get_current_tenant

_GUC = "app.current_tenant"
_CACHE_KEY = "_rls_tenant"


def _desired_tenant() -> str:
    """Valor a poner en `app.current_tenant`: UUID validado o '' (sin tenant)."""
    tid = get_current_tenant()
    if not tid:
        return ""
    try:
        return str(UUID(tid))
    except (ValueError, TypeError):
        return ""


def install_rls_listener(engine) -> None:
    """Registra el listener RLS sobre un engine async o síncrono. Idempotente.

    `desired` es siempre un UUID validado o '' → se interpola de forma segura en
    el `set_config`. La llamada `cursor.execute(...)` es directa sobre el cursor
    DBAPI y NO re-dispara `before_cursor_execute`, así que no hay recursión.
    """
    target = getattr(engine, "sync_engine", engine)  # AsyncEngine → su sync_engine
    if getattr(target, "_rls_listener_installed", False):
        return
    target._rls_listener_installed = True

    @event.listens_for(target, "begin")
    def _rls_reset_cache(conn):
        # SET LOCAL se descarta al terminar la transacción; al empezar una nueva
        # invalidamos la caché para re-aplicar en el primer statement.
        conn.info.pop(_CACHE_KEY, None)

    @event.listens_for(target, "before_cursor_execute")
    def _rls_set_tenant(conn, cursor, statement, parameters, context, executemany):
        if conn.dialect.name != "postgresql":
            return
        desired = _desired_tenant()
        if conn.info.get(_CACHE_KEY) == desired:
            return
        cursor.execute(f"SELECT set_config('{_GUC}', '{desired}', true)")
        conn.info[_CACHE_KEY] = desired


async def apply_tenant_rls(session: AsyncSession) -> str | None:
    """Aplica `SET LOCAL app.current_tenant` a la transacción actual de forma
    explícita. Redundante con `install_rls_listener` (que cubre toda sesión),
    se conserva como API explícita y por compatibilidad con los tests.

    Devuelve el tenant aplicado (string UUID) o `None` si no hay contexto o si
    el dialect no es Postgres.
    """
    dialect_name = session.bind.dialect.name if session.bind is not None else ""
    if dialect_name != "postgresql":
        return None

    tenant_id = get_current_tenant()
    if not tenant_id:
        return None

    try:
        parsed = str(UUID(tenant_id))
    except (ValueError, TypeError):
        return None

    await session.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": parsed},
    )
    return parsed
