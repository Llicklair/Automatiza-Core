"""Sesión de BD para tools de agentes.

`tool_session()` es el punto único para abrir sesiones desde tools: fija el
ContextVar de tenant para que el listener RLS de `app/db/rls.py` ejecute
`SET LOCAL app.current_tenant` en cada statement de la sesión, y evita que una
tool olvide el contexto y la sesión quede silenciosamente sin tenant.

Uso:
    async with tool_session(tenant_id) as db:
        ...

`tenant_id` es OBLIGATORIO. Para flujos deliberados SIN tenant (auth pre-tenant,
scan cross-tenant del scheduler, webhooks) usar `AsyncSessionLocal()` dentro de
`rls_bypass()` — ver `app/workers/tasks_scheduler.py`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import tenant_context
from app.db.base import AsyncSessionLocal


@asynccontextmanager
async def tool_session(tenant_id: str | UUID) -> AsyncIterator[AsyncSession]:
    """Abre una AsyncSession con el tenant-context aplicado (RLS).

    `tenant_id` es OBLIGATORIO: fija el ContextVar para que el listener RLS
    aplique `SET LOCAL app.current_tenant`. Antes aceptaba None y caía a una
    `AsyncSessionLocal()` "a secas" (heredando el ContextVar ambiente) — un
    fallback SILENCIOSO que enmascaraba olvidos de contexto. Ahora exige el
    tenant explícito y falla ruidosamente si falta (defensa en profundidad
    sobre la RLS fail-closed). Para acceso deliberado sin tenant: usar
    `AsyncSessionLocal()` dentro de `rls_bypass()`.
    """
    if tenant_id is None:
        raise ValueError(
            "tool_session() requiere un tenant_id explícito. Para acceso "
            "deliberado sin tenant usa AsyncSessionLocal() dentro de rls_bypass()."
        )
    with tenant_context(str(tenant_id)):
        async with AsyncSessionLocal() as db:
            yield db
