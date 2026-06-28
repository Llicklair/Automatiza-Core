"""Operaciones de inventario por lotes (batch).

Reúne en un solo sitio las modificaciones masivas de stock y de catálogo que el
agente de stock necesita, con soporte de `dry_run` para poder PREVISUALIZAR los
cambios (antes→después) sin tocar la BD y aplicarlos solo tras confirmación.

Convenciones respetadas (ver app/services/sales/*):
- `StockMovement.quantity` se guarda como magnitud POSITIVA; la dirección la
  marca `movement_type` ("entrada", "salida", "ajuste").
- `StockMovement.stock_after` es el stock global resultante del producto.
- Todo filtra por `tenant_id` (multi-tenant).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Product, StockMovement

# Campos de catálogo editables en lote y su tipo de validación.
_NUMERIC_FIELDS = {"price", "cost_price", "tax_percentage", "stock_min_alert"}
_TEXT_FIELDS = {"category", "location"}
_BOOL_FIELDS = {"is_active"}
EDITABLE_FIELDS = _NUMERIC_FIELDS | _TEXT_FIELDS | _BOOL_FIELDS

# op → movement_type para los ajustes de stock.
_OP_MOVEMENT = {"set": "ajuste", "add": "entrada", "remove": "salida"}


async def resolve_product(
    db: AsyncSession, tenant_id: UUID, ref: str
) -> tuple[Product | None, str]:
    """Resuelve una referencia de producto (id, SKU, código de barras o nombre).

    Devuelve (producto, motivo). Si hay varias coincidencias por nombre, devuelve
    (None, 'ambiguo: N coincidencias') para que el caller lo marque como warning
    en lugar de modificar el producto equivocado.
    """
    ref = (ref or "").strip()
    if not ref:
        return None, "referencia vacía"

    # 1) UUID exacto
    try:
        pid = UUID(ref)
        prod = await db.get(Product, pid)
        if prod and prod.tenant_id == tenant_id:
            return prod, "id"
        return None, "id no encontrado en este tenant"
    except (ValueError, TypeError):
        pass

    # 2) SKU o código de barras exactos
    res = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id,
            or_(Product.sku == ref, Product.barcode == ref),
        )
    )
    exact = res.scalars().all()
    if len(exact) == 1:
        return exact[0], "sku/barcode"
    if len(exact) > 1:
        return None, f"ambiguo: {len(exact)} coincidencias por SKU/código"

    # 3) Nombre (case-insensitive, exacto primero, luego contiene)
    res = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id, Product.name.ilike(ref)
        )
    )
    by_name = res.scalars().all()
    if len(by_name) == 1:
        return by_name[0], "nombre exacto"
    if len(by_name) > 1:
        return None, f"ambiguo: {len(by_name)} coincidencias por nombre"

    res = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id, Product.name.ilike(f"%{ref}%")
        )
    )
    contains = res.scalars().all()
    if len(contains) == 1:
        return contains[0], "nombre parcial"
    if len(contains) > 1:
        return None, f"ambiguo: {len(contains)} coincidencias por nombre parcial"

    return None, "no encontrado"


def _to_int(value: object) -> int:
    return int(float(value))


async def batch_adjust_stock(
    db: AsyncSession,
    tenant_id: UUID,
    items: list[dict],
    op: str = "set",
    reason: str = "",
    user_id: UUID | None = None,
    dry_run: bool = True,
) -> dict:
    """Ajusta stock de varios productos a la vez.

    items: lista de {"ref": str, "quantity": number}.
    op:
      - "set":    fija la cantidad absoluta (recuento de inventario) → movimiento "ajuste"
      - "add":    suma unidades (entrada de mercancía)               → movimiento "entrada"
      - "remove": resta unidades (mermas, roturas, salidas)          → movimiento "salida"

    Con dry_run=True NO escribe nada: solo calcula el plan (antes→después) y los
    warnings (no encontrado, ambiguo, stock negativo). Con dry_run=False aplica y
    commitea, registrando un StockMovement por producto.
    """
    if op not in _OP_MOVEMENT:
        raise ValueError(f"op inválido '{op}'. Usa: set, add, remove.")
    movement_type = _OP_MOVEMENT[op]

    plan: list[dict] = []
    applied = 0
    for item in items:
        ref = str(item.get("ref", "")).strip()
        try:
            qty = _to_int(item.get("quantity"))
        except (ValueError, TypeError, InvalidOperation):
            plan.append({"ref": ref, "status": "error", "warning": "cantidad no numérica"})
            continue
        if qty < 0:
            plan.append({"ref": ref, "status": "error", "warning": "cantidad negativa no permitida"})
            continue

        product, how = await resolve_product(db, tenant_id, ref)
        if product is None:
            plan.append({"ref": ref, "status": "skipped", "warning": how})
            continue

        before = int(product.stock_quantity or 0)
        if op == "set":
            after = qty
        elif op == "add":
            after = before + qty
        else:  # remove
            after = before - qty

        row = {
            "ref": ref,
            "product_id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "before": before,
            "after": after,
            "delta": after - before,
            "movement_type": movement_type,
            "resolved_by": how,
        }

        if after < 0:
            row["status"] = "skipped"
            row["warning"] = f"resultaría en stock negativo ({after})"
            plan.append(row)
            continue

        row["status"] = "ok"
        plan.append(row)

        if not dry_run and after != before:
            product.stock_quantity = after
            # Convención de `quantity` en StockMovement (igual que sales/commands.py
            # y el modal de stock del frontend):
            #   - "ajuste": quantity = NUEVO total absoluto (la UI muestra "= {q} → {stock_after}")
            #   - "entrada"/"salida": quantity = magnitud del movimiento (uds. movidas)
            movement_qty = after if movement_type == "ajuste" else abs(after - before)
            db.add(
                StockMovement(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    user_id=user_id,
                    movement_type=movement_type,
                    quantity=movement_qty,
                    stock_after=after,
                    unit_cost=product.cost_price,
                    reference="batch",
                    notes=(reason or "Ajuste por lotes") + f" [{before}→{after}]",
                )
            )
            applied += 1

    if not dry_run:
        await db.commit()

    return {
        "op": op,
        "movement_type": movement_type,
        "dry_run": dry_run,
        "total": len(items),
        "ok": sum(1 for r in plan if r["status"] == "ok"),
        "skipped": sum(1 for r in plan if r["status"] in ("skipped", "error")),
        "applied": applied,
        "plan": plan,
    }


def _coerce_field(field: str, value: object) -> object:
    """Valida y convierte el valor de un campo editable. Lanza ValueError si no aplica."""
    if field in _NUMERIC_FIELDS:
        try:
            num = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(f"'{field}' debe ser numérico (recibido: {value!r})") from exc
        if num < 0:
            raise ValueError(f"'{field}' no puede ser negativo")
        if field == "stock_min_alert":
            return int(num)
        return num
    if field in _BOOL_FIELDS:
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        if s in ("true", "1", "sí", "si", "activo", "yes"):
            return True
        if s in ("false", "0", "no", "inactivo"):
            return False
        raise ValueError(f"'{field}' debe ser booleano (recibido: {value!r})")
    # texto
    return str(value)


async def batch_update_fields(
    db: AsyncSession,
    tenant_id: UUID,
    items: list[dict],
    dry_run: bool = True,
) -> dict:
    """Actualiza campos de catálogo de varios productos a la vez.

    items: lista de {"ref": str, "fields": {campo: valor, ...}}.
    Campos permitidos: price, cost_price, tax_percentage, stock_min_alert,
    category, location, is_active.

    Con dry_run=True devuelve el plan (campo: antes→después) sin escribir.
    """
    plan: list[dict] = []
    applied = 0
    for item in items:
        ref = str(item.get("ref", "")).strip()
        fields = item.get("fields") or {}
        if not isinstance(fields, dict) or not fields:
            plan.append({"ref": ref, "status": "error", "warning": "sin campos a actualizar"})
            continue

        unknown = set(fields) - EDITABLE_FIELDS
        if unknown:
            plan.append(
                {"ref": ref, "status": "error", "warning": f"campos no editables: {', '.join(sorted(unknown))}"}
            )
            continue

        product, how = await resolve_product(db, tenant_id, ref)
        if product is None:
            plan.append({"ref": ref, "status": "skipped", "warning": how})
            continue

        changes: dict[str, dict] = {}
        error = None
        coerced: dict[str, object] = {}
        for field, value in fields.items():
            try:
                new_val = _coerce_field(field, value)
            except ValueError as e:
                error = str(e)
                break
            old_val = getattr(product, field)
            coerced[field] = new_val
            changes[field] = {
                "before": float(old_val) if isinstance(old_val, Decimal) else old_val,
                "after": float(new_val) if isinstance(new_val, Decimal) else new_val,
            }

        if error:
            plan.append({"ref": ref, "name": product.name, "status": "error", "warning": error})
            continue

        row = {
            "ref": ref,
            "product_id": str(product.id),
            "name": product.name,
            "sku": product.sku,
            "changes": changes,
            "resolved_by": how,
            "status": "ok",
        }
        plan.append(row)

        if not dry_run:
            for field, new_val in coerced.items():
                setattr(product, field, new_val)
            applied += 1

    if not dry_run:
        await db.commit()

    return {
        "dry_run": dry_run,
        "total": len(items),
        "ok": sum(1 for r in plan if r["status"] == "ok"),
        "skipped": sum(1 for r in plan if r["status"] in ("skipped", "error")),
        "applied": applied,
        "plan": plan,
    }
