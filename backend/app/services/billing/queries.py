"""Billing queries — read-only operations (CQRS-lite).

No side effects: no INSERT/UPDATE/DELETE, no file writes, no commits.
"""

import logging
import os
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.billing import VerifactuRecord
from app.db.models.models import (
    FixedAsset,
    Invoice,
    JournalEntry,
    RecurringInvoice,
    Tenant,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
VALID_IVA = {0.0, 4.0, 10.0, 21.0}


def _d(x) -> Decimal:
    """Convierte a Decimal vía str para no arrastrar el error binario del float."""
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x if x is not None else 0))


def _round2(d: Decimal) -> Decimal:
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def compute_invoice_totals(lines_data: list[dict], *, allow_negative: bool = False) -> dict:
    """Valida el IVA de cada línea y calcula los importes con Decimal.

    Pura y sin efectos. Centraliza la aritmética monetaria de la factura para
    (a) evitar el arrastre de redondeo del `float` y (b) permitir validar las
    líneas ANTES de consumir un número correlativo (sin huecos ni huérfanas).

    Devuelve `{"lines", "amount_base", "tax_amount", "amount_total"}` con los
    totales redondeados a 2 decimales y, por línea, `_line_base`/`_line_total`.
    Lanza ValueError si algún IVA no es válido o si el total resulta negativo.

    `allow_negative=True` permite totales negativos: lo necesitan las facturas
    rectificativas / de abono (RD 1619/2012 Art. 15), que minoran una factura
    anterior con importes negativos. Para una factura ordinaria se deja en
    False, de modo que un total negativo siga siendo un error de captura.
    """
    total_base = Decimal("0")
    total_tax = Decimal("0")
    out_lines: list[dict] = []
    for ld in lines_data:
        qty = _d(ld.get("quantity", 1))
        uprice = _d(ld.get("unit_price", 0))
        discount = _d(ld.get("discount_percentage", 0))
        tax_perc = float(ld.get("tax_percentage", 21))
        if tax_perc not in VALID_IVA:
            raise ValueError(f"Tipo de IVA inválido: {tax_perc}%. Los valores permitidos son: 0%, 4%, 10%, 21%.")
        if not (Decimal("0") <= discount <= Decimal("100")):
            raise ValueError(f"Descuento por línea fuera de rango: {discount}%. Debe estar entre 0 y 100.")
        line_base = qty * uprice
        if discount > 0:
            line_base -= line_base * (discount / Decimal("100"))
        # Una línea con base negativa (cantidad/precio negativos) solo es válida en
        # una rectificativa/abono. En una factura ordinaria la validación del TOTAL
        # no la detectaba si otra línea la compensaba → base de línea negativa
        # camuflada en un F1 fiscalmente inválido (audit ERP 2026-07-03).
        if line_base < 0 and not allow_negative:
            raise ValueError(
                "Una línea no puede tener base negativa en una factura ordinaria. "
                "Usa una factura rectificativa para abonos."
            )
        line_tax = line_base * (_d(tax_perc) / Decimal("100"))
        total_base += line_base
        total_tax += line_tax
        out_lines.append(
            {
                **ld,
                "quantity": float(qty),
                "unit_price": float(uprice),
                "discount_percentage": float(discount),
                "tax_percentage": tax_perc,
                "_line_base": float(_round2(line_base)),
                "_line_total": float(_round2(line_base + line_tax)),
            }
        )
    amount_total = _round2(total_base + total_tax)
    if amount_total < 0 and not allow_negative:
        raise ValueError("El importe total de la factura no puede ser negativo.")
    return {
        "lines": out_lines,
        "amount_base": float(_round2(total_base)),
        "tax_amount": float(_round2(total_tax)),
        "amount_total": float(amount_total),
    }


# ── Invoice helpers ──────────────────────────────────────────────────────────


async def _load_invoice(invoice_id: UUID, tenant_id, db: AsyncSession, with_joins: bool = True):
    query = select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    if with_joins:
        query = query.options(joinedload(Invoice.client), joinedload(Invoice.lines))
    result = await db.execute(query)
    return result.unique().scalar_one_or_none() if with_joins else result.scalar_one_or_none()


async def _load_tenant(tenant_id, db: AsyncSession) -> tuple[str, str]:
    tenant_obj = await db.get(Tenant, tenant_id)
    company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
    company_nif = tenant_obj.nif if tenant_obj else "B00000000"
    return company_name, company_nif


async def _load_verifactu(invoice_id: UUID, db: AsyncSession) -> dict | None:
    """Carga el registro Verifactu de una factura y devuelve `{huella, verify_url}`
    para renderizar el QR tributario (FAC.QR). Devuelve None si la factura aún no
    tiene registro encadenado (el PDF/ticket sale sin QR — válido).

    `verify_url` es la URL del servicio de COTEJO de la AEAT (`ValidarQR`) con los 4
    parámetros obligatorios (nif, numserie, fecha, importe): es lo que el receptor
    escanea para verificar la factura en la sede de la AEAT.
    """
    result = await db.execute(select(VerifactuRecord).where(VerifactuRecord.invoice_id == invoice_id))
    record = result.scalar_one_or_none()
    if record is None:
        return None

    from app.services.billing.verifactu_chain import _fmt_fecha_expedicion, _fmt_importe
    from app.services.billing.verifactu_qr import build_aeat_cotejo_url

    return {
        "huella": record.huella,
        "verify_url": build_aeat_cotejo_url(
            nif=record.nif_emisor,
            num_serie=record.numero_factura,
            fecha=_fmt_fecha_expedicion(record.fecha_emision),
            importe=_fmt_importe(record.importe_total),
        ),
    }


async def load_verifactu_qr(invoice_id: UUID, db: AsyncSession) -> dict | None:
    """QR Verifactu público de una factura: `{huella, verify_url}` o None si aún no
    tiene registro encadenado. Mismo builder que el PDF (FAC.QR), reutilizable
    desde rutas (p.ej. el ticket del TPV)."""
    return await _load_verifactu(invoice_id, db)


def _build_invoice_data(
    invoice,
    company_name: str,
    company_nif: str,
    verifactu: dict | None = None,
) -> dict:
    return {
        "number": invoice.invoice_number or f"F-{str(invoice.id)[:8].upper()}",
        "date": invoice.date.isoformat() if invoice.date else "",
        "amount_base": float(invoice.amount_base or 0),
        "tax_amount": float(invoice.tax_amount or 0),
        "amount_total": float(invoice.amount_total or 0),
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
        "company": {
            "name": company_name,
            "nif": company_nif,
            "address": "Calle Principal, 1 · Madrid",
            "phone": "",
        },
        "lines": [
            {
                "description": line.description or "",
                "quantity": float(line.quantity or 1),
                "unit_price": float(line.unit_price or 0),
                "tax_percentage": float(line.tax_percentage or 21),
                "total": float(line.total or 0),
            }
            for line in (invoice.lines or [])
        ],
        "notes": invoice.notes or "",
        "payment_terms": invoice.terms or "",
        "verifactu": verifactu,
    }


# ── Invoice queries ──────────────────────────────────────────────────────────


async def list_invoices(
    tenant_id,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
):
    query = (
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.tenant_id == tenant_id)
        .order_by(desc(Invoice.created_at))
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.unique().scalars().all()


async def get_invoice(invoice_id: UUID, tenant_id, db: AsyncSession):
    return await _load_invoice(invoice_id, tenant_id, db)


async def build_invoice_pdf(invoice_id: UUID, tenant_id, db: AsyncSession) -> tuple[bytes, str]:
    """Genera PDF al vuelo. Lanza ValueError si no existe.

    Incluye QR Verifactu si la factura tiene VerifactuRecord encadenado
    (RD 1007/2023 Art. 8 — FAC.QR).
    """
    from app.services.pdf import generate_invoice_pdf
    from app.services.template_service import get_default_theme

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    company_name, company_nif = await _load_tenant(tenant_id, db)
    theme_config = await get_default_theme(tenant_id, "invoice", db)
    verifactu = await _load_verifactu(invoice_id, db)
    invoice_data = _build_invoice_data(invoice, company_name, company_nif, verifactu)
    pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
    file_name = f"Factura_{invoice_data['number']}.pdf"
    return pdf_bytes, file_name


async def build_rectificative_pdf(
    invoice_id: UUID,
    tenant_id,
    reason: str,
    db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera PDF rectificativa al vuelo. Lanza ValueError si no existe."""
    from app.services.pdf import generate_rectificative_invoice_pdf
    from app.services.template_service import get_default_theme

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    company_name, company_nif = await _load_tenant(tenant_id, db)
    theme_config = await get_default_theme(tenant_id, "invoice", db)

    orig_base = float(invoice.amount_base or 0)
    orig_tax = float(invoice.tax_amount or 0)
    orig_total = float(invoice.amount_total or 0)

    corrected_lines = [
        {
            "description": line.description or "",
            "original_amount": float(line.total or 0),
            "corrected_amount": 0.0,
        }
        for line in (invoice.lines or [])
    ]

    data = {
        "number": f"FR-{(invoice.invoice_number or str(invoice.id)[:8]).upper()}",
        "date": datetime.now(UTC).isoformat(),
        "original_invoice": {
            "number": invoice.invoice_number or str(invoice.id)[:8],
            "date": invoice.date.isoformat() if invoice.date else "",
            "amount_base": orig_base,
            "tax_amount": orig_tax,
            "amount_total": orig_total,
        },
        "reason": reason,
        "corrected_lines": corrected_lines,
        "corrected_base": 0.0,
        "corrected_tax": 0.0,
        "corrected_total": 0.0,
        "company": {"name": company_name, "nif": company_nif, "address": "", "phone": ""},
        "client": {
            "name": invoice.client.name if invoice.client else "Cliente",
            "nif": invoice.client.nif if invoice.client else "",
            "email": invoice.client.email if invoice.client else "",
            "address": invoice.client.address if invoice.client else "",
        },
    }

    pdf_bytes = generate_rectificative_invoice_pdf(data, theme_config)
    file_name = f"Rectificativa_{data['number']}.pdf"
    return pdf_bytes, file_name


async def build_retention_pdf(
    invoice_id: UUID,
    tenant_id,
    retention_pct: float,
    db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera PDF con retención IRPF al vuelo. Lanza ValueError si no existe."""
    from app.services.pdf import generate_retention_invoice_pdf
    from app.services.template_service import get_default_theme

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    company_name, company_nif = await _load_tenant(tenant_id, db)
    theme_config = await get_default_theme(tenant_id, "invoice", db)
    verifactu = await _load_verifactu(invoice_id, db)

    base = float(invoice.amount_base or 0)
    retention_amount = round(base * retention_pct / 100, 2)

    data = _build_invoice_data(invoice, company_name, company_nif, verifactu)
    data["retention_percentage"] = retention_pct
    data["retention_amount"] = retention_amount

    pdf_bytes = generate_retention_invoice_pdf(data, theme_config)
    file_name = f"Factura_Retencion_{data['number']}.pdf"
    return pdf_bytes, file_name


# ── Accounting queries ───────────────────────────────────────────────────────


async def list_journal_entries(db: AsyncSession, tenant_id: UUID) -> list[JournalEntry]:
    query = (
        select(JournalEntry)
        .where(JournalEntry.tenant_id == tenant_id)
        .options(selectinload(JournalEntry.lines))
        .order_by(desc(JournalEntry.date))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_fixed_assets(db: AsyncSession, tenant_id: UUID) -> list[FixedAsset]:
    result = await db.execute(
        select(FixedAsset).where(FixedAsset.tenant_id == tenant_id).order_by(desc(FixedAsset.created_at))
    )
    return list(result.scalars().all())


# ── Recurring queries ────────────────────────────────────────────────────────


async def list_recurring(tenant_id: UUID, db: AsyncSession) -> list:
    result = await db.execute(
        select(RecurringInvoice)
        .where(RecurringInvoice.tenant_id == tenant_id)
        .options(joinedload(RecurringInvoice.client))
        .order_by(desc(RecurringInvoice.created_at))
    )
    return list(result.unique().scalars().all())
