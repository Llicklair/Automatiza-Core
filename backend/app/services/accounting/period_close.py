"""Cierre/reapertura de periodos contables + comprobación de bloqueo.

Reglas:
  - Un periodo cerrado bloquea CRUD sobre journal_entries con fecha dentro
    del rango del periodo.
  - Reabrir requiere `reason` y queda registrado (closed_by/reopened_by).
  - Solo se cierra de forma secuencial: para cerrar 2T se requiere 1T cerrado.
    (Política suave: emitir warning en lugar de bloquear, configurable.)
"""

from __future__ import annotations

from calendar import monthrange
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounting import AccountingPeriod


class PeriodClosedError(RuntimeError):
    """El periodo está cerrado: no se permite escritura."""

    def __init__(self, period_label: str, target_date: date | None = None):
        self.period_label = period_label
        self.target_date = target_date
        msg = f"El periodo contable {period_label} está cerrado y no admite cambios."
        if target_date:
            msg += f" Fecha del asiento: {target_date.isoformat()}."
        super().__init__(msg)


# ─── Helpers de rango ────────────────────────────────────────────────────────


def _month_range(year: int, month: int) -> tuple[date, date]:
    last = monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, last)


def _quarter_range(year: int, quarter: int) -> tuple[date, date]:
    months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}[quarter]
    start = date(year, months[0], 1)
    end_day = monthrange(year, months[1])[1]
    end = date(year, months[1], end_day)
    return start, end


def contains_date(period: AccountingPeriod, target: date) -> bool:
    """¿La fecha `target` cae dentro del rango del periodo?"""
    if period.kind == "month":
        start, end = _month_range(period.year, period.period_index)
    elif period.kind == "quarter":
        start, end = _quarter_range(period.year, period.period_index)
    elif period.kind == "year":
        start, end = date(period.year, 1, 1), date(period.year, 12, 31)
    else:
        return False
    return start <= target <= end


def _period_label(p: AccountingPeriod) -> str:
    if p.kind == "month":
        return f"{p.period_index:02d}/{p.year}"
    if p.kind == "quarter":
        return f"{p.period_index}T {p.year}"
    return f"Ejercicio {p.year}"


# ─── API ────────────────────────────────────────────────────────────────────


async def is_date_locked(
    db: AsyncSession,
    tenant_id: UUID,
    target: date | datetime,
) -> tuple[bool, str | None]:
    """¿Hay algún periodo cerrado que cubra esta fecha?

    Returns (locked, period_label_if_locked).
    """
    if isinstance(target, datetime):
        target_d = target.date()
    else:
        target_d = target

    res = await db.execute(
        select(AccountingPeriod)
        .where(AccountingPeriod.tenant_id == tenant_id)
        .where(AccountingPeriod.status == "closed")
        .where(AccountingPeriod.year == target_d.year)
    )
    periods = res.scalars().all()
    for p in periods:
        if contains_date(p, target_d):
            return True, _period_label(p)
    return False, None


async def list_periods(
    db: AsyncSession,
    tenant_id: UUID,
    year: int | None = None,
) -> list[AccountingPeriod]:
    stmt = select(AccountingPeriod).where(AccountingPeriod.tenant_id == tenant_id)
    if year is not None:
        stmt = stmt.where(AccountingPeriod.year == year)
    stmt = stmt.order_by(AccountingPeriod.year.desc(), AccountingPeriod.period_index.desc())
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def close_period(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None,
    year: int,
    kind: str,
    period_index: int,
    notes: str | None = None,
) -> AccountingPeriod:
    if kind not in {"month", "quarter", "year"}:
        raise ValueError(f"kind inválido: {kind}")
    if kind == "month" and not (1 <= period_index <= 12):
        raise ValueError("period_index debe estar entre 1 y 12 para mes")
    if kind == "quarter" and not (1 <= period_index <= 4):
        raise ValueError("period_index debe estar entre 1 y 4 para trimestre")
    if kind == "year" and period_index != 0:
        raise ValueError("period_index debe ser 0 para ejercicio anual")

    # ¿Existe ya?
    res = await db.execute(
        select(AccountingPeriod)
        .where(AccountingPeriod.tenant_id == tenant_id)
        .where(AccountingPeriod.year == year)
        .where(AccountingPeriod.kind == kind)
        .where(AccountingPeriod.period_index == period_index)
    )
    existing = res.scalar_one_or_none()

    if existing is not None:
        if existing.status == "closed":
            return existing  # idempotente
        existing.status = "closed"
        existing.closed_at = datetime.now(UTC)
        existing.closed_by_id = user_id
        existing.notes = notes
        await db.commit()
        await db.refresh(existing)
        return existing

    period = AccountingPeriod(
        tenant_id=tenant_id,
        year=year,
        kind=kind,
        period_index=period_index,
        status="closed",
        closed_by_id=user_id,
        notes=notes,
    )
    db.add(period)
    await db.commit()
    await db.refresh(period)
    return period


async def reopen_period(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None,
    period_id: UUID,
    reason: str,
) -> AccountingPeriod:
    if not reason or not reason.strip():
        raise ValueError("Se requiere un motivo para reabrir un periodo cerrado.")

    res = await db.execute(
        select(AccountingPeriod)
        .where(AccountingPeriod.id == period_id)
        .where(AccountingPeriod.tenant_id == tenant_id)
    )
    period = res.scalar_one_or_none()
    if period is None:
        raise LookupError("Periodo no encontrado")
    # Solo se reabre un periodo CERRADO (contrato ya documentado: el motivo se pide
    # "para reabrir un periodo cerrado"). Sin este guard se podia "reabrir" un
    # periodo abierto, ya-reabierto o nunca cerrado, sobre-escribiendo
    # reopened_at/motivo y dejando el estado contable incoherente.
    if period.status != "closed":
        raise ValueError(
            f"Solo se puede reabrir un periodo cerrado (estado actual: '{period.status}')."
        )

    period.status = "reopened"
    period.reopened_at = datetime.now(UTC)
    period.reopened_by_id = user_id
    period.reopen_reason = reason.strip()[:500]
    await db.commit()
    await db.refresh(period)
    return period
