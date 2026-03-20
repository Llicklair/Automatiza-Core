"""
Agente de Facturación — Autónomo con LangGraph.

El LLM decide qué herramientas usar según la intención del usuario:
  - Crear factura → create_invoice
  - Consultar facturas → list_invoices
  - Buscar cliente → search_client

Cada herramienta ejecuta lógica determinista (validación, BD, PDF).
El LLM solo razona y elige; nunca toca datos directamente.
"""
import json
import logging
import os
import re
import uuid
from calendar import timegm
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel, Field

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.agents.validators.billing import validate_invoice_data
from app.core.config import settings
from app.core.llm_factory import get_llm
from app.core.prompt_sanitizer import sanitize_user_input
from app.integrations.holded import HoldedClient

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0)


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
    return await _create_invoice_async(
            tenant_id, client_name, concept, amount_base, vat_rate,
            invoice_date, client_nif, notes,
            issuer_name, issuer_nif, issuer_address, issuer_email
    )


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
    from sqlalchemy import select, or_, func
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client, Invoice, InvoiceLine, TenantDocument

    today = date.today().isoformat()

    # ── Parsear importe ──
    try:
        raw = amount_base_str.strip()
        if re.search(r'\.\d{3}(?:[,\d]|$)', raw):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", ".")
        amount = Decimal(raw)
    except (InvalidOperation, Exception):
        return f"Error: Importe no válido: '{amount_base_str}'. Usa formato '1500.00'."

    # ── Parsear fecha ──
    inv_date_str = invoice_date_str.strip() if invoice_date_str else today
    try:
        inv_date = date.fromisoformat(inv_date_str)
    except ValueError:
        return f"Error: Fecha no válida: '{inv_date_str}'. Usa formato YYYY-MM-DD."

    # ── Resolución de cliente ──
    resolved_nif = client_nif.strip() if client_nif else ""
    resolved_name = client_name.strip()

    if not resolved_nif:
        try:
            async with AsyncSessionLocal() as db:
                if resolved_name:
                    res = await db.execute(
                        select(Client).where(
                            Client.tenant_id == UUID(tenant_id),
                            or_(
                                func.lower(Client.name) == resolved_name.lower(),
                                func.lower(Client.name).contains(resolved_name.lower()),
                            )
                        ).limit(1)
                    )
                else:
                    res = await db.execute(
                        select(Client).where(
                            Client.tenant_id == UUID(tenant_id)
                        ).order_by(Client.created_at.asc()).limit(1)
                    )
                client = res.scalar_one_or_none()
                if client:
                    resolved_nif = client.nif
                    resolved_name = client.name
        except Exception:
            pass

    if not resolved_nif:
        return (
            f"Error: No se encontró el NIF del cliente '{resolved_name}'. "
            "Proporciona el NIF directamente o crea el cliente primero."
        )

    # ── Validación determinista ──
    validation = validate_invoice_data(
        client_nif=resolved_nif,
        amount_base=amount,
        vat_rate=vat_rate,
        invoice_date=inv_date,
    )
    if not validation.is_valid:
        return f"Error de validación: {'; '.join(validation.errors)}"

    # ── Aprobación humana si > 5000€ ──
    if amount > Decimal("5000"):
        tax = round(amount * Decimal(str(vat_rate)) / 100, 2)
        total = amount + tax
        return (
            f"APROBACIÓN REQUERIDA: La factura supera el umbral de 5.000€.\n"
            f"Cliente: {resolved_name} (NIF: {resolved_nif})\n"
            f"Concepto: {concept}\n"
            f"Base: {amount}€ + IVA {vat_rate}% = {total}€\n"
            f"La factura NO se ha creado. Requiere aprobación humana desde el dashboard."
        )

    # ── Transacción atómica: Client + Invoice + InvoiceLine ──
    tax_amount = round(amount * Decimal(str(vat_rate)) / 100, 2)
    total_amount = amount + tax_amount
    inv_datetime = datetime(inv_date.year, inv_date.month, inv_date.day, tzinfo=UTC)
    invoice_number = f"IA-{uuid.uuid4().hex[:8].upper()}"

    warnings = validation.warnings[:]

    async with AsyncSessionLocal() as db:
        try:
            # Upsert cliente
            result = await db.execute(
                select(Client).where(
                    Client.tenant_id == UUID(tenant_id),
                    Client.nif == resolved_nif,
                )
            )
            local_client = result.scalars().first()
            if not local_client:
                local_client = Client(
                    tenant_id=UUID(tenant_id),
                    nif=resolved_nif,
                    name=resolved_name,
                )
                db.add(local_client)
                await db.flush()

            # Crear factura
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

            # Línea de factura
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

            # Emitir evento
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

            # ── Generar PDF ──
            document_id = None
            try:
                from app.services.pdf_service import generate_invoice_pdf

                inv_pdf_data = {
                    "number": new_invoice.invoice_number,
                    "date": new_invoice.date.isoformat(),
                    "amount_base": float(new_invoice.amount_base),
                    "tax_amount": float(new_invoice.tax_amount),
                    "amount_total": float(new_invoice.amount_total),
                    "notes": new_invoice.notes,
                    "client": {"name": local_client.name, "nif": local_client.nif},
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

                pdf_bytes = generate_invoice_pdf(inv_pdf_data)

                upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
                if not os.path.exists(upload_dir) and "WIN" in os.name.upper():
                    upload_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads")
                os.makedirs(upload_dir, exist_ok=True)

                file_name = f"Factura_{new_invoice.invoice_number}.pdf"
                file_path = os.path.join(upload_dir, file_name)
                with open(file_path, "wb") as f:
                    f.write(pdf_bytes)

                new_doc = TenantDocument(
                    tenant_id=UUID(tenant_id),
                    file_name=file_name,
                    file_path=file_path,
                    file_type="application/pdf",
                    file_size=len(pdf_bytes),
                    category="Facturas",
                    status="completed",
                )
                async with AsyncSessionLocal() as db_doc:
                    db_doc.add(new_doc)
                    await db_doc.commit()
                    await db_doc.refresh(new_doc)
                    document_id = str(new_doc.id)
            except Exception as pdf_err:
                warnings.append(f"Factura creada pero error al generar PDF: {pdf_err}")

        except Exception as e:
            await db.rollback()
            return f"Error al guardar la factura en base de datos: {e}"

    warn_text = f"\nAvisos: {'; '.join(warnings)}" if warnings else ""
    return (
        f"Factura creada correctamente.\n"
        f"Número: {invoice_number}\n"
        f"Cliente: {resolved_name} (NIF: {resolved_nif})\n"
        f"Concepto: {concept}\n"
        f"Base: {float(amount):.2f}€ + IVA {vat_rate}% = {float(total_amount):.2f}€\n"
        f"Estado: DRAFT (borrador)\n"
        f"ID factura: {new_invoice.id}\n"
        f"Documento PDF: {document_id or 'No generado'}"
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
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Invoice, Client

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

            total_facturado = 0
            lines = []
            for inv, cli in rows:
                total_facturado += float(inv.amount_total)
                lines.append(
                    f"- {inv.invoice_number}: {cli.name} | "
                    f"{float(inv.amount_total):.2f}€ | "
                    f"{inv.date.strftime('%Y-%m-%d')} | "
                    f"Estado: {inv.status}"
                )

            return (
                f"Facturas recientes ({len(rows)}):\n"
                + "\n".join(lines)
                + f"\n\nTotal facturado: {total_facturado:.2f}€"
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
    from sqlalchemy import select, or_, func
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Client

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
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Invoice, Client

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
                pass

            return (
                f"Factura {invoice.invoice_number} actualizada: {old_status} → {new_status}."
            )
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
    tenant_id: str, invoice_id: str, concept: str,
    amount_base_str: str, vat_rate: float, notes: str,
) -> str:
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Invoice, InvoiceLine

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
            vat = Decimal(str(new_vat)) if new_vat is not None else (
                Decimal(str((float(invoice.tax_amount) / float(invoice.amount_base) * 100)))
                if invoice.amount_base and float(invoice.amount_base) > 0 else Decimal("21")
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


async def _send_invoice_by_email_async(tenant_id: str, invoice_id: str, recipient_email: str) -> str:
    from sqlalchemy import select
    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Invoice, Client, TenantDocument

    try:
        async with AsyncSessionLocal() as db:
            # Cargar factura + cliente
            result = await db.execute(
                select(Invoice, Client).join(Client).where(
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

        # Enviar usando el email agent tools
        from app.agents.email_agent import send_email
        result_text = send_email.invoke({
            "tenant_id": tenant_id,
            "to": email_to,
            "subject": f"Factura {invoice.invoice_number} - {float(invoice.amount_total):.2f}€",
            "body": (
                f"Estimado/a {client.name},\n\n"
                f"Adjunto encontrará la factura {invoice.invoice_number} "
                f"por importe de {float(invoice.amount_total):.2f}€.\n\n"
                f"Concepto: {invoice.notes or 'Servicios profesionales'}\n"
                f"Fecha: {invoice.date.strftime('%d/%m/%Y')}\n\n"
                f"Un cordial saludo."
            ),
            "attachment_ids": [doc_id] if doc_id else None,
        })

        return f"Factura {invoice.invoice_number} enviada a {email_to}.\n{result_text}"
    except Exception as e:
        return f"Error enviando factura por email: {e}"


# ─── Lista de herramientas ────────────────────────────────────────────────────

tools = [
    create_invoice,
    list_invoices,
    search_client,
    update_invoice_status,
    update_invoice,
    send_invoice_by_email,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo LangGraph ───────────────────────────────────────────────

BILLING_SYSTEM_PROMPT = """Eres el Agente de Facturación de un ERP para PYMEs españolas. Tus capacidades:

1. **Crear facturas** con `create_invoice` — necesitas: client_name, concept, amount_base. El NIF se busca automáticamente.
2. **Consultar facturas** con `list_invoices` — facturas recientes, totales facturados, estados.
3. **Buscar clientes** con `search_client` — encontrar NIFs o verificar datos antes de facturar.
4. **Cambiar estado** con `update_invoice_status` — draft→pending→paid→cancelled.
5. **Editar factura** con `update_invoice` — modificar concepto, importe, IVA o notas (solo en borrador).
6. **Enviar por email** con `send_invoice_by_email` — envía la factura con PDF adjunto al cliente.
7. **Crear documentos** con `create_document` — exportar informes, listados CSV, resúmenes.
8. **Leer documentos** con `get_document_content` y `list_tenant_documents`.
9. **Memoria del tenant** con `get_tenant_knowledge` y `upsert_tenant_knowledge`.

REGLAS:
- Si el usuario quiere CREAR una factura, usa `create_invoice`. Extrae los datos de su mensaje.
- Si el usuario quiere VER/CONSULTAR/LISTAR facturas, usa `list_invoices`.
- Si necesitas el NIF de un cliente y no lo tienes, usa `search_client` primero.
- Para MODIFICAR una factura, primero usa `list_invoices` para obtener el ID, luego `update_invoice`.
- Para ENVIAR una factura por email, usa `send_invoice_by_email`. Si no conoces el ID, busca primero.
- Para marcar como PAGADA, usa `update_invoice_status` con new_status='paid'.
- Si te faltan datos críticos (cliente, concepto, importe), PREGUNTA al usuario antes de crear.
- Responde siempre en español.
- Si la factura supera 5000€, el sistema pedirá aprobación humana automáticamente.
- Las facturas se crean en estado BORRADOR (draft). El usuario las aprueba desde la UI.
- El IVA por defecto es 21%. Solo cámbialo si el usuario lo especifica.

ID del Tenant actual: {tenant_id}
Fecha de hoy: {today}"""


async def billing_agent_node(state: AgentState):
    """Nodo principal: el LLM razona y elige herramientas."""
    today = date.today().isoformat()

    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=BILLING_SYSTEM_PROMPT.format(
                tenant_id=state.get("tenant_id", ""),
                today=today,
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"billing_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de facturación...",
        status="completed",
        action_taken=(
            "Invocando herramientas de facturación"
            if response.tool_calls
            else "Asistencia de facturación completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def billing_finalize_node(state: AgentState):
    """Cierra el flujo del agente de facturación."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="billing_final",
        description="Agente de Facturación ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Operación de facturación completada."
        ),
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("billing_agent", billing_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", billing_finalize_node)

workflow.set_entry_point("billing_agent")
workflow.add_conditional_edges("billing_agent", tools_condition)
workflow.add_edge("tools", "billing_agent")

graph = workflow.compile()
