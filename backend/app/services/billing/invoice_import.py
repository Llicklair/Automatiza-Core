"""Integración de facturas escaneadas en el ERP.

Toma los borradores YA REVISADOS por el usuario (salidos del OCR
`extract_invoice_data`) y, por cada uno:
  1. resuelve/crea el proveedor (Client con client_type="supplier"),
  2. crea la factura de COMPRA (invoice_type="received", status="draft") + líneas,
  3. genera el asiento contable de compra (create_invoice_journal_entry),
  4. (opcional) suma stock SOLO de las líneas que casan con un producto del
     catálogo por SKU o nombre exacto — no crea productos ni inventa cantidades.

Todo detrás de revisión humana; nada se ejecuta desde el OCR sin confirmar.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import func, select, update

from app.db.models.billing import Invoice, InvoiceLine
from app.db.models.crm import Client
from app.db.models.inventory import Product, StockMovement
from app.services.billing.auto_accounting import create_invoice_journal_entry
from app.services.sales.commands import create_stock_movement

logger = logging.getLogger(__name__)


def _dec(v) -> Decimal:
    try:
        return Decimal(str(v if v is not None else 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)


def _parse_date(s: str | None) -> datetime:
    if not s:
        return datetime.now(UTC)
    try:
        return datetime.combine(date.fromisoformat(s[:10]), datetime.min.time(), tzinfo=UTC)
    except ValueError:
        return datetime.now(UTC)


async def _resolve_supplier(db, tenant_id: UUID, emisor: dict) -> Client:
    """Busca el proveedor por NIF (o nombre) y lo crea si no existe."""
    nif = (emisor.get("nif") or "").strip() or None
    name = (emisor.get("name") or "Proveedor sin nombre").strip()[:200]

    client = None
    if nif:
        res = await db.execute(
            select(Client).where(Client.tenant_id == tenant_id, Client.nif == nif)
        )
        client = res.scalars().first()
    if client is None:
        res = await db.execute(
            select(Client).where(
                Client.tenant_id == tenant_id, func.lower(Client.name) == name.lower()
            )
        )
        client = res.scalars().first()
    if client is None:
        client = Client(
            tenant_id=tenant_id,
            nif=nif,
            name=name,
            client_type="supplier",
            address=(emisor.get("address") or None),
            city=(emisor.get("city") or None),
            postal_code=(emisor.get("postal_code") or None),
        )
        db.add(client)
        await db.flush()
    return client


async def _match_product(db, tenant_id: UUID, description: str) -> Product | None:
    """Casa una línea con un producto del catálogo por SKU o nombre exacto."""
    desc = (description or "").strip()
    if not desc:
        return None
    res = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            (Product.sku == desc) | (func.lower(Product.name) == desc.lower()),
        )
    )
    return res.scalars().first()


async def _stock_ref_exists(db, tenant_id: UUID, reference: str) -> bool:
    res = await db.execute(
        select(StockMovement.id).where(
            StockMovement.tenant_id == tenant_id, StockMovement.reference == reference
        )
    )
    return res.scalar_one_or_none() is not None


async def import_received_invoices(
    db, tenant_id: UUID, drafts: list[dict], user_id: UUID | None = None
) -> list[dict]:
    """Crea N facturas de compra (+asiento, +stock opcional) desde borradores revisados."""
    results: list[dict] = []
    for draft in drafts:
        try:
            results.append(await _import_one(db, tenant_id, draft, user_id))
        except Exception as e:  # noqa: BLE001 — un fallo no debe tumbar el lote
            logger.exception("[INVOICE-IMPORT] Error importando factura")
            results.append({"ok": False, "error": str(e), "invoice_number": draft.get("invoice_number")})
    return results


async def _link_source_document(db, tenant_id: UUID, draft: dict, invoice_id) -> None:
    """Marca el documento origen (si el draft trae `source_document_id`) como
    importado y lo enlaza a la factura creada.

    Deja el documento con `entity_type='invoice'`, `entity_id=<factura>` y
    `status='imported'`. Una asimilación automática puede así saltarse los
    documentos ya procesados (no reimporta) y la UI puede mostrar el vínculo.
    """
    doc_id = draft.get("source_document_id")
    if not doc_id:
        return
    from app.db.models.tenant import TenantDocument

    try:
        await db.execute(
            update(TenantDocument)
            .where(
                TenantDocument.id == doc_id,
                TenantDocument.tenant_id == tenant_id,
            )
            .values(entity_type="invoice", entity_id=invoice_id, status="imported")
        )
    except Exception as e:  # noqa: BLE001 — el enlace es best-effort, no debe tumbar el import
        logger.warning("[INVOICE-IMPORT] no se pudo enlazar el documento %s: %s", doc_id, e)


async def _import_one(db, tenant_id: UUID, draft: dict, user_id: UUID | None) -> dict:
    supplier = await _resolve_supplier(db, tenant_id, draft.get("emisor") or {})

    # Idempotencia: una factura recibida queda identificada por (proveedor,
    # número del proveedor). Si ya existe, NO creamos otra — así reimportar el
    # mismo documento (o una automatización por evento que reescanee la carpeta)
    # no genera duplicados. El número de recibida lo pone el proveedor, por eso
    # la clave es proveedor+número, no solo el número.
    inv_number = (draft.get("invoice_number") or "").strip() or None
    if inv_number:
        dup = await db.execute(
            select(Invoice.id).where(
                Invoice.tenant_id == tenant_id,
                Invoice.client_id == supplier.id,
                Invoice.invoice_number == inv_number,
                Invoice.invoice_type == "received",
            ).limit(1)
        )
        existing_id = dup.scalar_one_or_none()
        if existing_id is not None:
            # Enlazamos el documento origen a la factura ya existente (idempotente)
            # y lo marcamos como importado para que no se reprocese.
            await _link_source_document(db, tenant_id, draft, existing_id)
            await db.commit()
            return {
                "ok": True,
                "skipped": True,
                "duplicate": True,
                "invoice_id": str(existing_id),
                "invoice_number": inv_number,
                "reason": "Ya existía una factura recibida con ese proveedor y número.",
            }

    lines_in = draft.get("lines") or []
    invoice = Invoice(
        tenant_id=tenant_id,
        client_id=supplier.id,
        invoice_number=(draft.get("invoice_number") or None),
        date=_parse_date(draft.get("issue_date")),
        due_date=_parse_date(draft["due_date"]) if draft.get("due_date") else None,
        amount_base=_dec(draft.get("amount_base")),
        tax_amount=_dec(draft.get("tax_amount")),
        amount_total=_dec(draft.get("amount_total")),
        status="draft",
        invoice_type="received",
        notes=(draft.get("notes") or None),
    )
    db.add(invoice)
    await db.flush()

    for ln in lines_in:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                description=(ln.get("description") or "")[:500],
                quantity=_dec(ln.get("quantity") or 1),
                unit_price=_dec(ln.get("unit_price")),
                tax_percentage=_dec(ln.get("tax_percentage") or 21),
                total=_dec(ln.get("total")),
            )
        )
    await db.flush()

    await create_invoice_journal_entry(db, tenant_id, invoice)
    # Enlaza el documento origen (si lo hay) a la factura recién creada y lo
    # marca como importado → idempotencia para reescaneos/automatizaciones.
    await _link_source_document(db, tenant_id, draft, invoice.id)
    await db.commit()
    await db.refresh(invoice)

    stock_applied: list[dict] = []
    stock_unmatched: list[str] = []
    if draft.get("apply_stock"):
        for idx, ln in enumerate(lines_in):
            desc = ln.get("description") or ""
            product = await _match_product(db, tenant_id, desc)
            if product is None:
                stock_unmatched.append(desc[:120])
                continue
            qty = round(float(_dec(ln.get("quantity") or 0)))
            if qty <= 0:
                stock_unmatched.append(desc[:120])
                continue
            reference = f"INVOICE:{invoice.id}:{idx}"
            if await _stock_ref_exists(db, tenant_id, reference):
                continue  # idempotente: ya aplicado
            await create_stock_movement(
                db,
                tenant_id,
                product.id,
                {
                    "movement_type": "entrada",
                    "quantity": qty,
                    "unit_cost": float(_dec(ln.get("unit_price"))),
                    "reference": reference,
                    "notes": f"Factura compra {invoice.invoice_number or invoice.id}",
                    "user_id": user_id,
                },
            )
            stock_applied.append({"product": product.name, "sku": product.sku, "quantity": qty})

    return {
        "ok": True,
        "invoice_id": str(invoice.id),
        "invoice_number": invoice.invoice_number,
        "supplier": supplier.name,
        "amount_total": float(invoice.amount_total),
        "stock_applied": stock_applied,
        "stock_unmatched": stock_unmatched,
    }
