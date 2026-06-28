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

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

# TZ de negocio del proyecto (scheduler, celery y tasks_scheduler ya operan
# en Europe/Madrid). Para *fechas de calendario* (fichaje, periodo de
# informes, nombres de fichero por día) hay que usar la fecha LOCAL, no la
# UTC: entre 00:00 y 02:00 hora española la fecha UTC es el día anterior.
BUSINESS_TZ = ZoneInfo("Europe/Madrid")


def local_today() -> date:
    """Fecha de calendario en la TZ de negocio (Europe/Madrid).

    Úsalo en lugar de `datetime.now(UTC).date()` cuando la fecha representa
    un día de negocio observado por el usuario (jornada laboral, periodo de
    facturación, etiqueta de informe). Los *timestamps* siguen en UTC.
    """
    return datetime.now(BUSINESS_TZ).date()


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
