"""
Invoice write tools: update_status, update, and the create_invoice @tool.
Heavy creation logic lives in _invoice_create_async.py.
"""

import logging
from decimal import Decimal
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Invoice, InvoiceLine

from ._invoice_create_async import _create_invoice_async
from ._invoice_validators import parse_amount_str

logger = logging.getLogger(__name__)


async def _update_invoice_status_async(tenant_id: str, invoice_id: str, new_status: str) -> str:
    allowed = {"draft", "pending", "paid", "cancelled"}
    if new_status not in allowed:
        return f"Error: Estado '{new_status}' no válido. Opciones: {', '.join(sorted(allowed))}"

    VALID_TRANSITIONS = {
        "draft": {"pending", "cancelled"},
        "pending": {"paid", "cancelled"},
        "paid": {"cancelled"},
        "cancelled": set(),
    }

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == UUID(tenant_id),
                    Invoice.id == UUID(invoice_id),
                )
            )
            invoice = result.scalar_one_or_none()
            if not invoice:
                return f"Error: Factura con ID {invoice_id} no encontrada."

            old_status = invoice.status or "draft"
            if new_status not in VALID_TRANSITIONS.get(old_status, set()):
                return (
                    f"Error: No se puede pasar de '{old_status}' a '{new_status}'. "
                    f"Transiciones válidas desde '{old_status}': {VALID_TRANSITIONS.get(old_status, set()) or 'ninguna (estado final)'}."
                )

            invoice.status = new_status
            await db.commit()

            try:
                from app.services.event_bus import emit_event
                await emit_event(
                    db=db, tenant_id=UUID(tenant_id), user_id=None,
                    event_name=f"invoice_{new_status}",
                    context={
                        "invoice_id": invoice_id,
                        "invoice_number": invoice.invoice_number,
                        "old_status": old_status,
                        "new_status": new_status,
                    },
                )
            except Exception:
                logger.debug(
                    "Failed to emit invoice_%s event for %s", new_status, invoice_id, exc_info=True
                )

            return f"Factura {invoice.invoice_number} actualizada: {old_status} → {new_status}."
    except Exception as e:
        return f"Error actualizando factura: {e}"


async def _update_invoice_async(
    tenant_id: str,
    invoice_id: str,
    concept: str,
    amount_base_str: str,
    vat_rate: float,
    notes: str,
) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Invoice).where(
                    Invoice.tenant_id == UUID(tenant_id),
                    Invoice.id == UUID(invoice_id),
                )
            )
            invoice = result.scalar_one_or_none()
            if not invoice:
                return f"Error: Factura con ID {invoice_id} no encontrada."

            if invoice.status != "draft":
                return f"Error: Solo se pueden editar facturas en borrador. Estado actual: {invoice.status}."

            changes = []

            if notes:
                invoice.notes = notes
                changes.append(f"notas='{notes[:50]}...'")

            new_base = None
            if amount_base_str.strip():
                new_base, err = parse_amount_str(amount_base_str)
                if err:
                    return err
                invoice.amount_base = new_base
                changes.append(f"base={new_base}€")

            new_vat = vat_rate if vat_rate >= 0 else None
            if new_vat is not None and new_vat not in (0, 4, 10, 21):
                return f"Error: IVA {new_vat}% no válido. Opciones: 0, 4, 10, 21."

            base = new_base if new_base is not None else invoice.amount_base
            vat = (
                Decimal(str(new_vat))
                if new_vat is not None
                else (
                    Decimal(str((float(invoice.tax_amount) / float(invoice.amount_base) * 100)))
                    if invoice.amount_base and float(invoice.amount_base) > 0
                    else Decimal("21")
                )
            )
            tax = round(base * vat / 100, 2)
            total = base + tax

            invoice.tax_amount = tax
            invoice.amount_total = total
            if new_vat is not None:
                changes.append(f"IVA={new_vat}%")

            if concept or new_base is not None:
                lines_result = await db.execute(
                    select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
                )
                first_line = lines_result.scalar_one_or_none()
                if first_line:
                    if concept:
                        first_line.description = concept
                        changes.append(f"concepto='{concept[:40]}'")
                    if new_base is not None:
                        first_line.unit_price = float(new_base)
                        first_line.total = float(total)
                    if new_vat is not None:
                        first_line.tax_percentage = float(new_vat)

            if not changes:
                return "No se especificaron cambios. Indica qué quieres modificar."

            await db.commit()
            return (
                f"Factura {invoice.invoice_number} actualizada: {', '.join(changes)}.\n"
                f"Nuevos totales: Base {float(base):.2f}€ + IVA = {float(total):.2f}€."
            )
    except Exception as e:
        return f"Error modificando factura: {e}"


# ─── @tool decorated public functions ─────────────────────────────────────────


@tool
async def create_invoice(
    tenant_id: str,
    client_name: str,
    concept: str,
    amount_base: str,
    vat_rate: float = 21.0,
    invoice_date: str = "",
    client_nif: str = "",
    notes: str = "",
    issuer_name: str = "",
    issuer_nif: str = "",
    issuer_address: str = "",
    issuer_email: str = "",
) -> str:
    """
    Crea una factura borrador con validación española completa.
    Valida NIF/CIF, IVA, importe. Genera PDF y guarda en BD.
    Si el importe supera 5000€, requiere aprobación humana.

    Args:
        tenant_id: ID del tenant
        client_name: Nombre o razón social del cliente
        concept: Descripción del servicio o producto facturado
        amount_base: Base imponible en euros (ej: "1500.00"). Separador decimal: punto
        vat_rate: Tipo de IVA (0, 4, 10 o 21). Por defecto 21
        invoice_date: Fecha de factura YYYY-MM-DD. Si vacío, usa hoy
        client_nif: NIF o CIF del cliente (9 caracteres). Si vacío, se busca por nombre en BD
        notes: Notas adicionales opcionales
        issuer_name: Nombre de la empresa emisora (si distinta del tenant)
        issuer_nif: NIF/CIF de la empresa emisora
        issuer_address: Dirección de la empresa emisora
        issuer_email: Email de la empresa emisora
    """
    try:
        _amount = float(amount_base) if isinstance(amount_base, str) else amount_base
        if _amount <= 0:
            return f"Error: el importe debe ser mayor que 0 (recibido: {amount_base})"
        amount_base = str(_amount)
    except (ValueError, TypeError):
        return f"Error: importe inválido '{amount_base}'. Debe ser un número positivo."

    try:
        _vat = float(vat_rate) if isinstance(vat_rate, str) else vat_rate
        if not (0 <= _vat <= 100):
            return f"Error: el tipo de IVA debe estar entre 0 y 100 (recibido: {vat_rate})"
        vat_rate = _vat
    except (ValueError, TypeError):
        return f"Error: tipo de IVA inválido '{vat_rate}'."

    if invoice_date:
        try:
            from datetime import date as _date
            if isinstance(invoice_date, str):
                _date.fromisoformat(invoice_date)
        except ValueError:
            return f"Error: fecha de factura inválida '{invoice_date}'. Usa formato YYYY-MM-DD."

    return await _create_invoice_async(
        tenant_id, client_name, concept, amount_base, vat_rate,
        invoice_date, client_nif, notes, issuer_name, issuer_nif, issuer_address, issuer_email,
    )


@tool
async def update_invoice_status(tenant_id: str, invoice_id: str, new_status: str) -> str:
    """
    Cambia el estado de una factura existente.
    Transiciones permitidas: draft→pending, pending→paid, cualquiera→cancelled.

    Args:
        tenant_id: ID del tenant
        invoice_id: ID (UUID) de la factura a modificar
        new_status: Nuevo estado ('draft', 'pending', 'paid', 'cancelled')
    """
    return await _update_invoice_status_async(tenant_id, invoice_id, new_status)


@tool
async def update_invoice(
    tenant_id: str,
    invoice_id: str,
    concept: str = "",
    amount_base: str = "",
    vat_rate: float = -1,
    notes: str = "",
) -> str:
    """
    Modifica los datos de una factura en estado DRAFT (borrador).
    Solo facturas en borrador pueden editarse. Recalcula IVA y total automáticamente.

    Args:
        tenant_id: ID del tenant
        invoice_id: ID (UUID) de la factura a modificar
        concept: Nuevo concepto/descripción (vacío = no cambiar)
        amount_base: Nueva base imponible en euros (vacío = no cambiar)
        vat_rate: Nuevo tipo de IVA (0, 4, 10, 21). -1 = no cambiar
        notes: Nuevas notas (vacío = no cambiar)
    """
    return await _update_invoice_async(tenant_id, invoice_id, concept, amount_base, vat_rate, notes)
