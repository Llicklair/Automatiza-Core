"""SQLAlchemy hook para Row-Level Security Postgres (SEC.RLS).

Lee `get_current_tenant()` del `ContextVar` en `app.core.tenant_context` y
ejecuta `SET LOCAL app.current_tenant = '<uuid>'` al inicio de cada
transacción. Las policies RLS creadas en la migración `0016_sec_rls`
filtran por esa variable.

En SQLite (tests) no hace nada — RLS es Postgres-only.

Validación de input: rechaza `tenant_id` que no parsee como UUID para evitar
SQL injection en la interpolación (necesaria porque `SET LOCAL` no acepta
parámetros bindeados).
"""

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import get_current_tenant


async def apply_tenant_rls(session: AsyncSession) -> str | None:
    """Aplica `SET LOCAL app.current_tenant` a la transacción actual.

    Devuelve el tenant aplicado (string UUID) o `None` si no hay contexto
    o si el dialect no es Postgres.
    """
    dialect_name = session.bind.dialect.name if session.bind is not None else ""
    if dialect_name != "postgresql":
        return None

    tenant_id = get_current_tenant()
    if not tenant_id:
        return None

    # Validar que es UUID parseable. Si no, dejamos la transacción sin
    # contexto — las policies bloquearán cualquier SELECT.
    try:
        parsed = str(UUID(tenant_id))
    except (ValueError, TypeError):
        return None

    # SET LOCAL no acepta parámetros bindeados — interpolación validada.
    await session.execute(text(f"SET LOCAL app.current_tenant = '{parsed}'"))
    return parsed
