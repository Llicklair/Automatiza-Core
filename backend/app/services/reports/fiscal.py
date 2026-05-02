"""Fiscal aggregation logic: IVA, IRPF, IS, libro registro, modelo 303.

Extracted from api/v1/routes/reports/_helpers.py and fiscal.py route.
"""

import csv
import io
import logging
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.services.reports._schemas import (
    FiscalIRPF,
    FiscalIS,
    FiscalIVA,
    FiscalSnapshot,
)
from app.db.models.models import Invoice, Payroll, Tenant

_logger = logging.getLogger(__name__)


async def aggregate_fiscal(
    db: AsyncSession, tenant_id: uuid.UUID, start: date, end: date, period: str, label: str
) -> FiscalSnapshot:
    """Agrega datos fiscales: IVA por tipo, IRPF retenciones, IS estimado."""
    from app.services.reports.summaries import generate_resumen_fiscal

    # ── IVA: Repercutido (ventas/emitidas) ──
    issued_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    issued_invoices = issued_q.scalars().all()

    vat_rep: dict[float, float] = {}
    base_rep: dict[float, float] = {}
    for inv in issued_invoices:
        lines_q = await db.execute(
            select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
        )
        inv_wl = lines_q.unique().scalar_one()
        for line in inv_wl.lines or []:
            rate = float(line.tax_percentage or 21)
            base = float(line.quantity or 1) * float(line.unit_price or 0)
            if line.discount_percentage:
                base -= base * float(line.discount_percentage) / 100
            vat_rep[rate] = vat_rep.get(rate, 0) + base * rate / 100
            base_rep[rate] = base_rep.get(rate, 0) + base

    # ── IVA: Soportado (compras/recibidas) ──
    received_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    received_invoices = received_q.scalars().all()

    vat_sop: dict[float, float] = {}
    base_sop: dict[float, float] = {}
    for inv in received_invoices:
        lines_q = await db.execute(
            select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
        )
        inv_wl = lines_q.unique().scalar_one()
        for line in inv_wl.lines or []:
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

    # ── IRPF: Retenciones en nominas ──
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
    irpf_nominas = round(sum(float(p.irpf or 0) for p in payrolls), 2)

    irpf_section = FiscalIRPF(
        retenciones_nominas=irpf_nominas,
        retenciones_facturas=0.0,
        total_retenciones=irpf_nominas,
    )

    # ── IS: Estimacion Impuesto de Sociedades ──
    ingresos_brutos = round(
        sum(float(i.amount_base or i.amount_total or 0) for i in issued_invoices), 2
    )
    gastos_deducibles = round(
        sum(float(i.amount_base or i.amount_total or 0) for i in received_invoices), 2
    )
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
    resumen = await generate_resumen_fiscal(period, label, iva_section, irpf_section, is_section)

    return FiscalSnapshot(
        period=period,
        period_label=label,
        generated_at=datetime.now(UTC),
        iva=iva_section,
        irpf=irpf_section,
        impuesto_sociedades=is_section,
        resumen_ejecutivo=resumen,
    )


async def build_modelo_303_data(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    quarter: int,
    year: int,
) -> dict:
    """Agrega datos para el Modelo 303 (liquidacion trimestral IVA).

    Returns dict ready for PDF generation.
    """
    quarter_months = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
    m_start, m_end = quarter_months[quarter]
    start = date(year, m_start, 1)
    last_day = monthrange(year, m_end)[1]
    end = date(year, m_end, last_day)

    # Tenant
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()
    tenant_name = tenant_obj.name if tenant_obj else "Mi Empresa"
    tenant_nif = tenant_obj.nif if tenant_obj else "B00000000"

    # IVA devengado (ventas)
    issued_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    issued_invoices = issued_q.scalars().all()

    vat_collected_map: dict[float, dict] = {}
    for inv in issued_invoices:
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

    # IVA deducible (compras)
    received_q = await db.execute(
        select(Invoice).where(
            and_(
                Invoice.tenant_id == tenant_id,
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

    return {
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "quarter": quarter,
        "year": year,
        "vat_collected": sorted(vat_collected_map.values(), key=lambda x: x["rate"], reverse=True),
        "vat_deducted": sorted(vat_deducted_map.values(), key=lambda x: x["rate"], reverse=True),
    }


async def build_libro_registro_csv(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    year: int,
    invoice_type_label: str,
) -> tuple[str, str]:
    """Genera CSV del libro de registro de facturas (emitidas/recibidas).

    Returns (csv_content, file_name).
    """
    invoice_type = "issued" if invoice_type_label == "emitidas" else "received"
    start = date(year, 1, 1)
    end = date(year, 12, 31)

    q = await db.execute(
        select(Invoice)
        .options(jl(Invoice.client), jl(Invoice.lines))
        .where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == invoice_type,
                Invoice.status.notin_(["cancelled"]),
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
        .order_by(Invoice.date)
    )
    invoices = q.unique().scalars().all()

    # Tenant data
    tenant_q = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant_obj = tenant_q.scalar_one_or_none()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    writer.writerow(
        [
            "Nº Factura",
            "Fecha Expedicion",
            "Fecha Operacion",
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
    file_name = f"LibroRegistro_{invoice_type_label}_{year}_{company_nif}.csv"

    return output.getvalue(), file_name
