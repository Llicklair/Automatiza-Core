# Inbox /forja (run-2) — sales_orders · BARRIDO 6 LENTES (2026-06-26)

Primer flujo con el modo **6-lentes en paralelo** (6 finders, uno por lente). Cobertura completa de
`create/update/delete_sales_order` (`services/sales/commands.py:788-880`), `queries.py`, ruta
`routes/sales_orders.py`, modelo `db/models/orders.py`. Marcado ✅ (6 lentes) en coverage.

## ⚠️ Media — SEGURIDAD: `client_id` no validado contra tenant al crear
`create_sales_order` (commands.py:788-836) asigna el `client_id` del payload al ORM sin comprobar
`Client.tenant_id == tenant_id`. Un usuario del tenant A puede crear un pedido apuntando a un cliente del
tenant B; el `joinedload(client)` de la respuesta devuelve nombre/NIF ajenos → fuga cross-tenant. RLS NO lo
frena (la fila del pedido está en el tenant correcto; la FK apunta fuera). Fix: `SELECT Client WHERE
id=client_id AND tenant_id=tenant_id` antes del flush; `LookupError` si no. **Verificar la MISMA omisión en
`create_quote` y `create_invoice`** (probable hermana).

## ⚠️ Alta — PERF: listados sin `.limit()` (patrón, 3 sitios)
`queries.py`: `list_sales_orders` (L368), `list_purchase_orders` (L353), `list_albaranes` (L267) NO paginan
→ vuelcan toda la tabla + joins a memoria. Los hermanos bien hechos (`list_clients`, `list_products`,
`list_quotes`, `list_stock_movements`) sí tienen `.limit()/.offset()`. Fix: añadir paginación a los 3 +
exponer `skip/limit` en sus rutas. Blast radius medio (3 servicios + 3 rutas) → PR dedicado.

## Media — ERRORES: `delete_sales_order` → 500 en vez de 409 (hermana del delete→409)
`commands.py:871` lanza `ConflictError` pero `routes/sales_orders.py:75-78` solo captura `LookupError` → el
ConflictError escapa → **500**. Es la hermana del patrón delete→409 ya aplicado en otras entidades, FALTA
aquí. Fix objetivo (1 línea en la ruta): `except ConflictError: raise HTTPException(409, ...)`. (Verificar
si quotes/otras rutas tienen el mismo gap.)

## Media — CONCURRENCIA
- `order_number = PED-{timestamp segundos}` sin `UNIQUE(tenant_id, order_number)` → doble-submit en el mismo
  segundo / multi-worker duplica. (Hermana de la numeración de factura por COUNT.) Fix: UNIQUE (migración).
- `update_sales_order` SELECT sin `with_for_update()` ni guard de transición → dos confirmaciones
  concurrentes ambas pasan. Hoy el daño es estado inconsistente (no descuenta stock ni factura aún), pero
  es trampa estructural si se añade lógica de confirmación. Fix: lock + máquina de estados.

## Media/baja — CORRECTITUD
- Cabecera (`amount_base/tax_amount`) se suma con `float` crudo sin redondear por línea, mientras cada
  `line.total` sí se redondea → con descuentos fraccionales la cabecera puede no cuadrar con Σlíneas. Fix:
  sumar los `round`-por-línea (fuente de verdad única).
- `update_sales_order` hace `setattr` de todo `data` sin whitelist → si se llama fuera del schema (agente),
  `tenant_id`/`amount_total`/`order_number` serían sobreescribibles. Hoy mitigado por el schema (3 campos).
  Whitelist defensiva. La transición de `status` no tiene máquina de estados (acepta cualquier string).

## 🧪 TEST-GAPS (para loop-tester)
1. **Totales con descuento** — ningún test afirma `amount_base/tax_amount/amount_total` con `discount>0`.
   (Alta: descuadre silencioso que llega a la factura.)
2. **Recálculo en update** — si se editan líneas/precio, ¿se recalcula la cabecera? Sin test (y posible bug).
3. **delete con factura/dependencia asociada → 409** — el delete solo se testea sin dependencias.

## Calibrado fuera (no defecto)
- Authz sólida: `get_current_user` en todos los endpoints, `tenant_id` del token (no del payload), `order_id`
  tipado UUID, rate-limit, `list/update/delete` filtran tenant. Sin IDOR en escritura/borrado, sin inyección.
- NO existe `convert_to_invoice` para pedidos de venta (solo para quotes) ni descuento de stock al confirmar
  — ausencias esperadas, no bugs.
