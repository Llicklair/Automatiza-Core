"""Calendario unificado — agrega eventos de múltiples módulos."""
from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.billing import Invoice
from app.db.models.calendar import Event, Reservation
from app.db.models.hr import Payroll
from app.db.models.models import User
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/unified")
@limiter.limit("60/minute")
async def unified_calendar(
    request: Request,
    start: date = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end: date = Query(..., description="Fecha fin YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve todos los eventos del rango [start, end] agrupados de todos los módulos."""
    start_dt = datetime.combine(start, time.min).replace(tzinfo=UTC)
    end_dt = datetime.combine(end, time.max).replace(tzinfo=UTC)
    now = datetime.now(UTC)
    tid = current_user.tenant_id
    items: list[dict] = []

    # ── CRM Events ──────────────────────────────────────────────────────────
    ev_rows = await db.execute(
        select(Event)
        .options(selectinload(Event.client))
        .where(Event.tenant_id == tid, Event.start_time >= start_dt, Event.start_time <= end_dt)
    )
    for ev in ev_rows.scalars():
        items.append({
            "id": str(ev.id),
            "source": "event",
            "title": ev.title,
            "start": ev.start_time.isoformat(),
            "end": ev.end_time.isoformat() if ev.end_time else None,
            "color": "blue",
            "href": "/crm/calendario",
            "subtitle": ev.client.name if ev.client else ev.type,
        })

    # ── Reservations ────────────────────────────────────────────────────────
    res_rows = await db.execute(
        select(Reservation)
        .options(selectinload(Reservation.client))
        .where(
            Reservation.tenant_id == tid,
            Reservation.start_time >= start_dt,
            Reservation.start_time <= end_dt,
        )
    )
    for res in res_rows.scalars():
        items.append({
            "id": str(res.id),
            "source": "reservation",
            "title": f"Reserva · {res.client.name if res.client else '—'}",
            "start": res.start_time.isoformat(),
            "end": res.end_time.isoformat() if res.end_time else None,
            "color": "purple",
            "href": "/crm/reservas",
            "subtitle": res.status,
        })

    # ── Invoice due dates ────────────────────────────────────────────────────
    inv_rows = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tid,
            Invoice.due_date.is_not(None),
            Invoice.due_date >= start_dt,
            Invoice.due_date <= end_dt,
            Invoice.status.in_(["sent", "draft"]),
        )
    )
    for inv in inv_rows.scalars():
        overdue = inv.due_date < now if inv.due_date else False
        items.append({
            "id": str(inv.id),
            "source": "invoice_due",
            "title": f"Vto. {inv.invoice_number or 'S/N'}",
            "start": inv.due_date.isoformat(),
            "end": None,
            "color": "red" if overdue else "amber",
            "href": "/ventas/facturas",
            "subtitle": f"{inv.client.name if inv.client else '—'} · {float(inv.amount_total or 0):.2f} €",
        })

    # ── Payroll periods ──────────────────────────────────────────────────────
    pay_rows = await db.execute(
        select(Payroll).where(
            Payroll.tenant_id == tid,
            Payroll.period_start >= start_dt,
            Payroll.period_start <= end_dt,
        )
    )
    for p in pay_rows.scalars():
        items.append({
            "id": str(p.id),
            "source": "payroll",
            "title": "Período nómina",
            "start": p.period_start.isoformat(),
            "end": p.period_end.isoformat() if p.period_end else None,
            "color": "green",
            "href": "/rrhh/nominas",
            "subtitle": p.status,
        })

    items.sort(key=lambda x: x["start"])
    return items
