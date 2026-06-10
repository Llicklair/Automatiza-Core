"""Sesión de BD para tools de agentes.

`tool_session()` es el punto único para abrir sesiones desde tools: garantiza
que el ContextVar de tenant esté seteado (el listener RLS de `app/db/rls.py`
hace `SET LOCAL app.current_tenant` al iniciar cada transacción) y evita que
una tool olvide el contexto y la sesión quede silenciosamente sin tenant.

Uso:
    async with tool_session(tenant_id) as db:
        ...

Sin `tenant_id` se comporta como `AsyncSessionLocal()` a secas (hereda el
ContextVar del request/task actual).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import tenant_context
from app.db.base import AsyncSessionLocal


@asynccontextmanager
async def tool_session(tenant_id: str | UUID | None = None) -> AsyncIterator[AsyncSession]:
    """Abre una AsyncSession con el tenant-context aplicado (RLS)."""
    if tenant_id is not None:
        with tenant_context(str(tenant_id)):
            async with AsyncSessionLocal() as db:
                yield db
    else:
        async with AsyncSessionLocal() as db:
            yield db
