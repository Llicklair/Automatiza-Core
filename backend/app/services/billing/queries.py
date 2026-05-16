"""Billing queries — read-only operations (CQRS-lite).

No side effects: no INSERT/UPDATE/DELETE, no file writes, no commits.
"""

import logging
import os
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.db.models.models import (
    FixedAsset,
    Invoice,
    JournalEntry,
    RecurringInvoice,
    Tenant,
)

logger = logging.getLogger(__name__)

UPLOAD_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
)
VALID_IVA = {0.0, 4.0, 10.0, 21.0}


# ── Invoice helpers ──────────────────────────────────────────────────────────


async def _load_invoice(
    invoice_id: UUID, tenant_id, db: AsyncSession, with_joins: bool = True
):
    query = select(Invoice).where(
        Invoice.id == invoice_id, Invoice.tenant_id == tenant_id
    )
    if with_joins:
        query = query.options(joinedload(Invoice.client), joinedload(Invoice.lines))
    result = await db.execute(query)
    return (
        result.unique().scalar_one_or_none()
        if with_joins
        else result.scalar_one_or_none()
    )


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


async def build_invoice_pdf(
    invoice_id: UUID, tenant_id, db: AsyncSession
) -> tuple[bytes, str]:
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

    base = float(invoice.amount_base or 0)
    retention_amount = round(base * retention_pct / 100, 2)

    data = _build_invoice_data(invoice, company_name, company_nif)
    data["retention_percentage"] = retention_pct
    data["retention_amount"] = retention_amount

    pdf_bytes = generate_retention_invoice_pdf(data, theme_config)
    file_name = f"Factura_Retencion_{data['number']}.pdf"
    return pdf_bytes, file_name


# ── Accounting queries ───────────────────────────────────────────────────────


async def list_journal_entries(
    db: AsyncSession, tenant_id: UUID
) -> list[JournalEntry]:
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
        select(FixedAsset)
        .where(FixedAsset.tenant_id == tenant_id)
        .order_by(desc(FixedAsset.created_at))
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
