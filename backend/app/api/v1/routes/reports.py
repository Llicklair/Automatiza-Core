"""
Endpoint de informes: genera el snapshot mensual de la empresa y lo guarda como documento PDF.
GET  /api/v1/reports/company-snapshot?month=2026-03
POST /api/v1/reports/company-snapshot/generate  (genera y persiste el PDF)
GET  /api/v1/reports/                            (lista informes generados)
"""

import os
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import (
    BankTransaction,
    Client,
    Employee,
    Invoice,
    Payroll,
    Tenant,
    TenantDocument,
    User,
)
from app.services.pdf_service import (
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_modelo_303_pdf,
    generate_snapshot_pdf,
    generate_text_report_pdf,
)

router = APIRouter(prefix="/reports", tags=["reports"])

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SnapshotSectionInvoices(BaseModel):
    ingresos_total: float
    gastos_total: float
    margen_bruto: float
    margen_pct: float
    facturas_emitidas: int
    facturas_recibidas: int
    facturas_pendientes_cobro: int
    importe_pendiente_cobro: float


class SnapshotSectionBanking(BaseModel):
    total_ingresos: float
    total_gastos: float
    saldo_neto: float
    transacciones: int
    reconciliadas: int


class SnapshotSectionHR(BaseModel):
    empleados_activos: int
    coste_nominas: float
    nominas_pagadas: int
    nominas_pendientes: int


class SnapshotSectionClients(BaseModel):
    total_clientes: int
    nuevos_periodo: int
    top_client_name: str | None
    top_client_amount: float


class CompanySnapshot(BaseModel):
    month: str                       # "2026-03"
    generated_at: datetime
    facturas: SnapshotSectionInvoices
    banca: SnapshotSectionBanking
    rrhh: SnapshotSectionHR
    clientes: SnapshotSectionClients
    resumen_ejecutivo: str


class ReportOut(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    file_name: str
    file_size: int
    category: str | None
    created_at: datetime


# ─── Helpers ──────────────────────────────────────────────────────────────────

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


# ─── Resumen ejecutivo: IA + fallback determinista ────────────────────────────

import logging as _logging

_report_logger = _logging.getLogger(__name__)


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
            _report_logger.info("[REPORTS] Resumen ejecutivo generado por IA")
            return ai_resumen

    except Exception as e:
        _report_logger.warning("[REPORTS] IA no disponible para resumen, usando determinista: %s", e)

    return deterministic


# ─── Aggregation logic ────────────────────────────────────────────────────────

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
        from app.db.models.models import Client
        cl_q = await db.execute(select(Client).where(Client.id == uuid.UUID(top_client_id)))
        cl = cl_q.scalar_one_or_none()
        if cl:
            top_client_name = cl.name

    # Clientes únicos con facturas en el período
    unique_client_ids = {str(i.client_id) for i in issued if i.client_id}

    # Clientes nuevos = creados en el período (aprox: primera factura en el período)
    new_clients = 0
    if unique_client_ids:
        from app.db.models.models import Client
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
    from app.db.models.models import Client
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


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/company-snapshot", response_model=CompanySnapshot)
async def get_company_snapshot(
    month: str = Query(default=None, description="Mes en formato YYYY-MM. Por defecto: mes actual."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el snapshot agregado de la empresa para el mes indicado (sin generar PDF)."""
    if not month:
        today = date.today()
        month = today.strftime("%Y-%m")

    start, end = _parse_month(month)
    return await _aggregate(db, current_user.tenant_id, start, end)


@router.post("/company-snapshot/generate", response_model=ReportOut, status_code=201)
async def generate_company_snapshot_pdf(
    month: str = Query(default=None, description="Mes en formato YYYY-MM. Por defecto: mes actual."),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera el informe mensual PDF y lo guarda en documentos del tenant."""
    if not month:
        today = date.today()
        month = today.strftime("%Y-%m")

    start, end = _parse_month(month)

    # Obtener nombre de la empresa
    from app.db.models.models import Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_q.scalar_one_or_none()
    company_name = tenant.name if tenant and tenant.name else "Tu empresa"

    snap = await _aggregate(db, current_user.tenant_id, start, end)

    # Generar PDF con gráficas
    pdf_bytes = generate_snapshot_pdf(
        snap=snap.model_dump(),
        company_name=company_name,
        month=month,
    )

    # Guardar a disco
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_name = f"informe_{month}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as fh:
        fh.write(pdf_bytes)

    # Persistir en tenant_documents
    doc = TenantDocument(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        uploaded_by=current_user.id,
        file_name=file_name,
        file_type="application/pdf",
        file_path=file_path,
        file_size=len(pdf_bytes),
        status="processed",
        parsed_content=snap.resumen_ejecutivo,
        category="informes",
        created_at=datetime.now(UTC),
        processed_at=datetime.now(UTC),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/", response_model=list[ReportOut])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todos los informes mensuales generados para este tenant."""
    q = await db.execute(
        select(TenantDocument)
        .where(
            and_(
                TenantDocument.tenant_id == current_user.tenant_id,
                TenantDocument.category == "informes",
            )
        )
        .order_by(TenantDocument.created_at.desc())
    )
    return q.scalars().all()


@router.get("/{report_id}/download")
async def download_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga el PDF de un informe."""
    q = await db.execute(
        select(TenantDocument).where(
            and_(
                TenantDocument.id == report_id,
                TenantDocument.tenant_id == current_user.tenant_id,
                TenantDocument.category == "informes",
            )
        )
    )
    doc = q.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Informe no encontrado")
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="Archivo no disponible")

    return FileResponse(
        path=doc.file_path,
        media_type="application/pdf",
        filename=doc.file_name,
    )


# ─── Modelo 303 (Borrador IVA trimestral) ────────────────────────────────────

@router.get("/modelo-303")
async def generate_modelo_303(
    quarter: int = Query(ge=1, le=4, description="Trimestre (1-4)"),
    year: int = Query(default=2026, description="Año fiscal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera borrador PDF del Modelo 303 (liquidación trimestral de IVA)."""
    from fastapi.responses import Response

    # Calcular rango de fechas del trimestre
    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    m_start, m_end = quarter_months[quarter]
    start = date(year, m_start, 1)
    last_day = monthrange(year, m_end)[1]
    end = date(year, m_end, last_day)

    # Obtener tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    tenant_name = tenant_obj.name if tenant_obj else "Mi Empresa"
    tenant_nif = tenant_obj.nif if tenant_obj else "B00000000"

    # Agregar IVA devengado (ventas) — facturas emitidas
    issued_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "issued",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    issued_invoices = issued_q.scalars().all()

    # Agregar por tipo de IVA desde las líneas de factura
    from sqlalchemy.orm import joinedload as jl
    vat_collected_map: dict[float, dict] = {}
    for inv in issued_invoices:
        # Reload lines
        lines_q = await db.execute(
            select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
        )
        inv_with_lines = lines_q.unique().scalar_one()
        for line in (inv_with_lines.lines or []):
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            quota = base * rate / 100
            if rate not in vat_collected_map:
                vat_collected_map[rate] = {"rate": rate, "base": 0.0, "quota": 0.0}
            vat_collected_map[rate]["base"] += base
            vat_collected_map[rate]["quota"] += quota

    # IVA deducible (compras) — facturas recibidas
    received_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "received",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    received_invoices = received_q.scalars().all()

    vat_deducted_map: dict[float, dict] = {}
    for inv in received_invoices:
        lines_q = await db.execute(
            select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
        )
        inv_with_lines = lines_q.unique().scalar_one()
        for line in (inv_with_lines.lines or []):
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            quota = base * rate / 100
            if rate not in vat_deducted_map:
                vat_deducted_map[rate] = {"rate": rate, "base": 0.0, "quota": 0.0}
            vat_deducted_map[rate]["base"] += base
            vat_deducted_map[rate]["quota"] += quota

    # Round values
    for m in [vat_collected_map, vat_deducted_map]:
        for v in m.values():
            v["base"] = round(v["base"], 2)
            v["quota"] = round(v["quota"], 2)

    data = {
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "quarter": quarter,
        "year": year,
        "vat_collected": sorted(vat_collected_map.values(), key=lambda x: x["rate"], reverse=True),
        "vat_deducted": sorted(vat_deducted_map.values(), key=lambda x: x["rate"], reverse=True),
    }

    pdf_bytes = generate_modelo_303_pdf(data)
    file_name = f"Modelo303_Q{quarter}_{year}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Informe de Tesorería (Cash Flow) ────────────────────────────────────────

@router.get("/cashflow")
async def generate_cashflow(
    start: str = Query(description="Fecha inicio YYYY-MM-DD"),
    end: str = Query(description="Fecha fin YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de informe de tesorería / cash flow."""
    from fastapi.responses import Response

    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD.")

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas pendientes (cobros previstos)
    issued_pending_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "issued",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    issued_pending = issued_pending_q.scalars().all()

    # Facturas recibidas pendientes (pagos previstos)
    received_pending_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "received",
                Invoice.status.in_(["draft", "pending"]),
            )
        )
    )
    received_pending = received_pending_q.scalars().all()

    # Nóminas pendientes
    payroll_pending_q = await db.execute(
        select(Payroll).where(
            and_(
                Payroll.tenant_id == current_user.tenant_id,
                Payroll.status != "paid",
                func.date(Payroll.period_end) >= start_date,
                func.date(Payroll.period_end) <= end_date,
            )
        )
    )
    payrolls_pending = payroll_pending_q.scalars().all()

    total_collections = sum(float(i.amount_total or 0) for i in issued_pending)
    total_payments = sum(float(i.amount_total or 0) for i in received_pending) + \
                     sum(float(p.net_salary or 0) for p in payrolls_pending)

    # Group by month
    from collections import defaultdict
    monthly_coll = defaultdict(float)
    monthly_pay = defaultdict(float)

    for inv in issued_pending:
        d = inv.due_date or inv.date
        if d:
            key = d.strftime("%Y-%m")
            monthly_coll[key] += float(inv.amount_total or 0)

    for inv in received_pending:
        d = inv.due_date or inv.date
        if d:
            key = d.strftime("%Y-%m")
            monthly_pay[key] += float(inv.amount_total or 0)

    for p in payrolls_pending:
        key = p.period_end.strftime("%Y-%m") if p.period_end else ""
        if key:
            monthly_pay[key] += float(p.net_salary or 0)

    # Build periods
    all_months = sorted(set(list(monthly_coll.keys()) + list(monthly_pay.keys())))
    initial_balance = 0.0  # Could be enhanced with bank balance
    cumulative = initial_balance
    periods = []
    for m in all_months:
        c = round(monthly_coll.get(m, 0), 2)
        p = round(monthly_pay.get(m, 0), 2)
        cumulative += c - p
        periods.append({"label": m, "collections": c, "payments": p, "cumulative_balance": round(cumulative, 2)})

    # Pending receivables for detail
    from sqlalchemy.orm import joinedload as jl
    recv_detail = []
    for inv in sorted(issued_pending, key=lambda x: float(x.amount_total or 0), reverse=True)[:10]:
        inv_q = await db.execute(select(Invoice).options(jl(Invoice.client)).where(Invoice.id == inv.id))
        inv_full = inv_q.unique().scalar_one()
        recv_detail.append({
            "client_name": inv_full.client.name if inv_full.client else "—",
            "invoice_number": inv_full.invoice_number or str(inv_full.id)[:8],
            "due_date": (inv_full.due_date or inv_full.date).isoformat() if (inv_full.due_date or inv_full.date) else "",
            "amount": float(inv_full.amount_total or 0),
        })

    data = {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "period_start": start,
        "period_end": end,
        "initial_balance": initial_balance,
        "total_collections": round(total_collections, 2),
        "total_payments": round(total_payments, 2),
        "final_balance": round(initial_balance + total_collections - total_payments, 2),
        "periods": periods,
        "pending_receivables": recv_detail,
    }

    pdf_bytes = generate_cashflow_report_pdf(data)
    file_name = f"Tesoreria_{start}_{end}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Informe de Morosidad ───────────────────────────────────────────────────

@router.get("/delinquency")
async def generate_delinquency(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF de informe de morosidad (facturas vencidas impagadas)."""
    from fastapi.responses import Response
    from sqlalchemy.orm import joinedload as jl

    today = date.today()

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"

    # Facturas emitidas vencidas no pagadas
    overdue_q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client))
        .where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == "issued",
                Invoice.status.notin_(["paid", "cancelled"]),
                Invoice.due_date.isnot(None),
                func.date(Invoice.due_date) < today,
            )
        )
        .order_by(Invoice.due_date)
    )
    overdue_invoices = overdue_q.unique().scalars().all()

    # Build aging buckets
    buckets = {"0-30": {"count": 0, "amount": 0.0}, "31-60": {"count": 0, "amount": 0.0},
               "61-90": {"count": 0, "amount": 0.0}, ">90": {"count": 0, "amount": 0.0}}

    detail_list = []
    client_totals: dict[str, float] = {}
    total_days = 0

    for inv in overdue_invoices:
        days = (today - inv.due_date.date() if hasattr(inv.due_date, 'date') else today - inv.due_date).days
        amount = float(inv.amount_total or 0)

        if days <= 30:
            buckets["0-30"]["count"] += 1
            buckets["0-30"]["amount"] += amount
        elif days <= 60:
            buckets["31-60"]["count"] += 1
            buckets["31-60"]["amount"] += amount
        elif days <= 90:
            buckets["61-90"]["count"] += 1
            buckets["61-90"]["amount"] += amount
        else:
            buckets[">90"]["count"] += 1
            buckets[">90"]["amount"] += amount

        total_days += days
        client_name = inv.client.name if inv.client else "—"
        client_totals[client_name] = client_totals.get(client_name, 0) + amount

        detail_list.append({
            "client_name": client_name,
            "invoice_number": inv.invoice_number or str(inv.id)[:8],
            "due_date": inv.due_date.isoformat() if inv.due_date else "",
            "days_overdue": days,
            "amount": amount,
            "collection_status": "Pendiente",
        })

    # Round bucket amounts
    for b in buckets.values():
        b["amount"] = round(b["amount"], 2)

    total_overdue = sum(float(inv.amount_total or 0) for inv in overdue_invoices)
    num_overdue = len(overdue_invoices)
    avg_days = total_days / num_overdue if num_overdue > 0 else 0
    worst_client = max(client_totals, key=client_totals.get) if client_totals else "—"

    data = {
        "company": {"name": company_name, "nif": tenant_obj.nif if tenant_obj else ""},
        "cutoff_date": today.isoformat(),
        "total_overdue": round(total_overdue, 2),
        "num_overdue": num_overdue,
        "avg_days_overdue": round(avg_days, 1),
        "worst_client": worst_client,
        "aging_buckets": buckets,
        "overdue_invoices": sorted(detail_list, key=lambda x: x["days_overdue"], reverse=True),
    }

    pdf_bytes = generate_delinquency_report_pdf(data)
    file_name = f"Morosidad_{today.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Compliance: Registro RGPD ──────────────────────────────────────────────

@router.get("/compliance/rgpd-registry")
async def generate_rgpd_registry(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera PDF del registro de actividades de tratamiento RGPD (Art. 30)."""
    from fastapi.responses import Response
    from app.services.pdf_service import generate_rgpd_registry_pdf

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa"
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"

    # Actividades de tratamiento predefinidas para un ERP de PYME
    activities = [
        {
            "name": "Gestión de clientes y proveedores",
            "purpose": "Mantenimiento de la relación contractual, facturación, comunicaciones comerciales",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato",
            "data_subjects": "Clientes, proveedores, representantes legales",
            "data_categories": "Nombre, NIF/CIF, dirección, email, teléfono, datos bancarios",
            "recipients": "AEAT (obligación fiscal), entidades bancarias",
            "international_transfers": "No se realizan",
            "retention_period": "Duración de la relación contractual + 6 años (Art. 30 Código de Comercio)",
            "security_measures": "Control de acceso por roles, cifrado en tránsito (TLS), copias de seguridad",
        },
        {
            "name": "Gestión de recursos humanos",
            "purpose": "Gestión laboral, nóminas, prevención de riesgos, formación",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato laboral; Art. 6.1.c — Obligación legal",
            "data_subjects": "Empleados, candidatos",
            "data_categories": "Nombre, NIF, dirección, datos bancarios, nóminas, historial laboral",
            "recipients": "Seguridad Social, AEAT, mutua de accidentes",
            "international_transfers": "No se realizan",
            "retention_period": "Duración de la relación laboral + 4 años (prescripción laboral)",
            "security_measures": "Acceso restringido a RRHH, cifrado de nóminas, auditoría de accesos",
        },
        {
            "name": "Facturación y contabilidad",
            "purpose": "Emisión de facturas, gestión contable, cumplimiento fiscal",
            "legal_basis": "Art. 6.1.c RGPD — Obligación legal (Ley de IVA, Código de Comercio)",
            "data_subjects": "Clientes, proveedores",
            "data_categories": "Datos identificativos, NIF, importes, conceptos facturados",
            "recipients": "AEAT, asesores fiscales",
            "international_transfers": "No se realizan",
            "retention_period": "6 años (Art. 30 Código de Comercio)",
            "security_measures": "Registro de auditoría, backups cifrados, acceso por roles",
        },
        {
            "name": "Comunicaciones por correo electrónico",
            "purpose": "Gestión de comunicaciones comerciales y operativas con clientes",
            "legal_basis": "Art. 6.1.b RGPD — Ejecución de contrato; Art. 6.1.f — Interés legítimo",
            "data_subjects": "Clientes, contactos comerciales",
            "data_categories": "Nombre, email, contenido de comunicaciones",
            "recipients": "Proveedor de correo electrónico",
            "international_transfers": "Posibles transferencias a EEUU (Google/Microsoft) con cláusulas contractuales tipo",
            "retention_period": "Duración de la relación + 1 año",
            "security_measures": "Cifrado TLS, autenticación OAuth 2.0, acceso restringido",
        },
    ]

    data = {
        "company": {"name": company_name, "nif": company_nif, "address": ""},
        "dpo": None,
        "activities": activities,
    }

    pdf_bytes = generate_rgpd_registry_pdf(data)
    file_name = f"Registro_RGPD_{company_nif}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


# ─── Libro de Registro (AEAT) ─────────────────────────────────────────────────

@router.get("/libro-registro")
async def export_libro_registro(
    year: int = Query(description="Año fiscal (p.ej. 2026)"),
    type: str = Query(default="emitidas", description="Tipo: 'emitidas' o 'recibidas'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Exporta el libro de registro de facturas emitidas o recibidas en formato CSV.
    Obligatorio para la AEAT. Campos: NIF, nombre, nº factura, fecha, base, IVA%, cuota, total.
    """
    import csv
    import io
    from fastapi.responses import StreamingResponse
    from sqlalchemy.orm import joinedload as jl

    invoice_type = "issued" if type == "emitidas" else "received"
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client), jl(Invoice.lines))
        .where(
            and_(
                Invoice.tenant_id == current_user.tenant_id,
                Invoice.invoice_type == invoice_type,
                Invoice.status.notin_(["cancelled"]),
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
        .order_by(Invoice.date)
    )
    invoices = q.unique().scalars().all()

    # Obtener datos del tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Cabecera AEAT-compatible
    writer.writerow([
        "Nº Factura", "Fecha Expedición", "Fecha Operación",
        "NIF Destinatario/Emisor", "Nombre Destinatario/Emisor",
        "Base Imponible", "Tipo IVA %", "Cuota IVA",
        "Base Imponible Total", "Cuota IVA Total", "Total Factura",
    ])

    for inv in invoices:
        counterpart_nif = inv.client.nif if inv.client else ""
        counterpart_name = inv.client.name if inv.client else ""
        inv_date = inv.date.strftime("%d/%m/%Y") if inv.date else ""
        inv_number = inv.invoice_number or str(inv.id)[:8].upper()

        if inv.lines:
            # Una fila por línea con el tipo de IVA de esa línea
            for line in inv.lines:
                qty = float(line.quantity or 1)
                uprice = float(line.unit_price or 0)
                discount = float(line.discount_percentage or 0)
                base_line = qty * uprice
                if discount:
                    base_line -= base_line * discount / 100
                rate = float(line.tax_percentage or 21)
                quota_line = base_line * rate / 100
                writer.writerow([
                    inv_number, inv_date, inv_date,
                    counterpart_nif, counterpart_name,
                    f"{base_line:.2f}", f"{rate:.2f}", f"{quota_line:.2f}",
                    f"{float(inv.amount_base or 0):.2f}",
                    f"{float(inv.tax_amount or 0):.2f}",
                    f"{float(inv.amount_total or 0):.2f}",
                ])
        else:
            # Sin líneas: usar los totales de cabecera
            writer.writerow([
                inv_number, inv_date, inv_date,
                counterpart_nif, counterpart_name,
                f"{float(inv.amount_base or 0):.2f}", "21.00",
                f"{float(inv.tax_amount or 0):.2f}",
                f"{float(inv.amount_base or 0):.2f}",
                f"{float(inv.tax_amount or 0):.2f}",
                f"{float(inv.amount_total or 0):.2f}",
            ])

    output.seek(0)
    company_nif = tenant_obj.nif if tenant_obj else "empresa"
    file_name = f"LibroRegistro_{type}_{year}_{company_nif}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
