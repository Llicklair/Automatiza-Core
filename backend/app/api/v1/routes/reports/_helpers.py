"""Shared helpers, constants, and aggregation logic for reports endpoints."""

import logging
import os
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import (
    BankTransaction,
    Client,
    Employee,
    Invoice,
    Payroll,
)

from ._schemas import (
    CompanySnapshot,
    FiscalIRPF,
    FiscalIS,
    FiscalIVA,
    FiscalSnapshot,
    SnapshotSectionBanking,
    SnapshotSectionClients,
    SnapshotSectionHR,
    SnapshotSectionInvoices,
)

_logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "uploads"))


# ─── Period parsing ──────────────────────────────────────────────────────────

def _parse_month(month: str) -> tuple[date, date]:
    """Devuelve (inicio_mes, fin_mes) a partir de 'YYYY-MM'."""
    try:
        year, mon = map(int, month.split("-"))
        start = date(year, mon, 1)
        last_day = monthrange(year, mon)[1]
        end = date(year, mon, last_day)
        return start, end
    except Exception:
        raise HTTPException(status_code=400, detail="Formato de mes inválido. Usa YYYY-MM.")


def _parse_period(period: str) -> tuple[date, date, str]:
    """Parsea periodo: 'YYYY-MM' (mensual) o 'YYYY-Q1..Q4' (trimestral).
    Devuelve (start, end, label)."""
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
            start, end = _parse_month(period)
            months = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                       "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
            label = f"{months[start.month - 1]} {start.year}"
            return start, end, label
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Formato de periodo inválido. Usa YYYY-MM o YYYY-Q1..Q4.")


# ─── Report text builder ────────────────────────────────────────────────────

def _build_report_text(snap: CompanySnapshot, company_name: str) -> str:
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
        "  1. FACTURACIÓN E INGRESOS",
        "═══════════════════════════════════════",
        f"  Ingresos (facturas emitidas):   {f.ingresos_total:,.2f} €",
        f"  Gastos (facturas recibidas):    {f.gastos_total:,.2f} €",
        f"  Margen bruto:                   {f.margen_bruto:,.2f} € ({f.margen_pct:.1f}%)",
        f"  Facturas emitidas:              {f.facturas_emitidas}",
        f"  Facturas recibidas:             {f.facturas_recibidas}",
        f"  Pendiente de cobro:             {f.facturas_pendientes_cobro} facturas · {f.importe_pendiente_cobro:,.2f} €",
        "",
        "═══════════════════════════════════════",
        "  2. POSICIÓN BANCARIA",
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
        f"  Coste total nóminas:            {h.coste_nominas:,.2f} €",
        f"  Nóminas pagadas:                {h.nominas_pagadas}",
        f"  Nóminas pendientes:             {h.nominas_pendientes}",
        "",
        "═══════════════════════════════════════",
        "  4. ANÁLISIS DE CLIENTES",
        "═══════════════════════════════════════",
        f"  Clientes totales:               {c.total_clientes}",
        f"  Nuevos este período:            {c.nuevos_periodo}",
    ]

    if c.top_client_name:
        lines.append(f"  Cliente principal:              {c.top_client_name} ({c.top_client_amount:,.2f} €)")

    lines += [
        "",
        "═══════════════════════════════════════",
        "  AutomatizaPyme — Informe generado por IA",
        "═══════════════════════════════════════",
    ]

    return "\n".join(lines)


# ─── Resumen ejecutivo: IA + fallback determinista ───────────────────────────

def _build_deterministic_resumen(
    month_str, ingresos, gastos, margen, margen_pct,
    fact_section, hr_section, bank_section, coste_nominas,
    total_clients, new_clients, top_client_name, top_amount,
) -> str:
    tendencia = "positiva" if margen > 0 else "negativa" if margen < 0 else "neutra"
    resumen = (
        f"El mes {month_str} presenta una tendencia {tendencia}. "
        f"La empresa facturó {ingresos:,.2f} € en ingresos con un margen bruto del {margen_pct:.1f}%. "
    )
    if fact_section.facturas_pendientes_cobro > 0:
        resumen += (
            f"Quedan {fact_section.facturas_pendientes_cobro} facturas pendientes de cobro "
            f"por un importe de {fact_section.importe_pendiente_cobro:,.2f} €. "
        )
    if hr_section.empleados_activos > 0:
        resumen += (
            f"La plantilla activa es de {hr_section.empleados_activos} empleados "
            f"con un coste de nóminas de {coste_nominas:,.2f} €. "
        )
    if bank_section.transacciones > 0:
        resumen += f"Se registraron {bank_section.transacciones} movimientos bancarios. "
    if new_clients > 0:
        resumen += f"Se captaron {new_clients} clientes nuevos (total: {total_clients}). "
    if top_client_name:
        resumen += f"El cliente principal fue {top_client_name} ({top_amount:,.2f} €)."
    return resumen.strip()


async def _generate_resumen_ejecutivo(
    month_str, ingresos, gastos, margen, margen_pct,
    fact_section, hr_section, bank_section, coste_nominas,
    total_clients, new_clients, top_client_name, top_amount,
) -> str:
    """Genera resumen ejecutivo con IA. Si falla (sin tokens, timeout), usa determinista."""
    deterministic = _build_deterministic_resumen(
        month_str, ingresos, gastos, margen, margen_pct,
        fact_section, hr_section, bank_section, coste_nominas,
        total_clients, new_clients, top_client_name, top_amount,
    )

    try:
        from app.core.llm_factory import get_llm
        llm = get_llm(temperature=0.3, max_tokens=600)

        prompt = (
            "Eres el director financiero de una PYME española. "
            "Redacta un resumen ejecutivo de 3-5 frases del mes para el CEO, "
            "en tono profesional pero accesible. Incluye tendencia, riesgos y recomendaciones. "
            "No inventes datos, usa SOLO los proporcionados.\n\n"
            f"MES: {month_str}\n"
            f"INGRESOS: {ingresos:,.2f} €  |  GASTOS: {gastos:,.2f} €  |  MARGEN: {margen:,.2f} € ({margen_pct:.1f}%)\n"
            f"FACTURAS EMITIDAS: {fact_section.facturas_emitidas}  |  RECIBIDAS: {fact_section.facturas_recibidas}\n"
            f"PENDIENTES COBRO: {fact_section.facturas_pendientes_cobro} facturas ({fact_section.importe_pendiente_cobro:,.2f} €)\n"
            f"EMPLEADOS: {hr_section.empleados_activos}  |  NÓMINAS: {coste_nominas:,.2f} €\n"
            f"MOVIMIENTOS BANCARIOS: {bank_section.transacciones}  |  SALDO NETO: {bank_section.saldo_neto:,.2f} €\n"
            f"CLIENTES: {total_clients} (nuevos: {new_clients})"
            + (f"  |  TOP: {top_client_name} ({top_amount:,.2f} €)" if top_client_name else "")
            + "\n\nResponde SOLO el texto del resumen, sin encabezados ni formato."
        )

        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        ai_resumen = response.content.strip()

        if len(ai_resumen) > 50:
            _logger.info("[REPORTS] Resumen ejecutivo generado por IA")
            return ai_resumen

    except Exception as e:
        _logger.warning("[REPORTS] IA no disponible para resumen, usando determinista: %s", e)

    return deterministic


async def _generate_resumen_fiscal(period: str, label: str, iva: FiscalIVA, irpf: FiscalIRPF, is_: FiscalIS) -> str:
    """Resumen ejecutivo fiscal con IA, fallback determinista."""
    resultado_iva = iva.resultado_iva
    estado_iva = "a ingresar" if resultado_iva > 0 else "a compensar/devolver" if resultado_iva < 0 else "neutro"

    deterministic = (
        f"Periodo {label}: IVA repercutido {iva.total_repercutido:,.2f} € vs soportado {iva.total_soportado:,.2f} €, "
        f"resultado {estado_iva} de {abs(resultado_iva):,.2f} €. "
        f"Retenciones IRPF: {irpf.total_retenciones:,.2f} €. "
        f"Estimación IS: base imponible {is_.base_imponible:,.2f} €, cuota estimada {is_.cuota_estimada:,.2f} € (tipo {is_.tipo_estimado:.0f}%)."
    )

    try:
        from app.core.llm_factory import get_llm
        llm = get_llm(temperature=0.3, max_tokens=600)

        prompt = (
            "Eres el asesor fiscal de una PYME española. "
            "Redacta un resumen fiscal de 3-5 frases para el CEO, "
            "en tono profesional. Incluye obligaciones fiscales próximas, riesgos y recomendaciones. "
            "No inventes datos, usa SOLO los proporcionados.\n\n"
            f"PERIODO: {label}\n"
            f"IVA REPERCUTIDO: {iva.total_repercutido:,.2f} € (base: {iva.base_repercutido:,.2f} €)\n"
            f"IVA SOPORTADO: {iva.total_soportado:,.2f} € (base: {iva.base_soportado:,.2f} €)\n"
            f"RESULTADO IVA: {resultado_iva:,.2f} € ({estado_iva})\n"
            f"IRPF RETENCIONES NÓMINAS: {irpf.retenciones_nominas:,.2f} €\n"
            f"IS — INGRESOS: {is_.ingresos_brutos:,.2f} €  |  GASTOS DEDUCIBLES: {is_.gastos_deducibles:,.2f} €\n"
            f"IS — BASE IMPONIBLE: {is_.base_imponible:,.2f} €  |  CUOTA ESTIMADA: {is_.cuota_estimada:,.2f} €\n"
            "\nResponde SOLO el texto del resumen, sin encabezados ni formato."
        )

        from langchain_core.messages import HumanMessage
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        ai_resumen = response.content.strip()
        if len(ai_resumen) > 50:
            return ai_resumen
    except Exception as e:
        _logger.warning("[REPORTS] IA no disponible para resumen fiscal: %s", e)

    return deterministic


# ─── Aggregation logic ───────────────────────────────────────────────────────

async def _aggregate(db: AsyncSession, tenant_id: uuid.UUID, start: date, end: date) -> CompanySnapshot:
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

    issued = [i for i in invoices if i.invoice_type == "issued"]
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

    # ── Banca ──
    tx_q = await db.execute(
        select(BankTransaction).where(
            and_(
                BankTransaction.tenant_id == tenant_id,
                BankTransaction.date >= start,
                BankTransaction.date <= end,
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
    emp_q = await db.execute(
        select(Employee).where(
            and_(Employee.tenant_id == tenant_id, Employee.status == "active")
        )
    )
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

    # ── Clientes (desde facturas del período agrupadas) ──
    client_totals: dict[str, float] = {}
    for inv in issued:
        cid = str(inv.client_id) if inv.client_id else "desconocido"
        client_totals[cid] = client_totals.get(cid, 0) + float(inv.amount_total or 0)

    top_client_id = max(client_totals, key=client_totals.get) if client_totals else None
    top_amount = client_totals[top_client_id] if top_client_id else 0.0

    # Buscar nombre del top client si existe
    top_client_name = None
    if top_client_id and top_client_id != "desconocido":
        cl_q = await db.execute(select(Client).where(Client.id == uuid.UUID(top_client_id)))
        cl = cl_q.scalar_one_or_none()
        if cl:
            top_client_name = cl.name

    # Clientes únicos con facturas en el período
    unique_client_ids = {str(i.client_id) for i in issued if i.client_id}

    # Clientes nuevos = creados en el período (aprox: primera factura en el período)
    new_clients = 0
    if unique_client_ids:
        nc_q = await db.execute(
            select(func.count()).select_from(Client).where(
                and_(
                    Client.tenant_id == tenant_id,
                    func.date(Client.created_at) >= start,
                    func.date(Client.created_at) <= end,
                )
            )
        )
        new_clients = nc_q.scalar() or 0

    # Total clientes del tenant
    total_q = await db.execute(
        select(func.count()).select_from(Client).where(Client.tenant_id == tenant_id)
    )
    total_clients = total_q.scalar() or 0

    client_section = SnapshotSectionClients(
        total_clientes=total_clients,
        nuevos_periodo=new_clients,
        top_client_name=top_client_name,
        top_client_amount=top_amount,
    )

    # ── Resumen ejecutivo (intenta IA, fallback determinista) ──
    resumen = await _generate_resumen_ejecutivo(
        month_str, ingresos, gastos, margen, margen_pct,
        fact_section, hr_section, bank_section, coste_nominas,
        total_clients, new_clients, top_client_name, top_amount,
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


# ─── Fiscal aggregation ─────────────────────────────────────────────────────

async def _aggregate_fiscal(db: AsyncSession, tenant_id: uuid.UUID, start: date, end: date, period: str, label: str) -> FiscalSnapshot:
    """Agrega datos fiscales: IVA por tipo, IRPF retenciones, IS estimado."""
    from sqlalchemy.orm import joinedload as jl

    # ── IVA: Repercutido (ventas/emitidas) ──
    issued_q = await db.execute(
        select(Invoice).where(and_(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "issued",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        ))
    )
    issued_invoices = issued_q.scalars().all()

    vat_rep: dict[float, float] = {}  # rate -> quota
    base_rep: dict[float, float] = {}  # rate -> base
    for inv in issued_invoices:
        lines_q = await db.execute(select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id))
        inv_wl = lines_q.unique().scalar_one()
        for line in (inv_wl.lines or []):
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            vat_rep[rate] = vat_rep.get(rate, 0) + base * rate / 100
            base_rep[rate] = base_rep.get(rate, 0) + base

    # ── IVA: Soportado (compras/recibidas) ──
    received_q = await db.execute(
        select(Invoice).where(and_(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_type == "received",
            func.date(Invoice.date) >= start,
            func.date(Invoice.date) <= end,
        ))
    )
    received_invoices = received_q.scalars().all()

    vat_sop: dict[float, float] = {}
    base_sop: dict[float, float] = {}
    for inv in received_invoices:
        lines_q = await db.execute(select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id))
        inv_wl = lines_q.unique().scalar_one()
        for line in (inv_wl.lines or []):
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            vat_sop[rate] = vat_sop.get(rate, 0) + base * rate / 100
            base_sop[rate] = base_sop.get(rate, 0) + base

    total_rep = round(sum(vat_rep.values()), 2)
    total_sop = round(sum(vat_sop.values()), 2)

    iva_section = FiscalIVA(
        repercutido_21=round(vat_rep.get(21, 0), 2),
        repercutido_10=round(vat_rep.get(10, 0), 2),
        repercutido_4=round(vat_rep.get(4, 0), 2),
        total_repercutido=total_rep,
        base_repercutido=round(sum(base_rep.values()), 2),
        soportado_21=round(vat_sop.get(21, 0), 2),
        soportado_10=round(vat_sop.get(10, 0), 2),
        soportado_4=round(vat_sop.get(4, 0), 2),
        total_soportado=total_sop,
        base_soportado=round(sum(base_sop.values()), 2),
        resultado_iva=round(total_rep - total_sop, 2),
    )

    # ── IRPF: Retenciones en nóminas ──
    payroll_q = await db.execute(
        select(Payroll).where(and_(
            Payroll.tenant_id == tenant_id,
            func.date(Payroll.period_start) >= start,
            func.date(Payroll.period_end) <= end,
        ))
    )
    payrolls = payroll_q.scalars().all()
    irpf_nominas = round(sum(float(p.irpf or 0) for p in payrolls), 2)

    irpf_section = FiscalIRPF(
        retenciones_nominas=irpf_nominas,
        retenciones_facturas=0.0,  # futuro: retenciones profesionales
        total_retenciones=irpf_nominas,
    )

    # ── IS: Estimación Impuesto de Sociedades ──
    ingresos_brutos = round(sum(float(i.amount_base or i.amount_total or 0) for i in issued_invoices), 2)
    gastos_deducibles = round(sum(float(i.amount_base or i.amount_total or 0) for i in received_invoices), 2)
    coste_nominas = round(sum(float(p.base_salary or 0) for p in payrolls), 2)
    gastos_total = gastos_deducibles + coste_nominas
    base_imponible = round(ingresos_brutos - gastos_total, 2)
    tipo = 25.0
    cuota = round(max(0, base_imponible) * tipo / 100, 2)

    is_section = FiscalIS(
        ingresos_brutos=ingresos_brutos,
        gastos_deducibles=round(gastos_total, 2),
        base_imponible=base_imponible,
        tipo_estimado=tipo,
        cuota_estimada=cuota,
    )

    # ── Resumen ejecutivo fiscal ──
    resumen = await _generate_resumen_fiscal(period, label, iva_section, irpf_section, is_section)

    return FiscalSnapshot(
        period=period,
        period_label=label,
        generated_at=datetime.now(UTC),
        iva=iva_section,
        irpf=irpf_section,
        impuesto_sociedades=is_section,
        resumen_ejecutivo=resumen,
    )
