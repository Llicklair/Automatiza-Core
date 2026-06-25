"""
Invoice write tools: update_status, update, and the create_invoice @tool.
Heavy creation logic lives in _invoice_create_async.py.
"""

import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Invoice, InvoiceLine

from ._invoice_create_async import _create_invoice_async
from ._invoice_validators import parse_amount_str

logger = logging.getLogger(__name__)


async def _update_invoice_status_async(tenant_id: str, invoice_id: str, new_status: str) -> str:
    # Las transiciones válidas las define la máquina de estado canónica
    # (services/state_machine), única fuente de verdad compartida con la capa de
    # servicios. NO duplicar la tabla aquí: una factura 'paid' NO se cancela (se
    # emite una rectificativa); solo admite revertir a 'sent' (desconciliar cobro).
    from app.services.state_machine import (
        InvalidTransitionError,
        allowed_next_states,
        validate_transition,
    )

    allowed = {"draft", "pending", "sent", "paid", "cancelled"}
    if new_status not in allowed:
        return f"Error: Estado '{new_status}' no válido. Opciones: {', '.join(sorted(allowed))}"

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
            try:
                validate_transition("Invoice", old_status, new_status)
            except InvalidTransitionError:
                nexts = allowed_next_states("Invoice", old_status)
                return (
                    f"Error: No se puede pasar de '{old_status}' a '{new_status}'. "
                    f"Transiciones válidas desde '{old_status}': {nexts or 'ninguna (estado final)'}."
                )

            invoice.status = new_status
            await db.commit()

            try:
                from app.services.event_bus import emit_event

                await emit_event(
                    db=db,
                    tenant_id=UUID(tenant_id),
                    user_id=None,
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

            # Parseo de los cambios solicitados ──────────────────────────────
            new_base = None
            if amount_base_str.strip():
                new_base, err = parse_amount_str(amount_base_str)
                if err:
                    return err

            new_vat = vat_rate if vat_rate >= 0 else None
            if new_vat is not None and new_vat not in (0, 4, 10, 21):
                return f"Error: IVA {new_vat}% no válido. Opciones: 0, 4, 10, 21."

            wants_fiscal_change = new_base is not None or new_vat is not None

            # ── Barrera fiscal (VeriFactu) ───────────────────────────────────
            # Si la factura ya tiene registro VeriFactu, su huella encadena
            # base/IVA/total (RD 1007/2023): mutarlos rompería la cadena
            # append-only. El agente NO toca importes en ese caso; hay que emitir
            # una rectificativa. Mismo invariante que delete_invoice en commands.
            if wants_fiscal_change:
                from app.db.models.billing import VerifactuRecord

                vf = await db.execute(
                    select(VerifactuRecord.id)
                    .where(VerifactuRecord.invoice_id == invoice.id)
                    .limit(1)
                )
                if vf.scalar_one_or_none() is not None:
                    return (
                        "Error: la factura ya tiene registro VeriFactu (cadena inmutable). "
                        "No se pueden cambiar base ni IVA desde el asistente; "
                        "emite una factura rectificativa para corregir los importes."
                    )

            changes = []
            if notes:
                invoice.notes = notes
                changes.append(f"notas='{notes[:50]}...'")

            # ── Importes con Decimal vía compute_invoice_totals (nunca float) ─
            if wants_fiscal_change:
                from app.services.billing.queries import compute_invoice_totals

                base = new_base if new_base is not None else invoice.amount_base
                if new_vat is not None:
                    vat_pct = float(new_vat)
                elif invoice.amount_base and float(invoice.amount_base) > 0:
                    vat_pct = float(round(float(invoice.tax_amount) / float(invoice.amount_base) * 100))
                else:
                    vat_pct = 21.0
                try:
                    totals = compute_invoice_totals(
                        [{"quantity": 1, "unit_price": float(base), "tax_percentage": vat_pct}]
                    )
                except ValueError as e:
                    return f"Error: {e}"

                invoice.amount_base = totals["amount_base"]
                invoice.tax_amount = totals["tax_amount"]
                invoice.amount_total = totals["amount_total"]
                if new_base is not None:
                    changes.append(f"base={totals['amount_base']}€")
                if new_vat is not None:
                    changes.append(f"IVA={new_vat}%")

            if concept or wants_fiscal_change:
                lines_result = await db.execute(
                    select(InvoiceLine).where(InvoiceLine.invoice_id == invoice.id)
                )
                first_line = lines_result.scalar_one_or_none()
                if first_line:
                    if concept:
                        first_line.description = concept
                        changes.append(f"concepto='{concept[:40]}'")
                    if new_base is not None:
                        first_line.unit_price = float(invoice.amount_base)
                        first_line.total = float(invoice.amount_total)
                    if new_vat is not None:
                        first_line.tax_percentage = float(new_vat)

            if not changes:
                return "No se especificaron cambios. Indica qué quieres modificar."

            await db.commit()
            return (
                f"Factura {invoice.invoice_number} actualizada: {', '.join(changes)}.\n"
                f"Nuevos totales: Base {float(invoice.amount_base):.2f}€ + IVA "
                f"= {float(invoice.amount_total):.2f}€."
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
        tenant_id,
        client_name,
        concept,
        amount_base,
        vat_rate,
        invoice_date,
        client_nif,
        notes,
        issuer_name,
        issuer_nif,
        issuer_address,
        issuer_email,
    )


@tool
async def update_invoice_status(tenant_id: str, invoice_id: str, new_status: str) -> str:
    """
    Cambia el estado de una factura existente. Las transiciones válidas las
    define la máquina de estado: una factura pagada NO se cancela (emite una
    rectificativa); solo puede revertir a 'sent' al desconciliar un cobro.

    Args:
        tenant_id: ID del tenant
        invoice_id: ID (UUID) de la factura a modificar
        new_status: Nuevo estado ('draft', 'pending', 'sent', 'paid', 'cancelled')
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
    Solo facturas en borrador pueden editarse. Recalcula IVA y total con Decimal.
    Si la factura ya tiene registro VeriFactu, NO se pueden cambiar base ni IVA
    (la cadena es inmutable): hay que emitir una factura rectificativa.

    Args:
        tenant_id: ID del tenant
        invoice_id: ID (UUID) de la factura a modificar
        concept: Nuevo concepto/descripción (vacío = no cambiar)
        amount_base: Nueva base imponible en euros (vacío = no cambiar)
        vat_rate: Nuevo tipo de IVA (0, 4, 10, 21). -1 = no cambiar
        notes: Nuevas notas (vacío = no cambiar)
    """
    return await _update_invoice_async(tenant_id, invoice_id, concept, amount_base, vat_rate, notes)
