"""Servicio de dominio para facturas.

Encapsula: CRUD, cálculo de líneas, generación de PDF, series correlativas.
"""

import logging
import os
import uuid as uuid_mod
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.models import (
    Invoice,
    InvoiceLine,
    InvoiceSeries,
    Tenant,
    TenantDocument,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
)

VALID_IVA = {0.0, 4.0, 10.0, 21.0}


# ── Helpers ─────────────────────────────────────────────────────────────────


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


def _build_invoice_data(invoice, company_name: str, company_nif: str) -> dict:
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
    }


# ── CRUD ────────────────────────────────────────────────────────────────────


async def list_invoices(
    tenant_id, db: AsyncSession, skip: int = 0, limit: int = 50,
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


async def update_status(
    invoice_id: UUID, tenant_id, new_status: str, db: AsyncSession,
):
    """Cambia estado. Lanza ValueError si no existe o estado inválido."""
    allowed = {"draft", "pending", "paid", "cancelled"}
    if new_status not in allowed:
        raise ValueError(f"Estado no válido. Opciones: {allowed}")

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    invoice.status = new_status
    await db.commit()
    await db.refresh(invoice)
    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == invoice_id)
    )
    return result.unique().scalar_one()


async def delete_invoice(invoice_id: UUID, tenant_id, db: AsyncSession) -> bool:
    invoice = await _load_invoice(invoice_id, tenant_id, db, with_joins=False)
    if not invoice:
        return False
    await db.delete(invoice)
    await db.commit()
    return True


async def create_invoice(
    client_id: UUID, payload_dict: dict, lines_data: list[dict],
    tenant_id, user_id, db: AsyncSession,
):
    """Crea factura con líneas. Lanza ValueError si IVA inválido o total negativo.
    Retorna la factura con joins para la response."""

    # Ignorar campos totalizadores del frontend
    for k in ("amount_base", "tax_amount", "amount_total"):
        payload_dict.pop(k, None)

    manual_number = payload_dict.pop("invoice_number", None)
    serie = (payload_dict.pop("serie", "F") or "F").upper()[:10]

    if manual_number:
        invoice_number = manual_number
    else:
        invoice_year = datetime.now(timezone.utc).year
        series_result = await db.execute(
            select(InvoiceSeries)
            .where(
                InvoiceSeries.tenant_id == tenant_id,
                InvoiceSeries.serie == serie,
                InvoiceSeries.year == invoice_year,
            )
            .with_for_update()
        )
        series_row = series_result.scalar_one_or_none()

        if series_row is None:
            series_row = InvoiceSeries(
                tenant_id=tenant_id,
                serie=serie,
                year=invoice_year,
                last_number=0,
                prefix=serie,
            )
            db.add(series_row)
            await db.flush()

        series_row.last_number += 1
        invoice_number = f"{series_row.prefix}{invoice_year}-{series_row.last_number:04d}"

    new_invoice = Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=invoice_number,
        amount_base=0.0,
        tax_amount=0.0,
        amount_total=0.0,
        **payload_dict,
    )
    db.add(new_invoice)
    await db.commit()
    await db.refresh(new_invoice)

    total_base = 0.0
    total_tax = 0.0

    for line_data in lines_data:
        qty = float(line_data.get("quantity", 1))
        uprice = float(line_data.get("unit_price", 0))
        discount_perc = float(line_data.get("discount_percentage", 0))
        tax_perc = float(line_data.get("tax_percentage", 21))

        if tax_perc not in VALID_IVA:
            raise ValueError(
                f"Tipo de IVA inválido: {tax_perc}%. Los valores permitidos son: 0%, 4%, 10%, 21%."
            )

        line_base = qty * uprice
        if discount_perc > 0:
            line_base -= line_base * (discount_perc / 100)
        line_tax = line_base * (tax_perc / 100)
        line_total = line_base + line_tax

        total_base += line_base
        total_tax += line_tax

        db.add(InvoiceLine(
            invoice_id=new_invoice.id,
            product_id=line_data.get("product_id"),
            description=line_data.get("description"),
            quantity=qty,
            unit_price=uprice,
            discount_percentage=discount_perc,
            tax_percentage=tax_perc,
            total=line_total,
        ))

    new_invoice.amount_base = round(total_base, 2)
    new_invoice.tax_amount = round(total_tax, 2)
    new_invoice.amount_total = round(total_base + total_tax, 2)

    if new_invoice.amount_total < 0:
        await db.rollback()
        raise ValueError("El importe total de la factura no puede ser negativo.")
    if lines_data and new_invoice.amount_total == 0:
        logger.warning("Factura creada con importe 0 para cliente %s", client_id)

    await db.commit()

    result = await db.execute(
        select(Invoice)
        .options(joinedload(Invoice.client), joinedload(Invoice.lines))
        .where(Invoice.id == new_invoice.id)
    )
    return result.unique().scalar_one()


# ── PDF generation ──────────────────────────────────────────────────────────


async def generate_and_save_invoice_pdf(invoice, tenant_id, user_id) -> None:
    """Genera el PDF de la factura y lo registra como TenantDocument (background)."""
    from app.db.base import AsyncSessionLocal
    from app.services.pdf import generate_invoice_pdf
    from app.services.template_service import get_default_theme

    try:
        async with AsyncSessionLocal() as session:
            tenant_obj = await session.get(Tenant, tenant_id)
            theme_config = await get_default_theme(tenant_id, "invoice", session)

        company_name = tenant_obj.name if tenant_obj else "Mi Empresa S.L."
        company_nif = tenant_obj.nif if tenant_obj else "B00000000"

        invoice_data = _build_invoice_data(invoice, company_name, company_nif)
        pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
        file_name = f"Factura_{invoice_data['number']}.pdf"

        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_name = f"{uuid_mod.uuid4().hex}.pdf"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as session:
            doc = TenantDocument(
                tenant_id=tenant_id,
                uploaded_by=user_id,
                file_name=file_name,
                file_type="application/pdf",
                file_path=file_path,
                file_size=len(pdf_bytes),
                category="Facturas",
                status="ready",
            )
            session.add(doc)
            await session.commit()
    except Exception as e:
        logger.error("Error generando PDF de factura: %s", e)


async def build_invoice_pdf(invoice_id: UUID, tenant_id, db: AsyncSession) -> tuple[bytes, str]:
    """Genera PDF al vuelo. Lanza ValueError si no existe."""
    from app.services.pdf import generate_invoice_pdf
    from app.services.template_service import get_default_theme

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    company_name, company_nif = await _load_tenant(tenant_id, db)
    theme_config = await get_default_theme(tenant_id, "invoice", db)
    invoice_data = _build_invoice_data(invoice, company_name, company_nif)
    pdf_bytes = generate_invoice_pdf(invoice_data, theme_config)
    file_name = f"Factura_{invoice_data['number']}.pdf"
    return pdf_bytes, file_name


async def build_rectificative_pdf(
    invoice_id: UUID, tenant_id, reason: str, db: AsyncSession,
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
        "date": datetime.now(timezone.utc).isoformat(),
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
    invoice_id: UUID, tenant_id, retention_pct: float, db: AsyncSession,
) -> tuple[bytes, str]:
    """Genera PDF con retención IRPF al vuelo. Lanza ValueError si no existe."""
    from app.services.pdf import generate_retention_invoice_pdf
    from app.services.template_service import get_default_theme

    invoice = await _load_invoice(invoice_id, tenant_id, db)
    if not invoice:
        raise ValueError("Factura no encontrada")

    company_name, company_nif = await _load_tenant(tenant_id, db)
    theme_config = await get_default_theme(tenant_id, "invoice", db)

    base = float(invoice.amount_base or 0)
    retention_amount = round(base * retention_pct / 100, 2)

    data = _build_invoice_data(invoice, company_name, company_nif)
    data["retention_percentage"] = retention_pct
    data["retention_amount"] = retention_amount

    pdf_bytes = generate_retention_invoice_pdf(data, theme_config)
    file_name = f"Factura_Retencion_{data['number']}.pdf"
    return pdf_bytes, file_name
