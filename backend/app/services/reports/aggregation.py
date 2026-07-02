"""Aggregation logic for company snapshots and period parsing.

Extracted from api/v1/routes/reports/_helpers.py — pure business logic,
no HTTP/FastAPI dependency.
"""

import logging
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    BankTransaction,
    Client,
    Employee,
    Invoice,
    Payroll,
)
from app.services.analytics import DEMO_TX_PREFIX
from app.services.billing.constants import EMITTED_INVOICE_TYPES
from app.services.reports._schemas import (
    CompanySnapshot,
    SnapshotSectionBanking,
    SnapshotSectionClients,
    SnapshotSectionHR,
    SnapshotSectionInvoices,
)

_logger = logging.getLogger(__name__)


# ─── Period parsing ──────────────────────────────────────────────────────────


def parse_month(month: str) -> tuple[date, date]:
    """Devuelve (inicio_mes, fin_mes) a partir de 'YYYY-MM'.

    Raises ValueError on bad format (callers map to HTTPException if needed).
    """
    try:
        year, mon = map(int, month.split("-"))
        start = date(year, mon, 1)
        last_day = monthrange(year, mon)[1]
        end = date(year, mon, last_day)
        return start, end
    except Exception as exc:
        raise ValueError("Formato de mes invalido. Usa YYYY-MM.") from exc


def parse_period(period: str) -> tuple[date, date, str]:
    """Parsea periodo: 'YYYY-MM' (mensual) o 'YYYY-Q1..Q4' (trimestral).

    Returns (start, end, label). Raises ValueError on bad format.
    """
    try:
        if "-Q" in period.upper():
            year, q = period.upper().split("-Q")
            year, q = int(year), int(q)
            if q < 1 or q > 4:
                raise ValueError
            quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
            m_start, m_end = quarter_months[q]
            start = date(year, m_start, 1)
            end = date(year, m_end, monthrange(year, m_end)[1])
            label = f"T{q} {year}"
            return start, end, label
        else:
            start, end = parse_month(period)
            months = [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Septiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ]
            label = f"{months[start.month - 1]} {start.year}"
            return start, end, label
    except (ValueError, IndexError) as exc:
        raise ValueError("Formato de periodo invalido. Usa YYYY-MM o YYYY-Q1..Q4.") from exc


# ─── Report text builder ────────────────────────────────────────────────────


def build_report_text(snap: CompanySnapshot, company_name: str) -> str:
    """Construye el texto estructurado del informe mensual."""
    f = snap.facturas
    b = snap.banca
    h = snap.rrhh
    c = snap.clientes

    lines = [
        f"INFORME MENSUAL — {snap.month}",
        f"Empresa: {company_name}",
        f"Generado: {snap.generated_at.strftime('%d/%m/%Y %H:%M')}",
        "",
        "═══════════════════════════════════════",
        "  RESUMEN EJECUTIVO",
        "═══════════════════════════════════════",
        snap.resumen_ejecutivo,
        "",
        "═══════════════════════════════════════",
        "  1. FACTURACION E INGRESOS",
        "═══════════════════════════════════════",
        f"  Ingresos (facturas emitidas):   {f.ingresos_total:,.2f} €",
        f"  Gastos (facturas recibidas):    {f.gastos_total:,.2f} €",
        f"  Margen bruto:                   {f.margen_bruto:,.2f} € ({f.margen_pct:.1f}%)",
        f"  Facturas emitidas:              {f.facturas_emitidas}",
        f"  Facturas recibidas:             {f.facturas_recibidas}",
        f"  Pendiente de cobro:             {f.facturas_pendientes_cobro} facturas · {f.importe_pendiente_cobro:,.2f} €",
        "",
        "═══════════════════════════════════════",
        "  2. POSICION BANCARIA",
        "═══════════════════════════════════════",
        f"  Total entradas:                 {b.total_ingresos:,.2f} €",
        f"  Total salidas:                  {b.total_gastos:,.2f} €",
        f"  Saldo neto del mes:             {b.saldo_neto:,.2f} €",
        f"  Movimientos registrados:        {b.transacciones}",
        f"  Reconciliados:                  {b.reconciliadas}",
        "",
        "═══════════════════════════════════════",
        "  3. RECURSOS HUMANOS",
        "═══════════════════════════════════════",
        f"  Empleados activos:              {h.empleados_activos}",
        f"  Coste total nominas:            {h.coste_nominas:,.2f} €",
        f"  Nominas pagadas:                {h.nominas_pagadas}",
        f"  Nominas pendientes:             {h.nominas_pendientes}",
        "",
        "═══════════════════════════════════════",
        "  4. ANALISIS DE CLIENTES",
        "═══════════════════════════════════════",
        f"  Clientes totales:               {c.total_clientes}",
        f"  Nuevos este periodo:            {c.nuevos_periodo}",
    ]

    if c.top_client_name:
        lines.append(f"  Cliente principal:              {c.top_client_name} ({c.top_client_amount:,.2f} €)")

    lines += [
        "",
        "═══════════════════════════════════════",
        "  AutomatizaCore — Informe generado por IA",
        "═══════════════════════════════════════",
    ]

    return "\n".join(lines)


# ─── Main aggregation ────────────────────────────────────────────────────────


async def aggregate(db: AsyncSession, tenant_id: uuid.UUID, start: date, end: date) -> CompanySnapshot:
    """Agrega datos de la empresa para un rango de fechas y genera snapshot."""
    from app.services.reports.summaries import generate_resumen_ejecutivo

    month_str = start.strftime("%Y-%m")

    # ── Facturas ──
    inv_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    invoices = inv_q.scalars().all()

    # Emitidas = issued + rectificativas (conjunto canónico, ver billing/constants):
    # los abonos llevan importe negativo y netean ingresos/top-clientes, igual que
    # en analytics — antes este informe los excluía y sobreestimaba los ingresos.
    issued = [i for i in invoices if i.invoice_type in EMITTED_INVOICE_TYPES]
    received = [i for i in invoices if i.invoice_type == "received"]
    pending_issued = [i for i in issued if i.status in ("draft", "pending")]

    ingresos = sum(float(i.amount_total or 0) for i in issued)
    gastos = sum(float(i.amount_total or 0) for i in received)
    margen = ingresos - gastos
    margen_pct = round((margen / ingresos) * 100, 1) if ingresos > 0 else 0.0

    fact_section = SnapshotSectionInvoices(
        ingresos_total=ingresos,
        gastos_total=gastos,
        margen_bruto=margen,
        margen_pct=margen_pct,
        facturas_emitidas=len(issued),
        facturas_recibidas=len(received),
        facturas_pendientes_cobro=len(pending_issued),
        importe_pendiente_cobro=sum(float(i.amount_total or 0) for i in pending_issued),
    )

    # ── Banca (excluye datos demo) ──
    tx_q = await db.execute(
        select(BankTransaction).where(
            and_(
                BankTransaction.tenant_id == tenant_id,
                BankTransaction.date >= start,
                BankTransaction.date <= end,
                not_(BankTransaction.description.like(f"{DEMO_TX_PREFIX}%")),
            )
        )
    )
    txs = tx_q.scalars().all()

    bank_in = sum(float(t.amount) for t in txs if float(t.amount) > 0)
    bank_out = abs(sum(float(t.amount) for t in txs if float(t.amount) < 0))
    reconciled = sum(1 for t in txs if t.status == "reconciled")

    bank_section = SnapshotSectionBanking(
        total_ingresos=bank_in,
        total_gastos=bank_out,
        saldo_neto=bank_in - bank_out,
        transacciones=len(txs),
        reconciliadas=reconciled,
    )

    # ── RRHH ──
    emp_q = await db.execute(select(Employee).where(and_(Employee.tenant_id == tenant_id, Employee.status == "active")))
    employees = emp_q.scalars().all()

    payroll_q = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == tenant_id,
                func.date(Payroll.period_start) >= start,
                func.date(Payroll.period_end) <= end,
            )
        )
    )
    payrolls = payroll_q.scalars().all()

    coste_nominas = sum(float(p.net_salary or 0) for p in payrolls)
    paid_payrolls = [p for p in payrolls if p.status == "paid"]

    hr_section = SnapshotSectionHR(
        empleados_activos=len(employees),
        coste_nominas=coste_nominas,
        nominas_pagadas=len(paid_payrolls),
        nominas_pendientes=len(payrolls) - len(paid_payrolls),
    )

    # ── Clientes (desde facturas del periodo agrupadas) ──
    client_totals: dict[str, float] = {}
    for inv in issued:
        cid = str(inv.client_id) if inv.client_id else "desconocido"
        client_totals[cid] = client_totals.get(cid, 0) + float(inv.amount_total or 0)

    top_client_id = max(client_totals, key=client_totals.get) if client_totals else None
    top_amount = client_totals[top_client_id] if top_client_id else 0.0

    top_client_name = None
    if top_client_id and top_client_id != "desconocido":
        cl_q = await db.execute(select(Client).where(Client.id == uuid.UUID(top_client_id)))
        cl = cl_q.scalar_one_or_none()
        if cl:
            top_client_name = cl.name

    unique_client_ids = {str(i.client_id) for i in issued if i.client_id}

    new_clients = 0
    if unique_client_ids:
        nc_q = await db.execute(
            select(func.count())
            .select_from(Client)
            .where(
                and_(
                    Client.tenant_id == tenant_id,
                    func.date(Client.created_at) >= start,
                    func.date(Client.created_at) <= end,
                )
            )
        )
        new_clients = nc_q.scalar() or 0

    total_q = await db.execute(select(func.count()).select_from(Client).where(Client.tenant_id == tenant_id))
    total_clients = total_q.scalar() or 0

    client_section = SnapshotSectionClients(
        total_clientes=total_clients,
        nuevos_periodo=new_clients,
        top_client_name=top_client_name,
        top_client_amount=top_amount,
    )

    # ── Resumen ejecutivo (intenta IA, fallback determinista) ──
    resumen = await generate_resumen_ejecutivo(
        month_str,
        ingresos,
        gastos,
        margen,
        margen_pct,
        fact_section,
        hr_section,
        bank_section,
        coste_nominas,
        total_clients,
        new_clients,
        top_client_name,
        top_amount,
    )

    return CompanySnapshot(
        month=month_str,
        generated_at=datetime.now(UTC),
        facturas=fact_section,
        banca=bank_section,
        rrhh=hr_section,
        clientes=client_section,
        resumen_ejecutivo=resumen,
    )
