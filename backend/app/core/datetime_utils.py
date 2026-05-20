"""Helpers compartidos para manejo de datetime.

**Por qué existe este módulo**: SQLite y algunos drivers no preservan
`tzinfo` aunque la columna esté declarada `TIMESTAMP WITH TIME ZONE`.
Comparar `datetime.now(UTC)` (tz-aware) contra un atributo ORM tz-naive
lanza `TypeError: can't compare offset-naive and offset-aware datetimes`.

Histórico: este bug se descubrió simultáneamente en
`services/workflow/recovery.py` y `services/workflow/approval.py` al
añadir coverage (iteración 2026-05-19). El patrón apareció en al menos
6 lugares en `backend/app/`. En lugar de duplicar el "if tzinfo is None"
in-line, centralizamos aquí.

**Regla de uso**: si vas a comparar un `datetime` que viene del ORM
contra `datetime.now(UTC)`, normaliza primero con `as_aware()`.
"""

from datetime import datetime, timezone


def as_aware(dt: datetime | None, default_tz: timezone = timezone.utc) -> datetime | None:
    """Devuelve `dt` tz-aware. Si es naive, asume `default_tz` (UTC por defecto).

    No-op para `None` y para datetimes ya tz-aware. Idempotente.

    Casos cubiertos:
        - SQLite via aiosqlite: pierde tzinfo en columnas TIMESTAMPTZ
        - Postgres via asyncpg: preserva tzinfo (no-op aquí)
        - Cualquier driver futuro que se comporte como SQLite
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt
