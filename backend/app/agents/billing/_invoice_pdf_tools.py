"""
PDF generation and template helpers for invoices.
"""

import logging
import os
from uuid import UUID

from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.billing import DocumentTemplate
from app.db.models.models import TenantDocument

logger = logging.getLogger(__name__)


async def _load_invoice_template(tenant_id: str) -> tuple[dict | None, str | None]:
    """Carga la plantilla visual activa del tenant. Devuelve (theme_config, template_name)."""
    from sqlalchemy import select

    try:
        async with AsyncSessionLocal() as db:
            r = await db.execute(
                select(DocumentTemplate)
                .where(
                    DocumentTemplate.tenant_id == UUID(tenant_id),
                    DocumentTemplate.template_type == "invoice",
                )
                .order_by(DocumentTemplate.is_default.desc(), DocumentTemplate.created_at)
            )
            tpl = r.scalars().first()
        if not tpl:
            return None, None
        return {
            "accent_color": tpl.accent_color,
            "font_family": tpl.font_family,
            "layout_style": tpl.layout_style,
            "logo_position": tpl.logo_position,
            "header_style": tpl.header_style,
            "table_style": tpl.table_style,
            "footer_text": tpl.footer_text,
        }, tpl.name
    except Exception as e:
        logger.error("No se pudo cargar plantilla de factura: %s", e)
        return None, None


async def _generate_and_save_invoice_pdf(
    tenant_id: str,
    invoice,
    invoice_line,
    client,
    issuer_name: str,
    issuer_nif: str,
    issuer_address: str,
    issuer_email: str,
    theme_config: dict | None,
) -> tuple[str | None, str | None]:
    """Genera el PDF de factura, lo guarda en disco y en BD. Devuelve (document_id, warning)."""
    from app.services.pdf import generate_invoice_pdf

    try:
        pdf_data = {
            "number": invoice.invoice_number,
            "date": invoice.date.isoformat(),
            "amount_base": float(invoice.amount_base),
            "tax_amount": float(invoice.tax_amount),
            "amount_total": float(invoice.amount_total),
            "notes": invoice.notes,
            "client": {"name": client.name, "nif": client.nif},
            "lines": [
                {
                    "description": invoice_line.description,
                    "quantity": invoice_line.quantity,
                    "unit_price": invoice_line.unit_price,
                    "tax_percentage": invoice_line.tax_percentage,
                    "total": invoice_line.total,
                }
            ],
            "company": {
                "name": issuer_name or getattr(settings, "APP_NAME", "Empresa"),
                "nif": issuer_nif or "B-00000000",
                "address": issuer_address or "",
                "email": issuer_email or "",
            },
        }
        pdf_bytes = generate_invoice_pdf(pdf_data, theme_config)

        upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
        if not os.path.exists(upload_dir) and os.name == "nt":
            upload_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "uploads")
            )
        os.makedirs(upload_dir, exist_ok=True)

        file_name = f"Factura_{invoice.invoice_number}.pdf"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        doc = TenantDocument(
            tenant_id=UUID(tenant_id),
            file_name=file_name,
            file_path=file_path,
            file_type="application/pdf",
            file_size=len(pdf_bytes),
            category="Facturas",
            status="completed",
        )
        async with AsyncSessionLocal() as db_doc:
            db_doc.add(doc)
            await db_doc.commit()
            await db_doc.refresh(doc)
        return str(doc.id), None
    except Exception as e:
        return None, f"Factura creada pero error al generar PDF: {e}"
