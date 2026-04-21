"""
Core async logic for invoice creation.
Called by _invoice_write_tools.py — not exported as an agent tool.
"""

import logging
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select

from app.agents.validators.billing import validate_invoice_data
from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, InvoiceLine

from ._client_tools import _resolve_client
from ._invoice_pdf_tools import _generate_and_save_invoice_pdf, _load_invoice_template
from ._invoice_validators import parse_amount_str

logger = logging.getLogger(__name__)


async def _create_invoice_async(
    tenant_id: str,
    client_name: str,
    concept: str,
    amount_base_str: str,
    vat_rate: float,
    invoice_date_str: str,
    client_nif: str,
    notes: str,
    issuer_name: str,
    issuer_nif: str,
    issuer_address: str,
    issuer_email: str,
) -> str:
    amount, err = parse_amount_str(amount_base_str)
    if err:
        return err

    # Parsear fecha
    inv_date_str = invoice_date_str.strip() if invoice_date_str else date.today().isoformat()
    try:
        inv_date = date.fromisoformat(inv_date_str)
    except ValueError:
        return f"Error: Fecha no válida: '{inv_date_str}'. Usa formato YYYY-MM-DD."

    # Resolver cliente
    client_result = await _resolve_client(tenant_id, client_name, client_nif)
    if isinstance(client_result, str):
        return client_result
    resolved_client_id, resolved_name, resolved_nif = client_result

    # Validar
    validation = validate_invoice_data(
        client_nif=resolved_nif,
        amount_base=amount,
        vat_rate=vat_rate,
        invoice_date=inv_date,
    )
    if not validation.is_valid:
        return f"Error de validación: {'; '.join(validation.errors)}"

    # Aprobación humana si > 5000€
    if amount > Decimal("5000"):
        tax = round(amount * Decimal(str(vat_rate)) / 100, 2)
        return (
            f"APROBACIÓN REQUERIDA: La factura supera el umbral de 5.000€.\n"
            f"Cliente: {resolved_name} (NIF: {resolved_nif})\nConcepto: {concept}\n"
            f"Base: {amount}€ + IVA {vat_rate}% = {amount + tax}€\n"
            f"La factura NO se ha creado. Requiere aprobación humana desde el dashboard."
        )

    tax_amount = round(amount * Decimal(str(vat_rate)) / 100, 2)
    total_amount = amount + tax_amount
    inv_datetime = datetime(inv_date.year, inv_date.month, inv_date.day, tzinfo=UTC)
    invoice_number = f"IA-{uuid.uuid4().hex[:8].upper()}"
    warnings = validation.warnings[:]

    async with AsyncSessionLocal() as db:
        try:
            # Upsert cliente
            if resolved_client_id:
                result = await db.execute(select(Client).where(Client.id == resolved_client_id))
                local_client = result.scalars().first()
            else:
                result = await db.execute(
                    select(Client).where(
                        Client.tenant_id == UUID(tenant_id),
                        Client.nif == resolved_nif,
                        func.lower(Client.name) == resolved_name.lower(),
                    )
                )
                local_client = result.scalars().first()
                if not local_client:
                    result = await db.execute(
                        select(Client).where(
                            Client.tenant_id == UUID(tenant_id), Client.nif == resolved_nif
                        )
                    )
                    local_client = result.scalars().first()
            if not local_client:
                local_client = Client(
                    tenant_id=UUID(tenant_id), nif=resolved_nif, name=resolved_name
                )
                db.add(local_client)
                await db.flush()

            new_invoice = Invoice(
                tenant_id=UUID(tenant_id),
                client_id=local_client.id,
                invoice_number=invoice_number,
                date=inv_datetime,
                amount_base=amount,
                tax_amount=tax_amount,
                amount_total=total_amount,
                notes=notes or None,
                status="draft",
            )
            db.add(new_invoice)
            await db.flush()

            invoice_line = InvoiceLine(
                invoice_id=new_invoice.id,
                description=concept or "Servicio",
                quantity=1.0,
                unit_price=float(amount),
                discount_percentage=0.0,
                tax_percentage=float(vat_rate),
                total=float(total_amount),
            )
            db.add(invoice_line)

            try:
                from app.services.event_bus import emit_event

                await emit_event(
                    db=db,
                    tenant_id=UUID(tenant_id),
                    user_id=None,
                    event_name="invoice_created",
                    context={
                        "invoice_id": str(new_invoice.id),
                        "invoice_number": invoice_number,
                        "amount_total": float(total_amount),
                        "client_name": resolved_name,
                        "client_nif": resolved_nif,
                        "concept": concept,
                    },
                )
            except Exception as ev_err:
                warnings.append(f"Evento invoice_created no emitido: {ev_err}")

            await db.commit()
            await db.refresh(new_invoice)
        except Exception as e:
            await db.rollback()
            return f"Error al guardar la factura en base de datos: {e}"

    theme_config, template_name = await _load_invoice_template(tenant_id)
    document_id, pdf_warn = await _generate_and_save_invoice_pdf(
        tenant_id,
        new_invoice,
        invoice_line,
        local_client,
        issuer_name,
        issuer_nif,
        issuer_address,
        issuer_email,
        theme_config,
    )
    if pdf_warn:
        warnings.append(pdf_warn)

    warn_text = f"\nAvisos: {'; '.join(warnings)}" if warnings else ""
    return (
        f"Factura creada correctamente.\n"
        f"Número: {invoice_number}\n"
        f"Cliente: {resolved_name} (NIF: {resolved_nif})\n"
        f"Concepto: {concept}\n"
        f"Base: {float(amount):.2f}€ + IVA {vat_rate}% = {float(total_amount):.2f}€\n"
        f"Estado: DRAFT (borrador)\n"
        f"ID factura: {new_invoice.id}\n"
        f"Documento PDF: {document_id or 'No generado'}\n"
        f"Plantilla visual: {template_name or 'predeterminada del sistema'}"
        f"{warn_text}"
    )
