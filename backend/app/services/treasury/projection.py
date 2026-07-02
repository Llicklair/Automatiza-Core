"""Cashflow proyectado — F2.7.

Construye una serie diaria de saldo de tesorería previsto a N días vista
combinando:

  - Saldo bancario actual (último balance conocido).
  - Cobros previstos: facturas emitidas pendientes con due_date dentro
    de la ventana.
  - Pagos previstos: facturas recibidas pendientes con due_date dentro
    de la ventana.
  - Nóminas previstas: payrolls aprobadas/pendientes con issue_date en
    ventana — por defecto se proyectan al día 28 del mes que cubren.

Devuelve por día: opening_balance, in, out, closing_balance, eventos
("3 facturas vencen + nómina equipo"). Si en algún día closing_balance
cae bajo 0 → genera un `CashflowAlert` con la fecha y el déficit.

El motor es determinista (sin LLM) y rápido — pensado para ejecutarse
al cargar la página `/tesoreria/cashflow` y como input del bandeja IA.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import local_today
from app.db.models.billing import Invoice
from app.db.models.hr import Payroll
from app.db.models.models import BankTransaction


@dataclass
class CashflowEvent:
    kind: str  # "invoice_in" | "invoice_out" | "payroll"
    label: str
    amount: float
    source_id: str | None = None


@dataclass
class CashflowDay:
    day: date
    opening_balance: float
    inflow: float
    outflow: float
    closing_balance: float
    events: list[CashflowEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.day.isoformat(),
            "opening_balance": round(self.opening_balance, 2),
            "inflow": round(self.inflow, 2),
            "outflow": round(self.outflow, 2),
            "closing_balance": round(self.closing_balance, 2),
            "events": [
                {"kind": e.kind, "label": e.label, "amount": round(e.amount, 2), "source_id": e.source_id}
                for e in self.events
            ],
        }


@dataclass
class CashflowAlert:
    day: date
    deficit: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.day.isoformat(),
            "deficit": round(self.deficit, 2),
            "message": self.message,
        }


async def _current_balance(db: AsyncSession, tenant_id: UUID) -> float:
    """Saldo actual = última `BankTransaction.balance` no NULL, o suma
    de movimientos del último mes si no hay balance reportado.
    """
    last_q = await db.execute(
        sa.select(BankTransaction.balance)
        .where(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.balance.is_not(None),
        )
        .order_by(BankTransaction.date.desc())
        .limit(1)
    )
    val = last_q.scalar_one_or_none()
    if val is not None:
        return float(val)

    since = datetime.now(UTC) - timedelta(days=30)
    sum_q = await db.execute(
        sa.select(sa.func.coalesce(sa.func.sum(BankTransaction.amount), 0)).where(
            BankTransaction.tenant_id == tenant_id,
            BankTransaction.date >= since,
        )
    )
    return float(sum_q.scalar_one() or 0)


def _payroll_pay_date(p: Payroll) -> date:
    """Fecha estimada de pago: día 28 del mes de `period_end`."""
    pe = p.period_end
    if isinstance(pe, datetime):
        pe = pe.date()
    day = min(28, _last_day_of_month(pe))
    return date(pe.year, pe.month, day)


def _last_day_of_month(d: date) -> int:
    from calendar import monthrange

    return monthrange(d.year, d.month)[1]


async def project_cashflow(
    db: AsyncSession,
    tenant_id: UUID,
    days_ahead: int = 90,
    *,
    today: date | None = None,
) -> dict[str, Any]:
    """Devuelve la proyección de cashflow:

    {
      "opening_balance": float,
      "days_ahead": int,
      "series": [CashflowDay(...).to_dict()],
      "summary": {"total_in": ..., "total_out": ..., "net": ..., "min_balance": ..., "min_balance_date": "YYYY-MM-DD"},
      "alerts": [CashflowAlert(...).to_dict()],
    }
    """
    if days_ahead < 1 or days_ahead > 365:
        raise ValueError(f"days_ahead fuera de rango (1..365): {days_ahead}")

    today = today or local_today()
    horizon = today + timedelta(days=days_ahead)

    opening = await _current_balance(db, tenant_id)

    by_day: dict[date, list[CashflowEvent]] = defaultdict(list)

    # Cobros previstos
    issued_q = await db.execute(
        sa.select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
            Invoice.status.in_(["sent", "draft", "pending"]),
            Invoice.due_date.is_not(None),
            sa.func.date(Invoice.due_date) >= today,
            sa.func.date(Invoice.due_date) <= horizon,
        )
    )
    for inv in issued_q.scalars().all():
        d = inv.due_date.date() if isinstance(inv.due_date, datetime) else inv.due_date
        by_day[d].append(
            CashflowEvent(
                kind="invoice_in",
                label=f"Cobro factura {inv.invoice_number or inv.id}",
                amount=float(inv.amount_total or 0),
                source_id=str(inv.id),
            )
        )

    # Pagos previstos
    received_q = await db.execute(
        sa.select(Invoice).where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            Invoice.status.in_(["sent", "draft", "pending"]),
            Invoice.due_date.is_not(None),
            sa.func.date(Invoice.due_date) >= today,
            sa.func.date(Invoice.due_date) <= horizon,
        )
    )
    for inv in received_q.scalars().all():
        d = inv.due_date.date() if isinstance(inv.due_date, datetime) else inv.due_date
        by_day[d].append(
            CashflowEvent(
                kind="invoice_out",
                label=f"Pago factura {inv.invoice_number or inv.id}",
                amount=-float(inv.amount_total or 0),
                source_id=str(inv.id),
            )
        )

    # Nóminas previstas
    payrolls_q = await db.execute(
        sa.select(Payroll).where(
            Payroll.tenant_id == tenant_id,
            Payroll.status.in_(["draft", "approved", "pending"]),
        )
    )
    for p in payrolls_q.scalars().all():
        pay_date = _payroll_pay_date(p)
        if today <= pay_date <= horizon:
            by_day[pay_date].append(
                CashflowEvent(
                    kind="payroll",
                    label="Nómina empleado",
                    amount=-float(p.net_salary or 0),
                    source_id=str(p.id),
                )
            )

    # Serie diaria
    series: list[CashflowDay] = []
    alerts: list[CashflowAlert] = []
    running = opening
    total_in = total_out = 0.0
    min_balance = opening
    min_balance_date = today

    for offset in range(days_ahead + 1):
        d = today + timedelta(days=offset)
        events = by_day.get(d, [])
        day_in = sum(e.amount for e in events if e.amount > 0)
        day_out = -sum(e.amount for e in events if e.amount < 0)
        opening_balance = running
        closing = opening_balance + day_in - day_out
        running = closing
        total_in += day_in
        total_out += day_out
        if closing < min_balance:
            min_balance = closing
            min_balance_date = d
        series.append(
            CashflowDay(
                day=d,
                opening_balance=opening_balance,
                inflow=day_in,
                outflow=day_out,
                closing_balance=closing,
                events=events,
            )
        )
        if closing < 0:
            alerts.append(
                CashflowAlert(
                    day=d,
                    deficit=-closing,
                    message=(
                        f"Tensión de liquidez prevista para {d.isoformat()}: " f"saldo proyectado {closing:.2f} €."
                    ),
                )
            )

    return {
        "opening_balance": round(opening, 2),
        "days_ahead": days_ahead,
        "series": [d.to_dict() for d in series],
        "summary": {
            "total_in": round(total_in, 2),
            "total_out": round(total_out, 2),
            "net": round(total_in - total_out, 2),
            "min_balance": round(min_balance, 2),
            "min_balance_date": min_balance_date.isoformat(),
        },
        "alerts": [a.to_dict() for a in alerts],
    }
