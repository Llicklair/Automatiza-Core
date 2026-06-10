"""
Invoice query and delivery tools (read operations + email).
Covers: _list_invoices_async, _send_invoice_by_email_async,
        list_invoices, send_invoice_by_email.
"""

import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, TenantDocument

logger = logging.getLogger(__name__)


async def _list_invoices_async(tenant_id: str, limit: int) -> str:
    try:
        async with AsyncSessionLocal() as db:
            stmt = (
                select(Invoice, Client)
                .join(Client)
                .where(Invoice.tenant_id == UUID(tenant_id))
                .order_by(Invoice.date.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                return "No hay facturas registradas en el sistema."

            invoice_numbers = [inv.invoice_number for inv, _ in rows]
            doc_stmt = select(TenantDocument.id, TenantDocument.file_name).where(
                TenantDocument.tenant_id == UUID(tenant_id),
                TenantDocument.file_type == "application/pdf",
            )
            doc_result = await db.execute(doc_stmt)
            doc_map: dict[str, str] = {}
            for doc_id, file_name in doc_result.all():
                for inv_num in invoice_numbers:
                    if inv_num in (file_name or ""):
                        doc_map[inv_num] = str(doc_id)

            total_facturado = 0
            lines = []
            for inv, cli in rows:
                total_facturado += float(inv.amount_total)
                doc_id = doc_map.get(inv.invoice_number, "")
                doc_info = f" | document_id: {doc_id}" if doc_id else ""
                lines.append(
                    f"- {inv.invoice_number} | invoice_id: {inv.id} | {cli.name} | "
                    f"{float(inv.amount_total):.2f}€ | "
                    f"{inv.date.strftime('%Y-%m-%d')} | "
                    f"Estado: {inv.status}{doc_info}"
                )

            return (
                f"Facturas recientes ({len(rows)}):\n"
                + "\n".join(lines)
                + f"\n\nTotal facturado: {total_facturado:.2f}€\n"
                + "(invoice_id es el UUID a pasar a update_invoice_status / update_invoice / "
                + "send_invoice_by_email. document_id es el UUID del PDF — úsalo como attachment_id "
                + "al enviar por email.)"
            )
    except Exception as e:
        return f"Error consultando facturas: {e}"


async def _send_invoice_by_email_async(
    tenant_id: str, invoice_id: str, recipient_email: str
) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Invoice, Client)
                .join(Client)
                .where(
                    Invoice.tenant_id == UUID(tenant_id),
                    Invoice.id == UUID(invoice_id),
                )
            )
            row = result.first()
            if not row:
                return f"Error: Factura {invoice_id} no encontrada."

            invoice, client = row

            email_to = recipient_email.strip() if recipient_email else (client.email or "")
            if not email_to:
                return (
                    f"Error: El cliente '{client.name}' no tiene email registrado. "
                    "Proporciona el email del destinatario."
                )

            doc_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == UUID(tenant_id),
                    TenantDocument.file_name.contains(invoice.invoice_number),
                    TenantDocument.file_type == "application/pdf",
                )
            )
            pdf_doc = doc_result.scalar_one_or_none()
            doc_id = str(pdf_doc.id) if pdf_doc else None

        from app.services.email.sender import send_email

        result_text = await send_email(
            tenant_id=tenant_id,
            to=email_to,
            subject=f"Factura {invoice.invoice_number} - {float(invoice.amount_total):.2f}€",
            body=(
                f"Estimado/a {client.name},\n\n"
                f"Adjunto encontrará la factura {invoice.invoice_number} "
                f"por importe de {float(invoice.amount_total):.2f}€.\n\n"
                f"Concepto: {invoice.notes or 'Servicios profesionales'}\n"
                f"Fecha: {invoice.date.strftime('%d/%m/%Y')}\n\n"
                f"Un cordial saludo."
            ),
            attachment_ids=[doc_id] if doc_id else None,
        )

        return f"Factura {invoice.invoice_number} enviada a {email_to}.\n{result_text}"
    except Exception as e:
        return f"Error enviando factura por email: {e}"


# ─── @tool decorated public functions ─────────────────────────────────────────


@tool
async def list_invoices(tenant_id: str, limit: int = 15) -> str:
    """
    Lista las facturas más recientes del tenant con cliente, importe y estado.
    Útil para consultas como "¿cuánto he facturado?", "ver facturas", "listado".

    Cada línea incluye `invoice_id: <uuid>` (UUID del Invoice — pásalo a
    update_invoice_status / update_invoice / send_invoice_by_email) y
    opcionalmente `document_id: <uuid>` (UUID del PDF — pásalo como
    attachment_id al enviar por email). NO confundir ambos: el invoice_number
    (ej: "IA-XXX" o "F2026-XXXX") es solo un identificador legible y NO sirve
    como input para las tools de update.

    Args:
        tenant_id: ID del tenant
        limit: Número máximo de facturas a devolver (por defecto 15)
    """
    return await _list_invoices_async(tenant_id, limit)


@tool
async def send_invoice_by_email(tenant_id: str, invoice_id: str, recipient_email: str = "") -> str:
    """
    Envía una factura existente por email al cliente.
    Busca el PDF de la factura y lo envía como adjunto.
    Si no se proporciona email, usa el del cliente vinculado.

    Args:
        tenant_id: ID del tenant
        invoice_id: ID (UUID) de la factura a enviar
        recipient_email: Email del destinatario (opcional, usa el del cliente si vacío)
    """
    return await _send_invoice_by_email_async(tenant_id, invoice_id, recipient_email)
