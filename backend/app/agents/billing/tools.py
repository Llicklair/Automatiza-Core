"""
Billing agent tool definitions.

All @tool decorated functions and their private async helpers.
"""

import json
import logging
import os
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import desc, func, or_, select

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import (
    delete_tenant_knowledge,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
)
from app.agents.validators.billing import validate_invoice_data
from app.core.config import settings
from app.db.base import AsyncSessionLocal
from app.db.models.billing import DeliveryNote, DeliveryNoteLine, DocumentTemplate
from app.db.models.models import Client, Invoice, InvoiceLine, TenantDocument

logger = logging.getLogger(__name__)


# ─── Herramientas del agente ──────────────────────────────────────────────────


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
    # Validate inputs
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


async def _resolve_client(
    tenant_id: str, client_name: str, client_nif: str = ""
) -> "tuple[UUID | None, str, str] | str":
    """
    Busca un cliente por nombre (y opcionalmente NIF).
    Devuelve (client_id, resolved_name, resolved_nif) o un string de error.
    Si se pasa client_nif, omite la búsqueda y devuelve (None, name, nif).
    """
    name = client_name.strip()
    nif = client_nif.strip()
    if nif:
        return None, name, nif
    if not name:
        return "Error: Debes indicar el nombre del cliente o su NIF."

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Client).where(
                Client.tenant_id == UUID(tenant_id),
                func.lower(Client.name) == name.lower(),
            )
        )
        exact = res.scalars().all()
        if len(exact) == 1:
            c = exact[0]
            return c.id, c.name, c.nif or ""
        if len(exact) > 1:
            opts = ", ".join(f"'{c.name}' (NIF: {c.nif or 'N/A'})" for c in exact)
            return f"Error: Hay {len(exact)} clientes con el nombre '{client_name}': {opts}. Especifica el NIF."

        res = await db.execute(
            select(Client)
            .where(
                Client.tenant_id == UUID(tenant_id),
                func.lower(Client.name).contains(name.lower()),
            )
            .order_by(Client.name)
            .limit(5)
        )
        partial = res.scalars().all()
        if len(partial) == 1:
            c = partial[0]
            return c.id, c.name, c.nif or ""
        if len(partial) > 1:
            opts = ", ".join(f"'{c.name}' (NIF: {c.nif or 'N/A'})" for c in partial)
            return (
                f"Error: '{client_name}' coincide con {len(partial)} clientes: {opts}. "
                "Especifica el NIF del cliente para evitar facturar al equivocado."
            )
    return (
        f"Error: No se encontró el cliente '{client_name}'. "
        "Comprueba el nombre o proporciona el NIF directamente."
    )


async def _load_invoice_template(tenant_id: str) -> tuple[dict | None, str | None]:
    """Carga la plantilla visual activa del tenant. Devuelve (theme_config, template_name)."""
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
            "lines": [{
                "description": invoice_line.description,
                "quantity": invoice_line.quantity,
                "unit_price": invoice_line.unit_price,
                "tax_percentage": invoice_line.tax_percentage,
                "total": invoice_line.total,
            }],
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
    # Parsear importe
    try:
        raw = amount_base_str.strip()
        raw = raw.replace(".", "").replace(",", ".") if re.search(r"\.\d{3}(?:[,\d]|$)", raw) else raw.replace(",", ".")
        amount = Decimal(raw)
    except (InvalidOperation, Exception):
        return f"Error: Importe no válido: '{amount_base_str}'. Usa formato '1500.00'."

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
        client_nif=resolved_nif, amount_base=amount, vat_rate=vat_rate, invoice_date=inv_date,
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
                        select(Client).where(Client.tenant_id == UUID(tenant_id), Client.nif == resolved_nif)
                    )
                    local_client = result.scalars().first()
            if not local_client:
                local_client = Client(tenant_id=UUID(tenant_id), nif=resolved_nif, name=resolved_name)
                db.add(local_client)
                await db.flush()

            new_invoice = Invoice(
                tenant_id=UUID(tenant_id), client_id=local_client.id,
                invoice_number=invoice_number, date=inv_datetime,
                amount_base=amount, tax_amount=tax_amount, amount_total=total_amount,
                notes=notes or None, status="draft",
            )
            db.add(new_invoice)
            await db.flush()

            invoice_line = InvoiceLine(
                invoice_id=new_invoice.id, description=concept or "Servicio",
                quantity=1.0, unit_price=float(amount), discount_percentage=0.0,
                tax_percentage=float(vat_rate), total=float(total_amount),
            )
            db.add(invoice_line)

            try:
                from app.services.event_bus import emit_event
                await emit_event(
                    db=db, tenant_id=UUID(tenant_id), user_id=None, event_name="invoice_created",
                    context={"invoice_id": str(new_invoice.id), "invoice_number": invoice_number,
                             "amount_total": float(total_amount), "client_name": resolved_name,
                             "client_nif": resolved_nif, "concept": concept},
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
        tenant_id, new_invoice, invoice_line, local_client,
        issuer_name, issuer_nif, issuer_address, issuer_email, theme_config,
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


@tool
async def list_invoices(tenant_id: str, limit: int = 15) -> str:
    """
    Lista las facturas más recientes del tenant con cliente, importe y estado.
    Útil para consultas como "¿cuánto he facturado?", "ver facturas", "listado".

    Args:
        tenant_id: ID del tenant
        limit: Número máximo de facturas a devolver (por defecto 15)
    """
    return await _list_invoices_async(tenant_id, limit)


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

            # Cargar document_ids en una sola consulta
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
                    f"- {inv.invoice_number}: {cli.name} | "
                    f"{float(inv.amount_total):.2f}€ | "
                    f"{inv.date.strftime('%Y-%m-%d')} | "
                    f"Estado: {inv.status}{doc_info}"
                )

            return (
                f"Facturas recientes ({len(rows)}):\n"
                + "\n".join(lines)
                + f"\n\nTotal facturado: {total_facturado:.2f}€\n"
                + "(Usa el document_id con send_invoice_by_email o pásalo al agente de email como attachment_id)"
            )
    except Exception as e:
        return f"Error consultando facturas: {e}"


@tool
async def search_client(tenant_id: str, query: str = "") -> str:
    """
    Busca clientes del tenant por nombre o NIF.
    Útil para encontrar el NIF antes de crear una factura, o para consultas de clientes.

    Args:
        tenant_id: ID del tenant
        query: Texto a buscar (nombre parcial o NIF). Si vacío, lista los primeros 10 clientes.
    """
    return await _search_client_async(tenant_id, query)


async def _search_client_async(tenant_id: str, query: str) -> str:

    try:
        async with AsyncSessionLocal() as db:
            base_q = select(Client).where(Client.tenant_id == UUID(tenant_id))
            if query.strip():
                q = query.strip()
                base_q = base_q.where(
                    or_(
                        func.lower(Client.name).contains(q.lower()),
                        Client.nif.ilike(f"%{q}%"),
                    )
                )
            base_q = base_q.order_by(Client.name).limit(10)

            result = await db.execute(base_q)
            clients = result.scalars().all()

            if not clients:
                return f"No se encontraron clientes{' con búsqueda: ' + query if query else ''}."

            lines = [
                f"- {c.name} | NIF: {c.nif or 'N/A'} | Email: {c.email or 'N/A'} | ID: {c.id}"
                for c in clients
            ]
            return f"Clientes encontrados ({len(clients)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error buscando clientes: {e}"


# ─── Herramientas de modificación ─────────────────────────────────────────────


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

            # Emitir evento
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

            # Actualizar base imponible y/o IVA
            new_base = None
            if amount_base_str.strip():
                try:
                    raw = amount_base_str.strip().replace(",", ".")
                    new_base = Decimal(raw)
                    invoice.amount_base = new_base
                    changes.append(f"base={new_base}€")
                except (InvalidOperation, Exception):
                    return f"Error: Importe no válido: '{amount_base_str}'."

            new_vat = vat_rate if vat_rate >= 0 else None
            if new_vat is not None and new_vat not in (0, 4, 10, 21):
                return f"Error: IVA {new_vat}% no válido. Opciones: 0, 4, 10, 21."

            # Recalcular totales
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

            # Actualizar línea de factura si hay concepto o importe nuevo
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


async def _send_invoice_by_email_async(
    tenant_id: str, invoice_id: str, recipient_email: str
) -> str:

    try:
        async with AsyncSessionLocal() as db:
            # Cargar factura + cliente
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

            # Determinar email destino
            email_to = recipient_email.strip() if recipient_email else (client.email or "")
            if not email_to:
                return (
                    f"Error: El cliente '{client.name}' no tiene email registrado. "
                    "Proporciona el email del destinatario."
                )

            # Buscar PDF de la factura
            doc_result = await db.execute(
                select(TenantDocument).where(
                    TenantDocument.tenant_id == UUID(tenant_id),
                    TenantDocument.file_name.contains(invoice.invoice_number),
                    TenantDocument.file_type == "application/pdf",
                )
            )
            pdf_doc = doc_result.scalar_one_or_none()
            doc_id = str(pdf_doc.id) if pdf_doc else None

        # Enviar usando el servicio real de email
        from app.agents.email import send_email_direct

        result_text = await send_email_direct(
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


# ─── Herramientas de albaranes ────────────────────────────────────────────────


@tool
async def list_albaranes(tenant_id: str, status: str = "") -> str:
    """
    Lista los albaranes del tenant. Opcionalmente filtra por status: draft, confirmed, delivered.

    Args:
        tenant_id: ID del tenant
        status: Filtro de estado (vacío = todos)
    """
    try:
        async with AsyncSessionLocal() as db:
            q = select(DeliveryNote).where(DeliveryNote.tenant_id == UUID(tenant_id))
            if status:
                q = q.where(DeliveryNote.status == status)
            q = q.order_by(desc(DeliveryNote.created_at)).limit(20)
            result = await db.execute(q)
            notes = result.scalars().all()
            if not notes:
                return "No hay albaranes registrados."
            lines = [
                f"- {n.albaran_number} | {n.date} | {n.status} | {float(n.amount_total):.2f}€"
                for n in notes
            ]
            return "Albaranes:\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando albaranes: {e}"


@tool
async def create_albaran(
    tenant_id: str,
    client_name: str,
    lines_json: str,
    albaran_date: str = "",
    notes: str = "",
) -> str:
    """
    Crea un albarán de entrega.

    Args:
        tenant_id: ID del tenant
        client_name: Nombre del cliente
        lines_json: JSON string con lista de líneas, cada una con: description, quantity, unit_price, tax_percentage
        albaran_date: Fecha del albarán en formato YYYY-MM-DD (opcional, hoy por defecto)
        notes: Observaciones opcionales
    """
    try:
        lines_data = json.loads(lines_json)
        entry_date = date.fromisoformat(albaran_date) if albaran_date else date.today()

        client_result = await _resolve_client(tenant_id, client_name)
        if isinstance(client_result, str):
            return client_result
        client_id, _resolved_name, _resolved_nif = client_result

        async with AsyncSessionLocal() as db:
            # Auto-number
            last_result = await db.execute(
                select(DeliveryNote)
                .where(DeliveryNote.tenant_id == UUID(tenant_id))
                .order_by(desc(DeliveryNote.created_at))
                .limit(1)
            )
            last = last_result.scalar_one_or_none()
            try:
                num = int(last.albaran_number.split("-")[-1]) + 1 if last and last.albaran_number else 1
            except (ValueError, IndexError):
                num = 1
            albaran_number = f"ALB-{num:05d}"

            amount_base = Decimal("0")
            tax_amount = Decimal("0")
            for line in lines_data:
                base = Decimal(str(line.get("quantity", 1))) * Decimal(str(line.get("unit_price", 0)))
                tax_amount += base * Decimal(str(line.get("tax_percentage", 21))) / Decimal("100")
                amount_base += base
            amount_total = amount_base + tax_amount

            note = DeliveryNote(
                tenant_id=UUID(tenant_id), client_id=client_id,
                albaran_number=albaran_number, date=entry_date,
                notes=notes or None, amount_base=amount_base,
                tax_amount=tax_amount, amount_total=amount_total,
            )
            db.add(note)
            await db.flush()

            for line in lines_data:
                base = Decimal(str(line.get("quantity", 1))) * Decimal(str(line.get("unit_price", 0)))
                total = base + base * Decimal(str(line.get("tax_percentage", 21))) / Decimal("100")
                db.add(DeliveryNoteLine(
                    albaran_id=note.id,
                    description=line.get("description", ""),
                    quantity=line.get("quantity", 1),
                    unit_price=line.get("unit_price", 0),
                    tax_percentage=line.get("tax_percentage", 21),
                    total=total,
                ))

            await db.commit()
            return (
                f"Albarán {albaran_number} creado correctamente para {client_name or 'sin cliente'}. "
                f"Total: {float(amount_total):.2f}€"
            )
    except Exception as e:
        return f"Error creando albarán: {e}"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    create_invoice,
    list_invoices,
    search_client,
    update_invoice_status,
    update_invoice,
    send_invoice_by_email,
    list_albaranes,
    create_albaran,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
    delete_tenant_knowledge,
]
