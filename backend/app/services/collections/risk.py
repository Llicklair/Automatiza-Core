"""Scoring de riesgo de cobro por cliente — F3.9.

Métricas calculadas sobre el histórico de facturas EMITIDAS del tenant:

  - days_avg_to_pay      — días promedio entre fecha emisión y fecha cobro
                            (solo facturas con `status='paid'`).
  - overdue_count        — facturas vencidas sin cobrar a hoy.
  - overdue_amount       — importe total vencido.
  - max_days_overdue     — peor demora actual.
  - ratio_paid_on_time   — % facturas cobradas dentro del vencimiento.
  - risk_level           — "low" | "medium" | "high" según combinación.

El motor es determinista. Si más adelante hay suficiente histórico, se
puede sustituir por un modelo entrenado, pero esta heurística cubre el
80 % de los casos útiles para una pyme.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.datetime_utils import local_today
from app.db.models.billing import Invoice
from app.db.models.crm import Client

_PAID_STATUSES = ("paid", "reconciled", "settled")
_UNPAID_STATUSES = ("sent", "pending", "draft", "overdue")


@dataclass
class ClientRiskScore:
    client_id: str
    client_name: str
    nif: str | None
    total_invoices: int
    paid_count: int
    unpaid_count: int
    overdue_count: int
    overdue_amount: float
    max_days_overdue: int
    days_avg_to_pay: float | None  # None si no hay facturas cobradas
    ratio_paid_on_time: float | None  # 0.0..1.0
    risk_level: str  # "low" | "medium" | "high"
    risk_score: int  # 0..100, mayor = peor
    drivers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_name": self.client_name,
            "nif": self.nif,
            "total_invoices": self.total_invoices,
            "paid_count": self.paid_count,
            "unpaid_count": self.unpaid_count,
            "overdue_count": self.overdue_count,
            "overdue_amount": round(self.overdue_amount, 2),
            "max_days_overdue": self.max_days_overdue,
            "days_avg_to_pay": (
                round(self.days_avg_to_pay, 1) if self.days_avg_to_pay is not None else None
            ),
            "ratio_paid_on_time": (
                round(self.ratio_paid_on_time, 3) if self.ratio_paid_on_time is not None else None
            ),
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "drivers": self.drivers,
        }


def _days_between(a: datetime | date | None, b: datetime | date | None) -> int | None:
    if a is None or b is None:
        return None
    da = a.date() if isinstance(a, datetime) else a
    db = b.date() if isinstance(b, datetime) else b
    return (da - db).days


def compute_client_risk(
    client: Client, invoices: list[Invoice], *, today: date | None = None
) -> ClientRiskScore:
    """Computa el scoring para un cliente concreto sobre sus facturas emitidas."""
    today = today or local_today()
    total = len(invoices)
    paid = [inv for inv in invoices if (inv.status or "").lower() in _PAID_STATUSES]
    unpaid = [inv for inv in invoices if (inv.status or "").lower() in _UNPAID_STATUSES]

    # Días promedio hasta cobro — usamos updated_at como proxy de fecha de cobro
    # cuando no hay payment_date dedicado. Si una factura está marcada paid,
    # asumimos que updated_at refleja el momento del cambio de estado.
    paid_intervals: list[int] = []
    on_time_count = 0
    for inv in paid:
        emit = inv.date
        pay_proxy = inv.updated_at or inv.created_at or inv.date
        delta = _days_between(pay_proxy, emit)
        if delta is not None and delta >= 0:
            paid_intervals.append(delta)
            if inv.due_date:
                due = inv.due_date.date() if isinstance(inv.due_date, datetime) else inv.due_date
                pay_d = pay_proxy.date() if isinstance(pay_proxy, datetime) else pay_proxy
                if pay_d <= due:
                    on_time_count += 1

    days_avg = (sum(paid_intervals) / len(paid_intervals)) if paid_intervals else None
    ratio_on_time = (on_time_count / len(paid)) if paid else None

    overdue_invoices = []
    overdue_amount = Decimal(0)
    max_overdue_days = 0
    for inv in unpaid:
        if not inv.due_date:
            continue
        due = inv.due_date.date() if isinstance(inv.due_date, datetime) else inv.due_date
        if due < today:
            days_late = (today - due).days
            overdue_invoices.append(inv)
            overdue_amount += Decimal(inv.amount_total or 0)
            max_overdue_days = max(max_overdue_days, days_late)

    drivers: list[str] = []
    score = 0

    if overdue_invoices:
        score += min(40, len(overdue_invoices) * 10)
        drivers.append(f"{len(overdue_invoices)} factura(s) vencida(s) sin cobrar")
    if max_overdue_days > 30:
        score += 20
        drivers.append(f"{max_overdue_days} días de demora máxima")
    elif max_overdue_days > 15:
        score += 10
    if days_avg is not None and days_avg > 45:
        score += 15
        drivers.append(f"Tarda {days_avg:.0f} días de media en pagar")
    if ratio_on_time is not None and ratio_on_time < 0.5:
        score += 15
        drivers.append(f"Solo {ratio_on_time*100:.0f}% de facturas pagadas a tiempo")
    if overdue_amount > Decimal("5000"):
        score += 10
        drivers.append(f"Importe vencido elevado ({float(overdue_amount):.0f} €)")

    score = min(score, 100)
    if score >= 60:
        risk_level = "high"
    elif score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    if not drivers:
        drivers.append("Sin señales de impago en el histórico.")

    return ClientRiskScore(
        client_id=str(client.id),
        client_name=client.name,
        nif=client.nif,
        total_invoices=total,
        paid_count=len(paid),
        unpaid_count=len(unpaid),
        overdue_count=len(overdue_invoices),
        overdue_amount=float(overdue_amount),
        max_days_overdue=max_overdue_days,
        days_avg_to_pay=days_avg,
        ratio_paid_on_time=ratio_on_time,
        risk_level=risk_level,
        risk_score=score,
        drivers=drivers,
    )


async def rank_tenant_collections(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    today: date | None = None,
    only_with_outstanding: bool = True,
) -> list[ClientRiskScore]:
    """Devuelve los clientes del tenant rankeados por risk_score descendente.

    Por defecto descarta clientes sin importe pendiente — el ranking es para
    decidir a quién perseguir, no para evaluar credit-worthiness genérico.
    """
    invoices_q = await db.execute(
        sa.select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
        )
    )
    invoices = list(invoices_q.scalars().all())

    by_client: dict[str, list[Invoice]] = {}
    clients_by_id: dict[str, Client] = {}
    for inv in invoices:
        if inv.client is None:
            continue
        by_client.setdefault(str(inv.client_id), []).append(inv)
        clients_by_id[str(inv.client_id)] = inv.client

    scores = [
        compute_client_risk(clients_by_id[cid], invs, today=today)
        for cid, invs in by_client.items()
    ]

    if only_with_outstanding:
        scores = [s for s in scores if s.unpaid_count > 0]

    scores.sort(key=lambda s: (-s.risk_score, -s.overdue_amount))
    return scores
