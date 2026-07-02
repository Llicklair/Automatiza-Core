"""
Contabilidad automatica PGC — genera asientos contables deterministas
para facturas y nominas segun el Plan General de Contabilidad español.

Todas las funciones son idempotentes: si ya existe un asiento para la
entidad, retornan None sin crear duplicados.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import JournalEntry
from app.services.billing.accounting import create_journal_entry

logger = logging.getLogger(__name__)

PGC = {
    "clientes": ("430", "Clientes"),
    "ventas": ("700", "Ventas de mercaderías"),
    "iva_repercutido": ("477", "Hacienda Pública, IVA repercutido"),
    "iva_soportado": ("472", "Hacienda Pública, IVA soportado"),
    "proveedores": ("400", "Proveedores"),
    "compras": ("600", "Compras de mercaderías"),
    "bancos": ("572", "Bancos c/c vista"),
    "sueldos": ("640", "Sueldos y salarios"),
    "ss_empresa": ("642", "Seguridad Social a cargo de la empresa"),
    "ss_acreedora": ("476", "Organismos de la Seguridad Social, acreedores"),
    "irpf_retenido": ("4751", "Hacienda Pública, acreedora por retenciones"),
    "remuneraciones_ptes": ("465", "Remuneraciones pendientes de pago"),
}


def _line(key: str, debit: float = 0, credit: float = 0) -> dict:
    code, name = PGC[key]
    return {"account_code": code, "account_name": name, "debit": debit, "credit": credit}


async def _has_entry(db: AsyncSession, tenant_id: UUID, **kwargs) -> bool:
    q = select(JournalEntry.id).where(JournalEntry.tenant_id == tenant_id)
    for k, v in kwargs.items():
        q = q.where(getattr(JournalEntry, k) == v)
    result = await db.execute(q.limit(1))
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Facturas
# ---------------------------------------------------------------------------


async def create_invoice_journal_entry(db, tenant_id, invoice) -> JournalEntry | None:
    if await _has_entry(db, tenant_id, invoice_id=invoice.id):
        return None

    total = float(invoice.amount_total)
    base = float(invoice.amount_base)
    tax = float(invoice.tax_amount or 0)

    if invoice.invoice_type == "issued":
        lines = [_line("clientes", debit=total)]
        if base:
            lines.append(_line("ventas", credit=base))
        if tax:
            lines.append(_line("iva_repercutido", credit=tax))
        desc = f"Factura emitida {invoice.invoice_number}"
    else:
        lines = []
        if base:
            lines.append(_line("compras", debit=base))
        if tax:
            lines.append(_line("iva_soportado", debit=tax))
        lines.append(_line("proveedores", credit=total))
        desc = f"Factura recibida {invoice.invoice_number}"

    return await create_journal_entry(
        db,
        tenant_id,
        date=invoice.date or datetime.now(UTC),
        description=desc,
        reference_id=f"INV-{invoice.id}",
        lines=lines,
        invoice_id=invoice.id,
    )


async def create_invoice_payment_entry(db, tenant_id, invoice) -> JournalEntry | None:
    # Idempotencia: el asiento de DEVENGO comparte invoice_id, así que hay que
    # deduplicar por reference_id (no por invoice_id). Sin esta guarda, re-conciliar
    # una factura ya pagada (reconcile manual + acción aprobable) duplicaba el
    # asiento de cobro 572/430 en la contabilidad (B1/B5).
    if await _has_entry(db, tenant_id, reference_id=f"PAY-INV-{invoice.id}"):
        return None

    total = float(invoice.amount_total)

    if invoice.invoice_type == "issued":
        lines = [
            _line("bancos", debit=total),
            _line("clientes", credit=total),
        ]
        desc = f"Cobro factura {invoice.invoice_number}"
    else:
        lines = [
            _line("proveedores", debit=total),
            _line("bancos", credit=total),
        ]
        desc = f"Pago factura {invoice.invoice_number}"

    return await create_journal_entry(
        db,
        tenant_id,
        date=datetime.now(UTC),
        description=desc,
        reference_id=f"PAY-INV-{invoice.id}",
        lines=lines,
        invoice_id=invoice.id,
    )


# ---------------------------------------------------------------------------
# Nominas
# ---------------------------------------------------------------------------


async def create_payroll_journal_entry(db, tenant_id, payroll) -> JournalEntry | None:
    if await _has_entry(db, tenant_id, payroll_id=payroll.id):
        return None

    gross = float(payroll.gross_salary or payroll.base_salary or 0)
    ss_total = sum(
        float(getattr(payroll, f, 0) or 0)
        for f in ("ss_contingencias_comunes", "ss_desempleo", "ss_formacion_profesional", "ss_mei")
    )
    # Cuota patronal de SS (642): coste real de la empresa, NO parte del bruto del
    # trabajador. Se lee de cuotas_empresa_json ({cc, at_ep, desempleo, fogasa,
    # fp, mei}); la 476 acreedora recoge worker + empresa (total a pagar a la TGSS).
    cuotas = payroll.cuotas_empresa_json or {}
    ss_empresa = sum(float(v or 0) for v in cuotas.values()) if isinstance(cuotas, dict) else 0.0
    irpf = float(payroll.irpf or 0)
    net = float(payroll.net_salary or 0)

    lines = [_line("sueldos", debit=gross)]
    if ss_empresa > 0:
        lines.append(_line("ss_empresa", debit=ss_empresa))
    if ss_total + ss_empresa > 0:
        lines.append(_line("ss_acreedora", credit=ss_total + ss_empresa))
    if irpf > 0:
        lines.append(_line("irpf_retenido", credit=irpf))
    lines.append(_line("remuneraciones_ptes", credit=net))

    emp_name = payroll.employee.name if payroll.employee else "Empleado"
    period = payroll.period_start.strftime("%m/%Y") if payroll.period_start else ""

    return await create_journal_entry(
        db,
        tenant_id,
        date=payroll.issue_date or datetime.now(UTC),
        description=f"Nómina {emp_name} {period}",
        reference_id=f"PAY-{payroll.id}",
        lines=lines,
        payroll_id=payroll.id,
    )


async def create_payroll_payment_entry(db, tenant_id, payroll) -> JournalEntry | None:
    # Idempotencia por reference_id (el asiento de devengo comparte payroll_id).
    if await _has_entry(db, tenant_id, reference_id=f"PAY-NOM-{payroll.id}"):
        return None

    net = float(payroll.net_salary or 0)
    emp_name = payroll.employee.name if payroll.employee else "Empleado"
    period = payroll.period_start.strftime("%m/%Y") if payroll.period_start else ""

    return await create_journal_entry(
        db,
        tenant_id,
        date=datetime.now(UTC),
        description=f"Pago nómina {emp_name} {period}",
        reference_id=f"PAY-NOM-{payroll.id}",
        lines=[
            _line("remuneraciones_ptes", debit=net),
            _line("bancos", credit=net),
        ],
        payroll_id=payroll.id,
    )
