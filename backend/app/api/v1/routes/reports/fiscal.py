"""Fiscal snapshot GET + POST generate + modelo 303 + libro registro endpoints."""

import csv
import io
import os
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Invoice, Tenant, TenantDocument, User
from app.services.pdf import generate_modelo_303_pdf

from ._helpers import UPLOAD_DIR, _aggregate_fiscal, _parse_period
from ._schemas import FiscalSnapshot, ReportOut

router = APIRouter()


@router.get("/fiscal-snapshot", response_model=FiscalSnapshot)
async def get_fiscal_snapshot(
    period: str = Query(
        default=None, description="Periodo: YYYY-MM (mensual) o YYYY-Q1..Q4 (trimestral)"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el snapshot fiscal para el periodo indicado."""
    if not period:
        today = date.today()
        period = today.strftime("%Y-%m")

    start, end, label = _parse_period(period)
    return await _aggregate_fiscal(db, current_user.tenant_id, start, end, period, label)


@router.post("/fiscal-snapshot/generate", response_model=ReportOut, status_code=201)
async def generate_fiscal_snapshot_pdf(
    period: str = Query(default=None, description="Periodo: YYYY-MM o YYYY-Q1..Q4"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera el informe fiscal PDF y lo guarda en documentos del tenant."""
    if not period:
        today = date.today()
        period = today.strftime("%Y-%m")

    start, end, label = _parse_period(period)

    tenant_q = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = tenant_q.scalar_one_or_none()
    company_name = tenant.name if tenant and tenant.name else "Tu empresa"

    snap = await _aggregate_fiscal(db, current_user.tenant_id, start, end, period, label)

    from app.services.pdf_reports import generate_fiscal_report_pdf

    pdf_bytes = generate_fiscal_report_pdf(
        snap=snap.model_dump(),
        company_name=company_name,
        period=period,
    )

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_period = period.replace("-", "_")
    file_name = f"fiscal_{safe_period}_{uuid.uuid4().hex[:8]}.pdf"
    file_path = os.path.join(UPLOAD_DIR, file_name)
    with open(file_path, "wb") as fh:
        fh.write(pdf_bytes)

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


@router.get("/modelo-303")
async def generate_modelo_303(
    quarter: int = Query(ge=1, le=4, description="Trimestre (1-4)"),
    year: int = Query(default=2026, description="Año fiscal"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera borrador PDF del Modelo 303 (liquidación trimestral de IVA)."""
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
    vat_collected_map: dict[float, dict] = {}
    for inv in issued_invoices:
        # Reload lines
        lines_q = await db.execute(
            select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
        )
        inv_with_lines = lines_q.unique().scalar_one()
        for line in inv_with_lines.lines or []:
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
        for line in inv_with_lines.lines or []:
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
    writer.writerow(
        [
            "Nº Factura",
            "Fecha Expedición",
            "Fecha Operación",
            "NIF Destinatario/Emisor",
            "Nombre Destinatario/Emisor",
            "Base Imponible",
            "Tipo IVA %",
            "Cuota IVA",
            "Base Imponible Total",
            "Cuota IVA Total",
            "Total Factura",
        ]
    )

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
                writer.writerow(
                    [
                        inv_number,
                        inv_date,
                        inv_date,
                        counterpart_nif,
                        counterpart_name,
                        f"{base_line:.2f}",
                        f"{rate:.2f}",
                        f"{quota_line:.2f}",
                        f"{float(inv.amount_base or 0):.2f}",
                        f"{float(inv.tax_amount or 0):.2f}",
                        f"{float(inv.amount_total or 0):.2f}",
                    ]
                )
        else:
            # Sin líneas: usar los totales de cabecera
            writer.writerow(
                [
                    inv_number,
                    inv_date,
                    inv_date,
                    counterpart_nif,
                    counterpart_name,
                    f"{float(inv.amount_base or 0):.2f}",
                    "21.00",
                    f"{float(inv.tax_amount or 0):.2f}",
                    f"{float(inv.amount_base or 0):.2f}",
                    f"{float(inv.tax_amount or 0):.2f}",
                    f"{float(inv.amount_total or 0):.2f}",
                ]
            )

    output.seek(0)
    company_nif = tenant_obj.nif if tenant_obj else "empresa"
    file_name = f"LibroRegistro_{type}_{year}_{company_nif}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
