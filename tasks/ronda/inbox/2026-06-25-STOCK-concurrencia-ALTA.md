# Inbox /forja v2 — ⚠️⚠️ CONCURRENCIA EN STOCK (sobreventa) — PRIORIDAD ALTA

Hallazgo más importante del barrido nocturno. Patrón de **race read-modify-write sin lock** en
toda la ruta de ventas → **sobreventa / stock negativo** con operaciones concurrentes. NO
auto-arreglado: ruta de dinero/stock + cambio coordinado multi-fichero + la concurrencia NO se
puede verificar con el test infra actual (SQLite); requiere tests con Postgres real.

## El patrón (verificado, código exacto)
`SELECT product; new = stock - n; if new<0 raise; product.stock = new; commit` — sin `FOR UPDATE`
ni UPDATE atómico. Dos peticiones con stock=5, qty=5: ambas leen 5, ambas pasan el check, ambas
escriben 0 → se consumieron 10 unidades sobre 5.

## Instancias
1. **[alta] `services/sales/commands.py:172-205` `create_stock_movement`** — salidas de stock.
2. **[alta] `services/sales/pos.py:230-244` `pos.checkout`** — TPV, alta velocidad (2 cajeros, mismo
   producto). El guard `reference=POS_SESSION:<id>` protege doble-submit de la MISMA sesión, no la
   race entre sesiones distintas.
3. **[media] `services/inventory/stock_service.py:159-170` `transfer`** — TOCTOU: `_available_in`
   (sin FOR UPDATE) → check → escribe `ProductStock`. Dos transferencias → desglose por almacén negativo.
4. **[media] `services/sales/commands.py:632-653` `update_albaran_status`→`_deduct_stock_for_albaran`** —
   el guard de idempotencia (`SELECT StockMovement WHERE reference=...`) corre sin lock sobre el albarán:
   dos confirmaciones concurrentes del mismo albarán pasan ambas el guard → doble descuento de stock.

## Fix recomendado (coordinado)
- #1/#2/#3: **UPDATE atómico** (preferido, sin lock retenido):
  `UPDATE products SET stock_quantity = stock_quantity - :n WHERE id=:id AND tenant_id=:t AND stock_quantity >= :n`
  → comprobar `rowcount == 1`; si 0 → "stock insuficiente". Alternativa: `SELECT ... FOR UPDATE` antes del check.
- #4: añadir **`UNIQUE (tenant_id, reference)` en `stock_movements`** (migración) → la 2ª inserción
  concurrente falla con IntegrityError y se maneja idempotentemente. ⚠️ Revisar antes si hay
  `reference NULL` duplicados en producción.
- **Tests**: con Postgres real, dos transacciones concurrentes (`asyncio.gather` con 2 sesiones) que
  intenten decrementar el mismo producto y afirmen que el total nunca queda negativo / no hay doble
  descuento. (SQLite del conftest no reproduce el locking de Postgres.)

Recomendación: un PR dedicado para esto, con su suite de concurrencia, revisado por ti. Es la deuda
de correctitud de mayor impacto de negocio encontrada (vender lo que no hay).
