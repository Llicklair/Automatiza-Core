"""Calendario escalonado de recordatorios de cobro — F3.9.

Para cada factura emitida no cobrada, genera la secuencia esperada de
acciones según los días desde el vencimiento:

  - D-3:    aviso amable previo (friendly_pre)
  - D+0:    recordatorio el día del vencimiento (reminder_due)
  - D+15:   requerimiento (formal_d15)
  - D+30:   requerimiento formal con intereses de demora (formal_d30)

La función central es pura (sin DB) — devuelve los pasos y deja que la
capa de orquestación decida si enviarlos.

`invoices_due_for_reminder(db, tenant_id)` cruza el calendario con las
facturas reales y devuelve las que ESTE día necesitan recordatorio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.billing import Invoice


_PAID_STATUSES = ("paid", "reconciled", "settled", "cancelled", "voided")

# Tipo medio de interés de demora aplicable a operaciones comerciales
# (Ley 3/2004 art. 7 — referencia BCE + 8 puntos). Se actualiza
# semestralmente; aquí guardamos un default razonable para 2026.
INTERES_DEMORA_PCT_ANUAL = Decimal("12.50")

_TEMPLATES: dict[str, dict[str, str]] = {
    "friendly_pre": {
        "subject": "Recordatorio amable: factura {invoice_number} vence el {due_date}",
        "body": (
            "Hola {client_name},\n\n"
            "Te escribo para recordarte amablemente que la factura {invoice_number} "
            "por importe de {amount:.2f} € vence el próximo {due_date}.\n\n"
            "Si ya has procesado el pago, ignora este mensaje. Si no, gracias por "
            "atenderlo en plazo.\n\n"
            "Un saludo,\n{sender_name}"
        ),
    },
    "reminder_due": {
        "subject": "Factura {invoice_number} vence hoy",
        "body": (
            "Hola {client_name},\n\n"
            "La factura {invoice_number} por importe de {amount:.2f} € vence HOY ({due_date}).\n\n"
            "Si necesitas ayuda con el pago, indícamelo. En caso contrario, te agradezco "
            "que efectúes la transferencia hoy mismo.\n\n"
            "Un saludo,\n{sender_name}"
        ),
    },
    "formal_d15": {
        "subject": "Factura {invoice_number} vencida desde hace {days_overdue} días",
        "body": (
            "Hola {client_name},\n\n"
            "La factura {invoice_number} por importe de {amount:.2f} € sigue impagada "
            "desde el {due_date} ({days_overdue} días de demora).\n\n"
            "Te ruego que regularices la situación esta semana. Si hay alguna "
            "incidencia, contáctame para gestionarla.\n\n"
            "Un saludo,\n{sender_name}"
        ),
    },
    "formal_d30": {
        "subject": "ÚLTIMO requerimiento — factura {invoice_number} ({days_overdue} días de demora)",
        "body": (
            "Hola {client_name},\n\n"
            "La factura {invoice_number} por importe de {amount:.2f} € lleva "
            "{days_overdue} días vencida sin abonar.\n\n"
            "Conforme a la Ley 3/2004 de lucha contra la morosidad, a partir de "
            "esta comunicación se aplica el interés legal de demora "
            "({interest_pct:.2f}% anual, ≈ {interest_amount:.2f} €).\n\n"
            "Te requiero el pago en los próximos 7 días naturales. En caso "
            "contrario, derivaremos el cobro al procedimiento monitorio.\n\n"
            "Un saludo,\n{sender_name}"
        ),
    },
}


@dataclass
class ReminderStep:
    invoice_id: str
    invoice_number: str | None
    client_id: str | None
    client_name: str | None
    client_email: str | None
    amount: float
    due_date: date
    step: str  # "friendly_pre" | "reminder_due" | "formal_d15" | "formal_d30"
    fire_date: date
    days_overdue: int
    subject: str
    body: str
    interest_amount: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "invoice_id": self.invoice_id,
            "invoice_number": self.invoice_number,
            "client_id": self.client_id,
            "client_name": self.client_name,
            "client_email": self.client_email,
            "amount": round(self.amount, 2),
            "due_date": self.due_date.isoformat(),
            "step": self.step,
            "fire_date": self.fire_date.isoformat(),
            "days_overdue": self.days_overdue,
            "subject": self.subject,
            "body": self.body,
            "interest_amount": round(self.interest_amount, 2),
        }


def _safe_date(d) -> date | None:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return None


def build_reminder_schedule(
    invoice: Invoice, *, today: date | None = None, sender_name: str = "Tu equipo"
) -> list[ReminderStep]:
    """Devuelve los pasos planificados para esta factura, ordenados por fire_date."""
    today = today or date.today()
    due = _safe_date(invoice.due_date)
    if due is None:
        return []
    if (invoice.status or "").lower() in _PAID_STATUSES:
        return []

    client = invoice.client
    client_email = getattr(client, "email", None) if client is not None else None
    client_name = client.name if client is not None else "Cliente"
    amount = float(invoice.amount_total or 0)

    schedule = [
        ("friendly_pre", due - timedelta(days=3)),
        ("reminder_due", due),
        ("formal_d15", due + timedelta(days=15)),
        ("formal_d30", due + timedelta(days=30)),
    ]

    steps: list[ReminderStep] = []
    for step_code, fire_date in schedule:
        days_overdue = max(0, (fire_date - due).days)
        interest_amount = 0.0
        if step_code == "formal_d30":
            interest_amount = float(
                Decimal(amount)
                * INTERES_DEMORA_PCT_ANUAL
                / Decimal(100)
                * Decimal(days_overdue)
                / Decimal(365)
            )

        ctx = {
            "client_name": client_name,
            "invoice_number": invoice.invoice_number or "—",
            "amount": amount,
            "due_date": due.isoformat(),
            "days_overdue": days_overdue,
            "interest_pct": float(INTERES_DEMORA_PCT_ANUAL),
            "interest_amount": interest_amount,
            "sender_name": sender_name,
        }
        tpl = _TEMPLATES[step_code]
        steps.append(
            ReminderStep(
                invoice_id=str(invoice.id),
                invoice_number=invoice.invoice_number,
                client_id=str(invoice.client_id) if invoice.client_id else None,
                client_name=client_name,
                client_email=client_email,
                amount=amount,
                due_date=due,
                step=step_code,
                fire_date=fire_date,
                days_overdue=days_overdue,
                subject=tpl["subject"].format(**ctx),
                body=tpl["body"].format(**ctx),
                interest_amount=interest_amount,
            )
        )

    steps.sort(key=lambda s: s.fire_date)
    return steps


async def invoices_due_for_reminder(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    today: date | None = None,
    sender_name: str = "Tu equipo",
) -> list[ReminderStep]:
    """Devuelve la lista de recordatorios cuyo `fire_date` cae HOY.

    Pensado para que un cron diario los procese: por cada paso devuelto,
    la capa de orquestación llama al email_sender y registra el envío.
    """
    today = today or date.today()
    invoices_q = await db.execute(
        sa.select(Invoice)
        .options(selectinload(Invoice.client))
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
            Invoice.due_date.is_not(None),
            ~Invoice.status.in_(_PAID_STATUSES),
        )
    )
    out: list[ReminderStep] = []
    for inv in invoices_q.scalars().all():
        schedule = build_reminder_schedule(inv, today=today, sender_name=sender_name)
        for step in schedule:
            if step.fire_date == today:
                out.append(step)
    return out
