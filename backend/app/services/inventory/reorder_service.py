"""Reposición automática: sugerencias de pedido y generación de pedidos de
compra borrador cuando el stock baja del punto de pedido (`stock_min_alert`).

`run_auto_reorder` es el punto de entrada del scheduler diario: genera los
borradores para todos los tenants de forma idempotente (no duplica un producto
que ya esté en un pedido de compra abierto).

No lanza HTTPException — solo excepciones Python o valores de retorno.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.crm import Client
from app.db.models.inventory import Product
from app.db.models.orders import PurchaseOrder, PurchaseOrderLine

logger = logging.getLogger(__name__)

# Estados de pedido de compra que se consideran "abiertos" para idempotencia:
# si un producto ya está en uno de estos, no se vuelve a pedir.
_OPEN_PO_STATUSES = ("draft", "pending", "sent")


def _suggest_qty(product: Product) -> int:
    """Cantidad sugerida a pedir. Si hay `reorder_quantity`, se usa; si no, se
    sugiere lo necesario para llevar el stock al doble del mínimo (mín. 1)."""
    if product.reorder_quantity and int(product.reorder_quantity) > 0:
        return int(product.reorder_quantity)
    target = int(product.stock_min_alert or 0) * 2
    return max(target - int(product.stock_quantity or 0), 1)


async def suggest_reorders(db: AsyncSession, tenant_id: UUID) -> list[dict]:
    """Productos en/bajo su punto de pedido, con cantidad sugerida y proveedor."""
    result = await db.execute(
        select(Product, Client.name)
        .outerjoin(Client, Product.supplier_id == Client.id)
        .where(
            Product.tenant_id == tenant_id,
            Product.is_active.is_(True),
            Product.stock_min_alert > 0,
            Product.stock_quantity <= Product.stock_min_alert,
        )
        .order_by(Product.stock_quantity.asc())
    )
    out: list[dict] = []
    for product, supplier_name in result.all():
        out.append(
            {
                "product_id": str(product.id),
                "name": product.name,
                "sku": product.sku,
                "current_stock": int(product.stock_quantity or 0),
                "reorder_point": int(product.stock_min_alert or 0),
                "suggested_qty": _suggest_qty(product),
                "cost_price": float(product.cost_price) if product.cost_price is not None else None,
                "tax_percentage": float(product.tax_percentage or 0),
                "supplier_id": str(product.supplier_id) if product.supplier_id else None,
                "supplier_name": supplier_name,
            }
        )
    return out


async def _products_in_open_pos(db: AsyncSession, tenant_id: UUID) -> set[str]:
    """IDs de productos que ya están en un pedido de compra abierto (idempotencia)."""
    result = await db.execute(
        select(PurchaseOrderLine.product_id)
        .join(PurchaseOrder, PurchaseOrderLine.order_id == PurchaseOrder.id)
        .where(
            PurchaseOrder.tenant_id == tenant_id,
            PurchaseOrder.status.in_(_OPEN_PO_STATUSES),
            PurchaseOrderLine.product_id.is_not(None),
        )
    )
    return {str(pid) for (pid,) in result.all() if pid}


async def generate_draft_pos(db: AsyncSession, tenant_id: UUID) -> dict:
    """Genera pedidos de compra BORRADOR agrupando las sugerencias por proveedor.

    Idempotente: omite productos que ya estén en un pedido de compra abierto
    (`skipped_existing_po`). Los productos sin proveedor van en
    `skipped_no_supplier`.
    """
    suggestions = await suggest_reorders(db, tenant_id)
    already_open = await _products_in_open_pos(db, tenant_id)

    groups: dict[str, list[dict]] = defaultdict(list)
    skipped_no_supplier: list[str] = []
    skipped_existing: list[str] = []
    for s in suggestions:
        if s["product_id"] in already_open:
            skipped_existing.append(s["name"])
            continue
        if not s["supplier_id"]:
            skipped_no_supplier.append(s["name"])
            continue
        groups[s["supplier_id"]].append(s)

    created: list[dict] = []
    for supplier_id, items in groups.items():
        po = PurchaseOrder(tenant_id=tenant_id, supplier_id=UUID(supplier_id), status="draft")
        db.add(po)
        await db.flush()
        base = 0.0
        tax = 0.0
        for it in items:
            qty = it["suggested_qty"]
            unit = it["cost_price"] or 0.0
            taxp = it["tax_percentage"] or 0.0
            line_base = qty * unit
            line_tax = line_base * taxp / 100.0
            base += line_base
            tax += line_tax
            db.add(
                PurchaseOrderLine(
                    order_id=po.id,
                    product_id=UUID(it["product_id"]),
                    description=it["name"],
                    quantity=qty,
                    unit_price=unit,
                    tax_percentage=taxp,
                    total=line_base + line_tax,
                )
            )
        po.amount_base = round(base, 2)
        po.tax_amount = round(tax, 2)
        po.amount_total = round(base + tax, 2)
        created.append(
            {
                "purchase_order_id": str(po.id),
                "supplier_id": supplier_id,
                "lines": len(items),
                "amount_total": round(base + tax, 2),
            }
        )

    await db.commit()
    return {
        "created": created,
        "skipped_no_supplier": skipped_no_supplier,
        "skipped_existing_po": skipped_existing,
    }


async def run_auto_reorder() -> None:
    """Punto de entrada del scheduler: genera borradores de reposición para
    todos los tenants activos. Idempotente, así que es seguro a diario."""
    from app.db.base import AsyncSessionLocal
    from app.db.models.auth import Tenant

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Tenant).where(Tenant.is_active.is_(True)))
        for tenant in result.scalars():
            try:
                res = await generate_draft_pos(db, tenant.id)
                if res["created"]:
                    logger.info(
                        "Reposición automática tenant %s: %d pedido(s) borrador",
                        tenant.id,
                        len(res["created"]),
                    )
            except Exception as exc:
                logger.error("Error en reposición automática tenant %s: %s", tenant.id, exc)
