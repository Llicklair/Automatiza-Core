"""Fiscal aggregation logic: IVA, IRPF, IS, libro registro, modelo 303.

Extracted from api/v1/routes/reports/_helpers.py and fiscal.py route.
"""

import csv
import io
import logging
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload as jl

from app.db.models.models import Invoice, Payroll, Tenant
from app.services.reports._schemas import (
    FiscalIRPF,
    FiscalIS,
    FiscalIVA,
    FiscalSnapshot,
)

_logger = logging.getLogger(__name__)


def _d(x) -> Decimal:
    """Convierte a Decimal vía str (evita arrastrar el error binario del float)."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x if x is not None else 0))


def _round2(d: Decimal) -> Decimal:
    return Decimal(d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def vat_breakdown_by_rate(invoices) -> dict[Decimal, dict]:
    """Desglose de IVA por tipo impositivo calculado con Decimal.

    Centraliza la aritmética del IVA de los modelos fiscales (303 trimestral,
    390 anual y snapshot) para que coincidan entre sí y no arrastren el error
    de redondeo del `float` —el mismo criterio que `compute_invoice_totals` en
    facturación—. Acumula base y cuota EXACTAS por tipo (sin redondear); el
    redondeo a 2 decimales lo aplica el caller al presentar cada tipo.

    Devuelve ``{rate(Decimal): {"base": Decimal, "quota": Decimal}}``.
    """
    acc: dict[Decimal, dict] = {}
    for inv in invoices:
        for line in inv.lines or []:
            rate = _d(line.tax_percentage if line.tax_percentage is not None else 21)
            base = _d(line.quantity if line.quantity is not None else 1) * _d(line.unit_price)
            if line.discount_percentage:
                base -= base * _d(line.discount_percentage) / Decimal("100")
            quota = base * rate / Decimal("100")
            slot = acc.setdefault(rate, {"base": Decimal("0"), "quota": Decimal("0")})
            slot["base"] += base
            slot["quota"] += quota
    return acc


async def aggregate_fiscal(
    db: AsyncSession, tenant_id: uuid.UUID, start: date, end: date, period: str, label: str
) -> FiscalSnapshot:
    """Agrega datos fiscales: IVA por tipo, IRPF retenciones, IS estimado."""
    from app.services.reports.summaries import generate_resumen_fiscal

    # ── IVA: Repercutido (ventas/emitidas) ──
    # Eager-load Invoice.lines en el outer query — antes había un N+1 que
    # hacía una SELECT por factura para cargar lines (lessons 2026-05-19).
    issued_q = await db.execute(
        select(Invoice).options(jl(Invoice.lines)).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    issued_invoices = issued_q.unique().scalars().all()

    # IVA repercutido (ventas) por tipo, con Decimal (sin arrastre de float).
    rep = vat_breakdown_by_rate(issued_invoices)

    # ── IVA: Soportado (compras/recibidas) ──
    received_q = await db.execute(
        select(Invoice).options(jl(Invoice.lines)).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    received_invoices = received_q.unique().scalars().all()

    # IVA soportado (compras) por tipo, con Decimal.
    sop = vat_breakdown_by_rate(received_invoices)

    def _quota(m: dict, r: int) -> float:
        return float(_round2(m.get(_d(r), {}).get("quota", Decimal("0"))))

    def _sum_quota(m: dict) -> Decimal:
        return _round2(sum((v["quota"] for v in m.values()), Decimal("0")))

    def _sum_base(m: dict) -> float:
        return float(_round2(sum((v["base"] for v in m.values()), Decimal("0"))))

    total_rep = _sum_quota(rep)
    total_sop = _sum_quota(sop)

    iva_section = FiscalIVA(
        repercutido_21=_quota(rep, 21),
        repercutido_10=_quota(rep, 10),
        repercutido_4=_quota(rep, 4),
        total_repercutido=float(total_rep),
        base_repercutido=_sum_base(rep),
        soportado_21=_quota(sop, 21),
        soportado_10=_quota(sop, 10),
        soportado_4=_quota(sop, 4),
        total_soportado=float(total_sop),
        base_soportado=_sum_base(sop),
        resultado_iva=float(_round2(total_rep - total_sop)),
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

    # IVA devengado (ventas) — eager-load lines (antes N+1)
    issued_q = await db.execute(
        select(Invoice).options(jl(Invoice.lines)).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "issued",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    issued_invoices = issued_q.unique().scalars().all()

    # IVA devengado (ventas) por tipo, con Decimal (sin arrastre de float).
    vat_collected = vat_breakdown_by_rate(issued_invoices)

    # IVA deducible (compras) — eager-load lines (antes N+1)
    received_q = await db.execute(
        select(Invoice).options(jl(Invoice.lines)).where(
            and_(
                Invoice.tenant_id == tenant_id,
                Invoice.invoice_type == "received",
                func.date(Invoice.date) >= start,
                func.date(Invoice.date) <= end,
            )
        )
    )
    received_invoices = received_q.unique().scalars().all()

    # IVA deducible (compras) por tipo, con Decimal.
    vat_deducted = vat_breakdown_by_rate(received_invoices)

    def _rows(m: dict) -> list[dict]:
        return sorted(
            (
                {
                    "rate": float(rate),
                    "base": float(_round2(v["base"])),
                    "quota": float(_round2(v["quota"])),
                }
                for rate, v in m.items()
            ),
            key=lambda x: x["rate"],
            reverse=True,
        )

    return {
        "tenant": {"name": tenant_name, "nif": tenant_nif},
        "quarter": quarter,
        "year": year,
        "vat_collected": _rows(vat_collected),
        "vat_deducted": _rows(vat_deducted),
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
