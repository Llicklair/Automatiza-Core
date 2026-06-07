"""Business logic for the Scanner module.

Raises Python exceptions (ValueError, LookupError), never HTTPException.
"""

import logging
from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import DeliveryNote
from app.db.models.inventory import Product, StockMovement
from app.services.inventory import lot_service

logger = logging.getLogger(__name__)


async def _find_product_by_code(db: AsyncSession, tenant_id: UUID, code: str) -> Product | None:
    """Find a product matching `code` against barcode first, then SKU.

    Lookups are tenant-scoped. The barcode match takes precedence because
    physical scanners emit EAN/UPC codes, which is the more specific identifier.
    """
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            or_(Product.barcode == code, Product.sku == code),
        )
    )
    products = list(result.scalars().all())
    if not products:
        return None
    # Prefer barcode match if multiple products share the same string across columns.
    for p in products:
        if p.barcode == code:
            return p
    return products[0]


async def scan_product(db: AsyncSession, tenant_id: UUID, code: str) -> dict:
    """Look up a product by barcode or SKU and return info + stock."""
    product = await _find_product_by_code(db, tenant_id, code)
    if not product:
        raise LookupError(f"Producto con código '{code}' no encontrado")

    return {
        "id": str(product.id),
        "sku": product.sku,
        "barcode": product.barcode,
        "name": product.name,
        "description": product.description,
        "price": float(product.price) if product.price else None,
        "stock_quantity": float(product.stock_quantity) if product.stock_quantity else 0,
        "stock_min_alert": float(product.stock_min_alert) if product.stock_min_alert else None,
        "low_stock": (
            product.stock_min_alert is not None
            and product.stock_quantity is not None
            and product.stock_quantity <= product.stock_min_alert
        ),
        "lots": await lot_service.lot_summary(db, product.id),
    }


async def record_movement(
    db: AsyncSession,
    tenant_id: UUID,
    code: str,
    quantity: float,
    notes: str,
    movement_type: str,
    device: str,
    lot_number: str | None = None,
    expiry_date: date | None = None,
    cost_price: float | None = None,
) -> dict:
    """Record a stock movement (entrada/salida) and update product quantity.

    `code` may be a barcode or a SKU — barcode is preferred when both match.

    Gestión OPCIONAL de lotes (FEFO):
      - En `entrada`, si se indica `lot_number`, se crea/actualiza el lote con su
        caducidad y coste.
      - En `salida`, si el producto tiene lotes, se descuenta en orden FEFO
        (primero el que caduca antes). Si no tiene lotes, se comporta como antes.
    """
    product = await _find_product_by_code(db, tenant_id, code)
    if not product:
        raise LookupError(f"Producto con código '{code}' no encontrado")

    current_stock = float(product.stock_quantity or 0)
    qty = abs(quantity)

    lots_info: dict | None = None
    if movement_type == "entrada":
        new_stock = current_stock + qty
        if lot_number:
            await lot_service.add_lot(
                db,
                tenant_id=tenant_id,
                product_id=product.id,
                lot_number=lot_number,
                quantity=int(qty),
                expiry_date=expiry_date,
                cost_price=cost_price,
            )
    else:
        if qty > current_stock:
            raise ValueError(f"Stock insuficiente ({current_stock} < {qty})")
        new_stock = current_stock - qty
        if await lot_service.has_lots(db, product.id):
            lots_info = await lot_service.deduct_fefo(db, product_id=product.id, quantity=int(qty))

    product.stock_quantity = new_stock

    movement = StockMovement(
        product_id=product.id,
        movement_type=movement_type,
        # `quantity` se guarda como magnitud POSITIVA en todo el sistema; la
        # dirección la marca `movement_type` (entrada/salida/ajuste). La UI ya
        # aplica el signo según el tipo.
        quantity=qty,
        stock_after=new_stock,
        unit_cost=cost_price if movement_type == "entrada" else None,
        reference=f"scanner:{device}",
        notes=notes or f"Movimiento vía escáner ({movement_type})",
    )
    db.add(movement)
    await db.commit()

    return {
        "product_id": str(product.id),
        "sku": product.sku,
        "barcode": product.barcode,
        "name": product.name,
        "movement_type": movement_type,
        "quantity": qty,
        "stock_before": current_stock,
        "stock_after": new_stock,
        "low_stock": (product.stock_min_alert is not None and new_stock <= float(product.stock_min_alert)),
        "lots": lots_info,
    }


async def confirm_delivery(db: AsyncSession, tenant_id: UUID, albaran_number: str) -> dict:
    """Confirm delivery of an albaran."""
    result = await db.execute(
        select(DeliveryNote).where(
            DeliveryNote.tenant_id == tenant_id,
            DeliveryNote.albaran_number == albaran_number,
        )
    )
    albaran = result.scalars().first()
    if not albaran:
        raise LookupError(f"Albarán '{albaran_number}' no encontrado")

    if albaran.status == "delivered":
        return {"status": "already_delivered", "albaran_number": albaran.albaran_number}

    previous_status = albaran.status
    albaran.status = "delivered"
    await db.commit()

    return {
        "status": "confirmed",
        "albaran_number": albaran.albaran_number,
        "previous_status": previous_status,
        "client_name": albaran.client_name if hasattr(albaran, "client_name") else None,
    }
