"""Política de retención para backups remotos (BAK.B2).

Política consensuada (Ronda 16 §87.2 + Ronda 18 §99):
* **30 días rolling** — se conserva el backup diario de los últimos 30 días.
* **12 snapshots mensuales** — se conserva el primer backup del mes para los
  últimos 12 meses (un año hacia atrás).
* Cualquier backup que no cumpla ninguna de las dos condiciones es candidato
  a purga.

Esta función opera sobre listas en memoria — no hace red ni I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone


@dataclass(frozen=True)
class BackupCandidate:
    """Backup candidato a evaluar para retención."""

    key: str  # identificador en el bucket B2 o equivalente
    created_at: datetime
    size_bytes: int = 0


def apply_rolling_retention(
    candidates: list[BackupCandidate],
    *,
    now: datetime | None = None,
    daily_window_days: int = 30,
    monthly_window_count: int = 12,
) -> tuple[list[BackupCandidate], list[BackupCandidate]]:
    """Aplica política rolling + mensual.

    Devuelve `(to_keep, to_purge)`.

    Reglas:
    1. `to_keep` contiene:
       - Todos los backups dentro de los últimos `daily_window_days` días.
       - Para cada uno de los últimos `monthly_window_count` meses
         (incluyendo el mes actual), el backup MÁS ANTIGUO de ese mes.
    2. `to_purge` contiene el resto.
    3. Si dos reglas eligen el mismo backup, solo se cuenta una vez en
       `to_keep`.
    """
    if not candidates:
        return [], []

    now_ts = now or datetime.now(timezone.utc)
    daily_cutoff = now_ts - timedelta(days=daily_window_days)

    sorted_candidates = sorted(candidates, key=lambda c: c.created_at)
    keep_set: set[str] = set()

    # Regla 1: ventana diaria
    for c in sorted_candidates:
        c_ts = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
        if c_ts >= daily_cutoff:
            keep_set.add(c.key)

    # Regla 2: snapshot mensual — el más antiguo de cada (año, mes)
    # dentro de la ventana de N meses hacia atrás.
    monthly_first: dict[tuple[int, int], BackupCandidate] = {}
    for c in sorted_candidates:
        c_ts = c.created_at if c.created_at.tzinfo else c.created_at.replace(tzinfo=timezone.utc)
        ym = (c_ts.year, c_ts.month)
        if ym not in monthly_first:
            monthly_first[ym] = c

    # Filtramos los últimos N meses
    eligible_months = _last_n_months(now_ts.date(), monthly_window_count)
    for ym in eligible_months:
        c = monthly_first.get(ym)
        if c is not None:
            keep_set.add(c.key)

    to_keep = [c for c in candidates if c.key in keep_set]
    to_purge = [c for c in candidates if c.key not in keep_set]
    return to_keep, to_purge


def _last_n_months(reference: date, n: int) -> list[tuple[int, int]]:
    """Devuelve `[(year, month), ...]` para los últimos N meses incluido el actual."""
    result = []
    y, m = reference.year, reference.month
    for _ in range(n):
        result.append((y, m))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    return result
