# Inbox /forja v2 — compras / recepción de mercancía (2026-06-26, lente correctitud)

Flujo: pedido de compra → recepción → stock. FIX #1 (guard de estado: no recibir cancelado/recibido) + FIX
#2 (`quantity > 0`) ya hechos → PR #52, 51 tests verde + regresión. Quedan dos que tocan stock/auditoría:

## ⚠️ Media — borrar un pedido parcialmente recibido NO revierte el stock
4. **`sales/commands.py:752-762` `delete_purchase_order`** — borra el PO y sus líneas (cascade) sin
   comprobar estado ni generar movimientos compensatorios. Si el PO se recibió parcialmente
   (`received_quantity > 0`), el stock YA se incrementó; al borrar el PO desaparece la evidencia pero el
   stock extra queda en `Product.stock_quantity` → **inventario inflado permanente sin traza**. Caso: PO-123
   recibe 10 uds (stock +10) → DELETE PO-123 → stock sigue +10 sin justificante. Contrasta con
   `delete_albaran` (L658-674) que SÍ llama a `_revert_stock_for_albaran` antes de borrar. Fix: replicar esa
   reversa para purchase orders (o bloquear el borrado si hay recepciones, devolviendo 409 — encaja con el
   patrón `delete→409` ya implementado). Toca importes de inventario → revisión humana.

## Baja — `stock_after` del StockMovement impreciso con líneas del mismo producto
3. **`sales/purchase_receiving.py:83`** — `stock_after=int(product.stock_quantity)` se captura tras
   `add_to_warehouse` pero sin `flush` por línea; en un PO con dos líneas del MISMO producto, el `stock_after`
   del histórico puede reflejar la suma acumulada en ambas (identity map de SQLAlchemy devuelve el objeto ya
   modificado). El stock REAL es correcto; solo el campo de auditoría `stock_after` queda impreciso. Fix:
   `await db.flush()` entre líneas del mismo producto, o calcular `stock_after` explícitamente acumulando.
   No cambia stock → bajo, pero toca la lógica de auditoría → revisión.
