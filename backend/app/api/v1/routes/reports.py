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
    Employee,
    Invoice,
    Payroll,
    TenantDocument,
    User,
)
from app.services.pdf_service import generate_snapshot_pdf, generate_text_report_pdf

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

    # ── Resumen ejecutivo ──
    tendencia = "positiva" if margen > 0 else "negativa"
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
        resumen += f"Se registraron {bank_section.transacciones} movimientos bancarios."

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
