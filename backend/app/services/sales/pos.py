"""TPV (Punto de Venta) — servicio.

Reglas clave:
- Una sesión `open` por (tenant_id, user_id) — garantizado por índice
  único parcial en BD. `open_session` lanza ValueError si ya hay otra.
- `add_line` resuelve datos del producto si product_id existe; permite
  líneas libres (sin product_id) para "varios" / "extras".
- `checkout` es atómico: descuenta stock con StockMovement
  (reference=POS_SESSION:<id>), bloquea HTTP 400 si stock insuficiente,
  calcula totales y cierra la sesión. No commitea hasta el final.
- Cancelar elimina la sesión y sus líneas (sin tocar stock — no se
  habían descontado todavía).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.inventory import Product, StockMovement
from app.db.models.pos import PosSession, PosSessionLine

logger = logging.getLogger(__name__)


def _pos_stock_reference(session_id: UUID) -> str:
    return f"POS_SESSION:{session_id}"


async def _get_open_session(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> PosSession | None:
    result = await db.execute(
        select(PosSession)
        .where(
            PosSession.tenant_id == tenant_id,
            PosSession.user_id == user_id,
            PosSession.status == "open",
        )
        .options(selectinload(PosSession.lines))
    )
    return result.scalar_one_or_none()


async def _get_session_for_user(db: AsyncSession, tenant_id: UUID, session_id: UUID) -> PosSession:
    result = await db.execute(
        select(PosSession)
        .where(PosSession.id == session_id, PosSession.tenant_id == tenant_id)
        .options(selectinload(PosSession.lines))
    )
    session = result.scalar_one_or_none()
    if not session:
        raise LookupError("Sesión TPV no encontrada")
    return session


def _line_total(quantity: int, unit_price: Decimal, tax_pct: Decimal) -> Decimal:
    base = Decimal(quantity) * Decimal(unit_price)
    return (base + base * Decimal(tax_pct) / Decimal("100")).quantize(Decimal("0.01"))


async def get_current_session(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> PosSession | None:
    """Devuelve la sesión 'open' del usuario o None."""
    return await _get_open_session(db, tenant_id, user_id)


async def open_session(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> PosSession:
    """Abre una nueva sesión. Falla si el cajero ya tiene una abierta."""
    existing = await _get_open_session(db, tenant_id, user_id)
    if existing:
        raise ValueError("Ya existe una sesión TPV abierta para este usuario")
    session = PosSession(tenant_id=tenant_id, user_id=user_id, status="open")
    db.add(session)
    await db.commit()
    await db.refresh(session)
    # Asegurar relación cargada para serialización
    await db.refresh(session, ["lines"])
    return session


async def _reload_with_lines(db: AsyncSession, tenant_id: UUID, session_id: UUID) -> PosSession:
    """Refresca el cache de la session de SQLAlchemy y devuelve la
    sesión con lines actualizadas. expire_all() asegura que el siguiente
    select vea los cambios committeados, no objetos en cache stale."""
    db.expire_all()
    return await _get_session_for_user(db, tenant_id, session_id)


async def add_line(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: UUID,
    data: dict,
) -> PosSession:
    """Añade una línea al carrito. Si product_id viene, completa datos
    desde el producto. Devuelve la sesión completa actualizada."""
    session = await _get_session_for_user(db, tenant_id, session_id)
    if session.status != "open":
        raise ValueError("La sesión no está abierta")

    product_id = data.get("product_id")
    description = data.get("description")
    unit_price = data.get("unit_price")
    tax_percentage = data.get("tax_percentage")
    quantity = int(data.get("quantity") or 1)
    if quantity <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")

    if product_id:
        prod_res = await db.execute(select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id))
        product = prod_res.scalar_one_or_none()
        if not product:
            raise LookupError("Producto no encontrado")
        description = description or product.name
        unit_price = float(product.price) if unit_price is None else unit_price
        tax_percentage = float(product.tax_percentage) if tax_percentage is None else tax_percentage
    else:
        if not description:
            raise ValueError("description es obligatorio sin product_id")
        unit_price = unit_price if unit_price is not None else 0
        tax_percentage = tax_percentage if tax_percentage is not None else 21

    total = _line_total(quantity, Decimal(str(unit_price)), Decimal(str(tax_percentage)))
    line = PosSessionLine(
        session_id=session.id,
        tenant_id=tenant_id,
        product_id=product_id,
        description=description,
        quantity=quantity,
        unit_price=Decimal(str(unit_price)),
        tax_percentage=Decimal(str(tax_percentage)),
        total=total,
    )
    db.add(line)
    await db.commit()
    return await _reload_with_lines(db, tenant_id, session_id)


async def update_line_quantity(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: UUID,
    line_id: UUID,
    quantity: int,
) -> PosSession:
    session = await _get_session_for_user(db, tenant_id, session_id)
    if session.status != "open":
        raise ValueError("La sesión no está abierta")
    if quantity <= 0:
        raise ValueError("La cantidad debe ser mayor que cero")

    line = next((ln for ln in session.lines if ln.id == line_id), None)
    if not line:
        raise LookupError("Línea no encontrada")
    line.quantity = quantity
    line.total = _line_total(quantity, line.unit_price, line.tax_percentage)
    await db.commit()
    return await _reload_with_lines(db, tenant_id, session_id)


async def remove_line(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: UUID,
    line_id: UUID,
) -> PosSession:
    session = await _get_session_for_user(db, tenant_id, session_id)
    if session.status != "open":
        raise ValueError("La sesión no está abierta")
    line = next((ln for ln in session.lines if ln.id == line_id), None)
    if not line:
        raise LookupError("Línea no encontrada")
    await db.delete(line)
    await db.commit()
    return await _reload_with_lines(db, tenant_id, session_id)


async def checkout(
    db: AsyncSession,
    tenant_id: UUID,
    session_id: UUID,
    user_id: UUID,
    payment_method: str,
    notes: str | None = None,
) -> PosSession:
    """Cierra la sesión: descuenta stock, calcula totales, guarda método.

    Atómico: si algún producto no tiene stock suficiente, NADA se aplica
    (raise ValueError → HTTP 400 desde el route).

    Re-submit SECUENCIAL (doble-click/retry): lo frena el guard de estado
    (`status != "open" → ValueError`), así que no se duplica venta ni stock.
    `reference=POS_SESSION:<id>` en los StockMovement es solo trazabilidad —
    NO hay UNIQUE sobre él, así que NO es un guard de idempotencia. La race
    SIMULTÁNEA (dos requests en la misma ventana de commit, sin SELECT FOR
    UPDATE) sigue pendiente → ver inbox (sobreventa/concurrencia).
    """
    session = await _get_session_for_user(db, tenant_id, session_id)
    if session.status != "open":
        raise ValueError("La sesión no está abierta o ya fue cerrada")
    if not session.lines:
        raise ValueError("No se puede cerrar una sesión vacía")

    reference = _pos_stock_reference(session.id)

    # Calcular totales y aplicar descuentos de stock atómicamente.
    subtotal = Decimal("0")
    tax_total = Decimal("0")

    for line in session.lines:
        line_base = Decimal(line.quantity) * Decimal(line.unit_price)
        line_tax = line_base * Decimal(line.tax_percentage) / Decimal("100")
        subtotal += line_base
        tax_total += line_tax

        if line.product_id is None:
            continue
        prod_res = await db.execute(
            select(Product).where(Product.id == line.product_id, Product.tenant_id == tenant_id)
        )
        product = prod_res.scalar_one_or_none()
        if product is None:
            continue
        new_stock = int(product.stock_quantity) - int(line.quantity)
        if new_stock < 0:
            raise ValueError(
                f"Stock insuficiente para '{product.name}' "
                f"(disponible {product.stock_quantity}, solicitado {line.quantity})"
            )
        product.stock_quantity = new_stock
        from app.services.inventory import lot_service

        if await lot_service.has_lots(db, product.id):
            await lot_service.deduct_fefo(db, product_id=product.id, quantity=int(line.quantity))
        db.add(
            StockMovement(
                tenant_id=tenant_id,
                product_id=product.id,
                user_id=user_id,
                movement_type="salida",
                quantity=int(line.quantity),
                stock_after=new_stock,
                unit_cost=product.cost_price,
                reference=reference,
                notes=f"Venta TPV sesión {session.id}",
            )
        )

    session.amount_subtotal = subtotal.quantize(Decimal("0.01"))
    session.tax_amount = tax_total.quantize(Decimal("0.01"))
    session.amount_total = (subtotal + tax_total).quantize(Decimal("0.01"))
    session.payment_method = payment_method
    session.status = "closed"
    if notes:
        session.notes = notes
    from datetime import UTC, datetime

    session.closed_at = datetime.now(UTC)

    await db.commit()
    return await _reload_with_lines(db, tenant_id, session_id)


WALK_IN_CLIENT_NAME = "Consumidor final (TPV)"


async def _get_or_create_walk_in_client(db: AsyncSession, tenant_id: UUID):
    """Cliente genérico de mostrador del tenant para tickets simplificados (F2).

    Un ticket F2 no tiene destinatario identificado (el registro VeriFactu no lo
    incluye). Este cliente solo satisface la FK NOT NULL de Invoice y agrupa las
    ventas de mostrador; sin NIF (consumidor final). Idempotente por nombre.
    """
    from app.db.models.crm import Client

    res = await db.execute(select(Client).where(Client.tenant_id == tenant_id, Client.name == WALK_IN_CLIENT_NAME))
    client = res.scalars().first()
    if client is not None:
        return client
    client = Client(tenant_id=tenant_id, name=WALK_IN_CLIENT_NAME, nif=None)
    db.add(client)
    await db.flush()
    return client


async def generar_factura_simplificada(db: AsyncSession, tenant_id: UUID, session_id: UUID):
    """Emite la factura simplificada (F2) de una sesión de TPV cerrada.

    Puente "fase 2" POS→facturación: crea una Invoice simplificada (is_simplified,
    tipo "issued", ya cobrada) con las líneas de la sesión, encadena su registro
    VeriFactu (TipoFactura F2 en modo voluntary) y enlaza la sesión. Idempotente:
    si la sesión ya está facturada devuelve esa factura. Un único commit atómico.
    """
    from datetime import UTC, datetime

    from app.db.models.billing import Invoice, InvoiceLine
    from app.services.billing.numbering import next_invoice_number
    from app.services.billing.verifactu_chain import maybe_append_verifactu_record

    res = await db.execute(
        select(PosSession)
        .options(selectinload(PosSession.lines))
        .where(PosSession.id == session_id, PosSession.tenant_id == tenant_id)
    )
    session = res.scalar_one_or_none()
    if session is None:
        raise ValueError("Sesión de TPV no encontrada.")
    if session.status != "closed":
        raise ValueError("Solo se factura una sesión de TPV cerrada.")

    async def _load_invoice(invoice_id):
        r = await db.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines), selectinload(Invoice.client))
            .where(Invoice.id == invoice_id)
        )
        return r.scalar_one()

    # Idempotencia: una sesión se factura una sola vez.
    if session.invoice_id is not None:
        return await _load_invoice(session.invoice_id)

    client = await _get_or_create_walk_in_client(db, tenant_id)
    invoice_number = await next_invoice_number(db, tenant_id, series="T")

    invoice = Invoice(
        tenant_id=tenant_id,
        client_id=client.id,
        invoice_number=invoice_number,
        date=datetime.now(UTC),
        amount_base=session.amount_subtotal,
        tax_amount=session.tax_amount,
        amount_total=session.amount_total,
        status="paid",
        invoice_type="issued",
        is_simplified=True,
        notes=f"Ticket TPV sesión {session.id}",
    )
    db.add(invoice)
    await db.flush()

    for ln in session.lines:
        db.add(
            InvoiceLine(
                invoice_id=invoice.id,
                product_id=ln.product_id,
                description=ln.description,
                quantity=ln.quantity,
                unit_price=ln.unit_price,
                tax_percentage=ln.tax_percentage,
                total=ln.total,
            )
        )

    # VeriFactu: el ticket se expide en el acto → encadena el registro F2 antes del
    # commit (atómico con la factura). En modo no_remission es un no-op.
    await maybe_append_verifactu_record(db, invoice=invoice)

    session.invoice_id = invoice.id
    await db.commit()
    return await _load_invoice(invoice.id)


async def cancel_session(db: AsyncSession, tenant_id: UUID, session_id: UUID) -> PosSession:
    session = await _get_session_for_user(db, tenant_id, session_id)
    if session.status != "open":
        raise ValueError("Solo se pueden cancelar sesiones abiertas")
    session.status = "cancelled"
    from datetime import UTC, datetime

    session.closed_at = datetime.now(UTC)
    await db.commit()
    return await _reload_with_lines(db, tenant_id, session_id)


async def list_sessions(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    user_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[PosSession]:
    query = select(PosSession).where(PosSession.tenant_id == tenant_id)
    if user_id:
        query = query.where(PosSession.user_id == user_id)
    if status:
        query = query.where(PosSession.status == status)
    query = query.order_by(desc(PosSession.opened_at)).options(selectinload(PosSession.lines)).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
