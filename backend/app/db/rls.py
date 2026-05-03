"""Row-Level Security (RLS) — listener SQLAlchemy.

Registra un hook `before_cursor_execute` en cada engine que, antes de cada
query, ejecuta `set_config('app.current_tenant', '<uuid>', true)` con el
tenant del ContextVar centralizado en `app.core.tenant_context`.

Las políticas de RLS definidas en la migración Alembic comparan
`tenant_id` con `current_setting('app.current_tenant', true)::uuid`,
bloqueando filas de otros tenants incluso si la query no incluye el filtro.

Diseño:
- Aplica solo a Postgres. SQLite (tests unitarios) lo ignora silenciosamente.
- Usa un guard via `connection.info` para evitar recursión cuando el
  propio `set_config` dispara otro `before_cursor_execute`.
- Si el ContextVar está vacío Y la sesión no es modo "system", el listener
  sigue ejecutando `set_config(..., '', true)` para limpiar cualquier valor
  residual del checkout anterior.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.core.tenant_context import get_current_tenant, is_system_context

_logger = logging.getLogger(__name__)

_GUARD_KEY = "_rls_setting_in_progress"
_SYSTEM_GUARD_KEY = "_rls_system_mode"


def register_rls_listener(engine: Engine) -> None:
    """Registra el listener RLS en un Engine síncrono.

    Para AsyncEngine, pasa `engine.sync_engine`. SQLAlchemy comparte los
    eventos entre el sync y el async engine subyacente.
    """

    @event.listens_for(engine, "before_cursor_execute")
    def _set_tenant(
        conn: Any,
        cursor: Any,
        statement: str,
        parameters: Any,
        context: Any,
        executemany: bool,
    ) -> None:
        # Solo Postgres. En SQLite (tests) RLS no existe y SET no es válido.
        if conn.dialect.name != "postgresql":
            return

        # Guard de recursión: cuando este listener ejecuta SET, ese SET
        # también dispara before_cursor_execute. Ignorarlo evita un loop.
        if conn.info.get(_GUARD_KEY):
            return

        # Modo "sistema": las queries que necesitan ver datos de todos los
        # tenants (scheduler, jobs de mantenimiento) marcan la sesión y
        # el listener no aplica políticas de tenant.
        if is_system_context() or conn.info.get(_SYSTEM_GUARD_KEY):
            return

        tenant = get_current_tenant()

        conn.info[_GUARD_KEY] = True
        try:
            if tenant is not None:
                cursor.execute(
                    "SELECT set_config('app.current_tenant', %s, true)",
                    (tenant,),
                )
            else:
                # Limpia el GUC para evitar arrastre del checkout anterior.
                cursor.execute(
                    "SELECT set_config('app.current_tenant', '', true)"
                )
        finally:
            conn.info[_GUARD_KEY] = False
