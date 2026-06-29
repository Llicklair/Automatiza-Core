"""Sales domain â€” write commands (CQRS-lite).

All functions here perform INSERT / UPDATE / DELETE operations.
Read-only helpers are imported from queries.py where needed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from datetime import date as date_type
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.core.datetime_utils import local_today
from app.core.exceptions import ConflictError
from app.db.models.billing import DeliveryNote, DeliveryNoteLine
from app.db.models.models import (
    Client,
    Invoice,
    InvoiceLine,
    Product,
    PurchaseOrder,
    PurchaseOrderLine,
    Quote,
    QuoteLine,
    SalesOrder,
    SalesOrderLine,
    StockMovement,
)
from app.services._tenant_guard import assert_fk_in_tenant
from app.services.sales.queries import _get_quote_or_raise, _quote_query_with_rels

logger = logging.getLogger(__name__)

VALID_STATUSES = ("draft", "confirmed", "delivered")

# ---------------------------------------------------------------------------
# client commands
# ---------------------------------------------------------------------------


async def create_client(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID,
    data: dict,
) -> Client:
    new_client = Client(tenant_id=tenant_id, **data)
    db.add(new_client)
    try:
        await db.commit()
        await db.refresh(new_client)
    except IntegrityError as exc:
        await db.rollback()
        raise ValueError("Ya existe un cliente con ese NIF o email") from exc
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error guardando cliente: %s", e)
        raise RuntimeError("Error al guardar el cliente") from e

    try:
        from app.services.event_bus import emit_event

        await emit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_name="client_created",
            context={
                "client_id": str(new_client.id),
                "client_name": new_client.name,
                "nif": new_client.nif,
            },
        )
    except Exception:
        logger.warning("emit_event client_created falló â€” no es crítico")

    return new_client


async def update_client(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    data: dict,
) -> Client:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise LookupError("Cliente no encontrado")
    for key, value in data.items():
        setattr(client, key, value)
    try:
        await db.commit()
        await db.refresh(client)
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error actualizando cliente %s: %s", client_id, e)
        raise RuntimeError("Error al actualizar el cliente") from e
    return client


async def delete_client(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
) -> None:
    result = await db.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    client = result.scalar_one_or_none()
    if not client:
        raise LookupError("Cliente no encontrado")
    try:
        await db.delete(client)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "No se puede eliminar el cliente porque tiene facturas o pedidos asociados"
        ) from None
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Error eliminando cliente %s: %s", client_id, e)
        raise RuntimeError("Error al eliminar el cliente") from e


# ---------------------------------------------------------------------------
# product commands
# ---------------------------------------------------------------------------


async def create_product(db: AsyncSession, tenant_id: UUID, data: dict) -> Product:
    product = Product(tenant_id=tenant_id, **data)
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(
    db: AsyncSession, tenant_id: UUID, product_id: UUID, data: dict
) -> Product:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")
    for key, value in data.items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, tenant_id: UUID, product_id: UUID) -> None:
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")
    await db.delete(product)
    await db.commit()


async def create_stock_movement(
    db: AsyncSession, tenant_id: UUID, product_id: UUID, data: dict
) -> StockMovement:
    # Row-level FOR UPDATE serializes concurrent stock movements of the same
    # product at the DB; products locked in sorted order to avoid deadlock.
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.tenant_id == tenant_id)
        .with_for_update()
    )
    product = result.scalar_one_or_none()
    if not product:
        raise LookupError("Producto no encontrado")

    movement_type = data["movement_type"]
    quantity = data["quantity"]
    # "unit" (unidades) | "box" (cajas). Las cajas son un contador independiente
    # (`product.stock_boxes`) que NO pasa por FEFO/lotes/ProductStock (unit-only).
    stock_kind = data.get("stock_kind", "unit")

    if stock_kind == "box":
        current = int(product.stock_boxes)
        if movement_type == "entrada":
            new_stock = current + abs(quantity)
        elif movement_type == "salida":
            new_stock = current - abs(quantity)
            if new_stock < 0:
                raise ValueError("Stock de cajas insuficiente")
        else:  # ajuste
            new_stock = quantity
        product.stock_boxes = new_stock
    else:
        if movement_type == "entrada":
            new_stock = int(product.stock_quantity) + abs(quantity)
        elif movement_type == "salida":
            new_stock = int(product.stock_quantity) - abs(quantity)
            if new_stock < 0:
                raise ValueError("Stock insuficiente")
        else:  # ajuste
            new_stock = quantity
        product.stock_quantity = new_stock

        # Si el producto gestiona lotes, una salida los descuenta en orden FEFO.
        if movement_type == "salida":
            from app.services.inventory import lot_service

            if await lot_service.has_lots(db, product_id):
                await lot_service.deduct_fefo(db, product_id=product_id, quantity=abs(quantity))

    movement = StockMovement(
        tenant_id=tenant_id,
        product_id=product_id,
        user_id=data.get("user_id"),
        movement_type=movement_type,
        stock_kind=stock_kind,
        reason=data.get("reason"),
        quantity=quantity,
        stock_after=new_stock,
        unit_cost=data.get("unit_cost"),
        reference=data.get("reference"),
        notes=data.get("notes"),
    )
    db.add(movement)
    await db.commit()
    await db.refresh(movement)
    return movement


# ---------------------------------------------------------------------------
# quote commands
# ---------------------------------------------------------------------------


async def create_quote(db: AsyncSession, tenant_id: UUID, data: dict) -> Quote:
    lines_data = data.pop("lines", [])

    amount_base = 0.0
    tax_amount = 0.0
    for ln in lines_data:
        line_base = ln["quantity"] * ln["unit_price"]
        line_tax = line_base * (ln["tax_percentage"] / 100)
        amount_base += line_base
        tax_amount += line_tax

    data.pop("amount_base", None)
    data.pop("tax_amount", None)
    data.pop("amount_total", None)

    await assert_fk_in_tenant(db, Client, data.get("client_id"), tenant_id, "Client")
    db_quote = Quote(
        tenant_id=tenant_id,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_base + tax_amount,
        **data,
    )
    db.add(db_quote)
    await db.flush()

    for ln in lines_data:
        line_base = ln["quantity"] * ln["unit_price"]
        db.add(
            QuoteLine(
                quote_id=db_quote.id,
                product_id=ln.get("product_id"),
                description=ln.get("description"),
                quantity=ln["quantity"],
                unit_price=ln["unit_price"],
                tax_percentage=ln["tax_percentage"],
                total_line=line_base,
            )
        )

    await db.commit()

    result = await db.execute(_quote_query_with_rels().where(Quote.id == db_quote.id))
    return result.scalar_one()


async def update_quote(
    db: AsyncSession,
    quote_id: UUID,
    tenant_id: UUID,
    update_data: dict,
) -> Quote:
    quote = await _get_quote_or_raise(db, quote_id, tenant_id)
    if "client_id" in update_data:
        await assert_fk_in_tenant(db, Client, update_data.get("client_id"), tenant_id, "Client")
    for field, value in update_data.items():
        setattr(quote, field, value)
    await db.commit()
    result = await db.execute(
        _quote_query_with_rels().where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    return result.scalar_one()


async def delete_quote(db: AsyncSession, quote_id: UUID, tenant_id: UUID) -> None:
    result = await db.execute(
        select(Quote).where(Quote.id == quote_id, Quote.tenant_id == tenant_id)
    )
    quote = result.scalar_one_or_none()
    if not quote:
        raise LookupError("Quote not found")
    try:
        await db.delete(quote)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "No se puede eliminar el presupuesto porque tiene registros asociados"
        ) from None


async def convert_to_invoice(
    db: AsyncSession,
    quote_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
) -> dict:
    quote = await _get_quote_or_raise(db, quote_id, tenant_id)

    if quote.status == "accepted":
        raise ValueError("Este presupuesto ya fue convertido en factura")

    count_res = await db.execute(
        select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id)
    )
    invoice_count = (count_res.scalar() or 0) + 1
    now = datetime.now(UTC)
    invoice_number = f"FAC-{now.year}-{invoice_count:04d}"

    new_invoice = Invoice(
        tenant_id=tenant_id,
        client_id=quote.client_id,
        invoice_number=invoice_number,
        date=now,
        amount_base=float(quote.amount_base or 0),
        tax_amount=float(quote.tax_amount or 0),
        amount_total=float(quote.amount_total or 0),
        notes=quote.notes,
        status="draft",
        invoice_type="issued",
    )
    db.add(new_invoice)
    await db.flush()

    for ql in quote.lines or []:
        line_base = float(ql.quantity or 1) * float(ql.unit_price or 0)
        line_tax = line_base * (float(ql.tax_percentage or 21) / 100)
        db.add(
            InvoiceLine(
                invoice_id=new_invoice.id,
                product_id=ql.product_id,
                description=ql.description,
                quantity=float(ql.quantity or 1),
                unit_price=float(ql.unit_price or 0),
                tax_percentage=float(ql.tax_percentage or 21),
                discount_percentage=0.0,
                total=line_base + line_tax,
            )
        )

    quote.status = "accepted"
    await db.commit()

    try:
        from app.services.event_bus import emit_event

        await emit_event(
            db=db,
            tenant_id=tenant_id,
            user_id=user_id,
            event_name="invoice_created",
            context={
                "invoice_id": str(new_invoice.id),
                "invoice_number": invoice_number,
                "amount_total": float(new_invoice.amount_total),
                "source": "quote_conversion",
                "quote_id": str(quote_id),
                "client_name": quote.client.name if quote.client else None,
            },
        )
    except Exception as e:
        logger.warning(
            "Error al emitir evento invoice_created tras conversion de presupuesto %s: %s",
            quote_id,
            e,
        )

    return {
        "invoice_id": str(new_invoice.id),
        "invoice_number": invoice_number,
        "amount_total": float(new_invoice.amount_total),
        "message": f"Presupuesto convertido en factura {invoice_number} correctamente.",
    }


# ---------------------------------------------------------------------------
# albaran commands
# ---------------------------------------------------------------------------


async def _next_albaran_number(tenant_id: UUID, db: AsyncSession) -> str:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.tenant_id == tenant_id)
        .order_by(desc(DeliveryNote.created_at))
        .limit(1)
    )
    last = result.scalar_one_or_none()
    if last and last.albaran_number:
        try:
            num = int(last.albaran_number.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"ALB-{num:05d}"


async def create_albaran(
    tenant_id: UUID,
    client_id: UUID | None,
    entry_date: date_type | None,
    notes: str | None,
    lines: list,
    db: AsyncSession,
) -> DeliveryNote:
    albaran_number = await _next_albaran_number(tenant_id, db)
    resolved_date = entry_date or local_today()

    amount_base = Decimal("0")
    tax_amount = Decimal("0")
    for line in lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        tax = base * Decimal(str(line.tax_percentage)) / Decimal("100")
        amount_base += base
        tax_amount += tax
    amount_total = amount_base + tax_amount

    await assert_fk_in_tenant(db, Client, client_id, tenant_id, "Client")
    note = DeliveryNote(
        tenant_id=tenant_id,
        client_id=client_id,
        albaran_number=albaran_number,
        date=resolved_date,
        notes=notes,
        amount_base=amount_base,
        tax_amount=tax_amount,
        amount_total=amount_total,
    )
    db.add(note)
    await db.flush()

    for line in lines:
        base = Decimal(str(line.quantity)) * Decimal(str(line.unit_price))
        total = base + base * Decimal(str(line.tax_percentage)) / Decimal("100")
        db.add(
            DeliveryNoteLine(
                albaran_id=note.id,
                product_id=line.product_id,
                description=line.description,
                quantity=line.quantity,
                unit_price=line.unit_price,
                tax_percentage=line.tax_percentage,
                total=total,
            )
        )

    await db.commit()
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == note.id)
        .options(selectinload(DeliveryNote.lines))
    )
    return result.scalar_one()


def _albaran_stock_reference(albaran_id: UUID) -> str:
    """Reference string used on StockMovement to mark deductions made by an
    albarán confirmation. Used for idempotency lookup."""
    return f"DELIVERY_NOTE:{albaran_id}"


def _albaran_stock_reverse_reference(albaran_id: UUID) -> str:
    """Reference string for the compensating StockMovement(entrada) generated
    when an albarán is downgraded from confirmed/delivered back to draft, or
    deleted while in confirmed/delivered state."""
    return f"DELIVERY_NOTE_REVERSED:{albaran_id}"


async def _deduct_stock_for_albaran(
    db: AsyncSession, note: DeliveryNote, user_id: UUID | None
) -> None:
    """Generate StockMovement(salida) rows for each line with a product_id.

    Idempotent: if any movement with reference=DELIVERY_NOTE:<id> already
    exists, this is a no-op. Raises ValueError if stock is insufficient.
    Does NOT commit — the caller controls the transaction.
    """
    reference = _albaran_stock_reference(note.id)
    existing = await db.execute(
        select(StockMovement.id)
        .where(
            StockMovement.tenant_id == note.tenant_id,
            StockMovement.reference == reference,
        )
        .limit(1)
    )
    if existing.scalar_one_or_none():
        return

    # Sort lines by product_id (deterministic lock order) to prevent deadlocks
    # when two concurrent transactions lock multiple products simultaneously.
    sorted_lines = sorted(
        (ln for ln in note.lines if ln.product_id is not None),
        key=lambda ln: ln.product_id,
    )
    for line in sorted_lines:
        qty = int(line.quantity or 0)
        if qty <= 0:
            continue
        # Row-level FOR UPDATE serializes concurrent stock deductions of the same
        # product at the DB; products locked in sorted order to avoid deadlock.
        product_res = await db.execute(
            select(Product)
            .where(
                Product.id == line.product_id,
                Product.tenant_id == note.tenant_id,
            )
            .with_for_update()
        )
        product = product_res.scalar_one_or_none()
        if product is None:
            continue
        new_stock = int(product.stock_quantity) - qty
        if new_stock < 0:
            raise ValueError(
                f"Stock insuficiente para '{product.name}' "
                f"(disponible {product.stock_quantity}, solicitado {qty})"
            )
        product.stock_quantity = new_stock
        from app.services.inventory import lot_service

        if await lot_service.has_lots(db, product.id):
            await lot_service.deduct_fefo(db, product_id=product.id, quantity=qty)
        db.add(
            StockMovement(
                tenant_id=note.tenant_id,
                product_id=product.id,
                user_id=user_id,
                movement_type="salida",
                quantity=qty,
                stock_after=new_stock,
                unit_cost=product.cost_price,
                reference=reference,
                notes=f"Albarán {note.albaran_number}",
            )
        )


async def _revert_stock_for_albaran(
    db: AsyncSession, note: DeliveryNote, user_id: UUID | None
) -> None:
    """Generate StockMovement(entrada) rows to compensate a prior deduction.

    Mirror of `_deduct_stock_for_albaran`: sums back the quantities that were
    subtracted when the albarán was confirmed. Idempotent: if a movement with
    `reference=DELIVERY_NOTE_REVERSED:<id>` already exists, this is a no-op.

    Only acts on lines whose original deduction is recorded (i.e. the albarán
    actually had a DELIVERY_NOTE:<id> StockMovement). If no original deduction
    is found, returns silently — nothing to revert.

    Does NOT commit — the caller controls the transaction.
    """
    forward_reference = _albaran_stock_reference(note.id)
    reverse_reference = _albaran_stock_reverse_reference(note.id)

    # Idempotency: bail if reversed already.
    already_reversed = await db.execute(
        select(StockMovement.id)
        .where(
            StockMovement.tenant_id == note.tenant_id,
            StockMovement.reference == reverse_reference,
        )
        .limit(1)
    )
    if already_reversed.scalar_one_or_none():
        return

    # Sanity check: must have a forward deduction before reverting.
    forward = await db.execute(
        select(StockMovement.id)
        .where(
            StockMovement.tenant_id == note.tenant_id,
            StockMovement.reference == forward_reference,
        )
        .limit(1)
    )
    if not forward.scalar_one_or_none():
        return

    # Sort lines by product_id (deterministic lock order) to prevent deadlocks
    # when two concurrent transactions lock multiple products simultaneously.
    sorted_lines = sorted(
        (ln for ln in note.lines if ln.product_id is not None),
        key=lambda ln: ln.product_id,
    )
    for line in sorted_lines:
        qty = int(line.quantity or 0)
        if qty <= 0:
            continue
        # Row-level FOR UPDATE serializes concurrent stock reverts of the same
        # product at the DB; products locked in sorted order to avoid deadlock.
        product_res = await db.execute(
            select(Product)
            .where(
                Product.id == line.product_id,
                Product.tenant_id == note.tenant_id,
            )
            .with_for_update()
        )
        product = product_res.scalar_one_or_none()
        if product is None:
            continue
        new_stock = int(product.stock_quantity) + qty
        product.stock_quantity = new_stock
        db.add(
            StockMovement(
                tenant_id=note.tenant_id,
                product_id=product.id,
                user_id=user_id,
                movement_type="entrada",
                quantity=qty,
                stock_after=new_stock,
                unit_cost=product.cost_price,
                reference=reverse_reference,
                notes=f"Reversa albarán {note.albaran_number}",
            )
        )


async def update_albaran_status(
    albaran_id: UUID,
    tenant_id: UUID,
    new_status: str,
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
) -> DeliveryNote:
    if new_status not in VALID_STATUSES:
        raise ValueError("Estado no valido")
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise LookupError("Albaran no encontrado")

    old_status = note.status
    note.status = new_status

    if new_status == "confirmed" and old_status != "confirmed":
        # Status sube a confirmed → descontar stock (idempotente).
        await _deduct_stock_for_albaran(db, note, user_id)
    elif old_status in ("confirmed", "delivered") and new_status == "draft":
        # Status baja a draft tras haber confirmado → revertir stock con
        # movimiento entrada compensatorio (idempotente).
        await _revert_stock_for_albaran(db, note, user_id)

    await db.commit()
    await db.refresh(note)
    return note


async def delete_albaran(
    albaran_id: UUID, tenant_id: UUID, db: AsyncSession, *, user_id: UUID | None = None
) -> None:
    result = await db.execute(
        select(DeliveryNote)
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id)
        .options(selectinload(DeliveryNote.lines))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise LookupError("Albaran no encontrado")
    # Si el albarán había confirmado stock, generar el movimiento de entrada
    # compensatorio antes de borrar para no dejar negative stock.
    if note.status in ("confirmed", "delivered"):
        await _revert_stock_for_albaran(db, note, user_id)
    await db.delete(note)
    await db.commit()


# ---------------------------------------------------------------------------
# purchase_order commands
# ---------------------------------------------------------------------------


async def create_purchase_order(
    db: AsyncSession, tenant_id: UUID, data: dict, lines_data: list[dict]
) -> PurchaseOrder:
    order_number = data.pop("order_number", None) or f"PC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    amount_base = 0.0
    tax_amount = 0.0
    for line in lines_data:
        base = float(line["quantity"]) * float(line["unit_price"])
        tax = base * (float(line["tax_percentage"]) / 100)
        amount_base += base
        tax_amount += tax

    order = PurchaseOrder(
        tenant_id=tenant_id,
        order_number=order_number,
        date=data.pop("date", None) or datetime.now(UTC),
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
        **data,
    )
    db.add(order)
    await db.flush()

    for ld in lines_data:
        base = float(ld["quantity"]) * float(ld["unit_price"])
        tax = base * (float(ld["tax_percentage"]) / 100)
        line = PurchaseOrderLine(
            order_id=order.id,
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=ld["quantity"],
            unit_price=ld["unit_price"],
            tax_percentage=ld["tax_percentage"],
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order.id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


async def update_purchase_order(
    db: AsyncSession, tenant_id: UUID, order_id: UUID, data: dict
) -> PurchaseOrder:
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido de compra no encontrado")
    for field, value in data.items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == order_id)
        .options(joinedload(PurchaseOrder.supplier), joinedload(PurchaseOrder.lines))
    )
    return result.unique().scalar_one()


async def delete_purchase_order(db: AsyncSession, tenant_id: UUID, order_id: UUID) -> None:
    result = await db.execute(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id, PurchaseOrder.tenant_id == tenant_id
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido de compra no encontrado")
    try:
        await db.delete(order)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "No se puede eliminar el pedido de compra porque tiene registros asociados"
        ) from None


# ---------------------------------------------------------------------------
# sales_order commands
# ---------------------------------------------------------------------------


async def create_sales_order(
    db: AsyncSession, tenant_id: UUID, data: dict, lines_data: list[dict]
) -> SalesOrder:
    order_number = (
        data.pop("order_number", None) or f"PED-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    )

    amount_base = 0.0
    tax_amount = 0.0
    for line in lines_data:
        base = line["quantity"] * line["unit_price"] * (1 - line["discount_percentage"] / 100)
        tax = base * (line["tax_percentage"] / 100)
        amount_base += base
        tax_amount += tax

    order = SalesOrder(
        tenant_id=tenant_id,
        order_number=order_number,
        date=data.pop("date", None) or datetime.now(UTC),
        amount_base=round(amount_base, 2),
        tax_amount=round(tax_amount, 2),
        amount_total=round(amount_base + tax_amount, 2),
        **data,
    )
    db.add(order)
    await db.flush()

    for ld in lines_data:
        base = ld["quantity"] * ld["unit_price"] * (1 - ld["discount_percentage"] / 100)
        tax = base * (ld["tax_percentage"] / 100)
        line = SalesOrderLine(
            order_id=order.id,
            product_id=ld.get("product_id"),
            description=ld["description"],
            quantity=ld["quantity"],
            unit_price=ld["unit_price"],
            discount_percentage=ld["discount_percentage"],
            tax_percentage=ld["tax_percentage"],
            total=round(base + tax, 2),
        )
        db.add(line)

    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order.id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


async def update_sales_order(
    db: AsyncSession, tenant_id: UUID, order_id: UUID, data: dict
) -> SalesOrder:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido no encontrado")
    for field, value in data.items():
        setattr(order, field, value)
    await db.commit()
    result = await db.execute(
        select(SalesOrder)
        .where(SalesOrder.id == order_id)
        .options(joinedload(SalesOrder.client), joinedload(SalesOrder.lines))
    )
    return result.unique().scalar_one()


async def delete_sales_order(db: AsyncSession, tenant_id: UUID, order_id: UUID) -> None:
    result = await db.execute(
        select(SalesOrder).where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise LookupError("Pedido no encontrado")
    try:
        await db.delete(order)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(
            "No se puede eliminar el pedido porque tiene registros asociados"
        ) from None
