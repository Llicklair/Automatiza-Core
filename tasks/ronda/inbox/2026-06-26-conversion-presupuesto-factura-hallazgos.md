# Inbox /forja v2 — conversión presupuesto→factura (2026-06-26, lente correctitud)

Flujo: `services/sales/commands.py::convert_to_invoice` (~L310-360). VERIFICADO en código. Todo crea
factura EMITIDA / numeración → **revisión humana, no auto-fix; línea roja fiscal**.

## ⚠️ ALTA — numeración por COUNT sin lock, ignora el servicio canónico
2. **`sales/commands.py:321-326`** numera con:
   ```python
   count_res = await db.execute(select(func.count(Invoice.id)).where(Invoice.tenant_id == tenant_id))
   invoice_number = f"FAC-{now.year}-{(count or 0)+1:04d}"
   ```
   Problemas: (a) **sin lock** → dos conversiones concurrentes leen el mismo COUNT → mismo `FAC-YYYY-NNNN`;
   el índice `unique` sobre `invoice_number` (`billing.py:53-54`) evita el duplicado pero la 2ª revienta con
   **IntegrityError → 500**. (b) **COUNT no es correlativo-seguro**: si se borra/anula una factura el conteo
   baja → se REUSA número (colisión o hueco). (c) **ignora `billing/numbering.py::next_invoice_number`**, que
   ya hace `pg_advisory_xact_lock` + `SELECT ... FOR UPDATE` sobre un contador de serie (`invoice_series`,
   `UniqueConstraint(tenant_id, serie, year)`) — es el mecanismo que usan el scheduler recurrente y
   `run_recurring`. Fix: sustituir el COUNT inline por `await next_invoice_number(db, tenant_id, series=...)`.
   ⚠️ Cambia cómo se generan los números de factura emitida → revisión fiscal + decidir la serie (¿"FAC"?).

## Media — cabecera copiada vs líneas recalculadas (posible descuadre de céntimos)
- **`sales/commands.py:333-335` vs 343-355`** — la cabecera del Invoice copia `amount_base/tax_amount/
  amount_total` del presupuesto, pero cada `InvoiceLine` se RECALCULA (`line_base = qty*unit_price`,
  `line_tax = base*tax%/100`). Si el presupuesto almacenó esos totales con un criterio de redondeo distinto
  (p.ej. redondeo por línea vs por factura), la suma de líneas de la factura puede no cuadrar con su propia
  cabecera por ±céntimos. Hoy probablemente cuadra (mismo cálculo simple), pero conviene un test de
  consistencia cabecera==Σlíneas tras convertir. Fiscal → revisión.

## Media — se puede convertir un presupuesto rechazado/caducado
3. **`sales/commands.py:317-319`** solo bloquea `quote.status == "accepted"`. Un quote `rejected` o vencido
   (`valid_until` pasado, columna existe en `billing.py:193` pero no se lee) pasa la guardia y genera una
   factura emitida. Caso: quote `valid_until=2025-01-01`, status `draft` (el cliente nunca respondió) → se
   factura sin aceptación. Casi objetivo (añadir guards `status in {"rejected","expired"}` y/o
   `valid_until < today`), pero crea factura emitida y cambia regla de negocio → tu decisión.

## Baja — sin trazabilidad presupuesto→factura
1/4. **El Invoice no guarda `quote_id`/`source_id`** (no hay FK a `quotes` en `billing.py`); tras convertir,
   la única señal es `quote.status="accepted"`. No se puede auditar "qué factura salió de este presupuesto".
   Fix: FK `quote_id` nullable en `Invoice` (migración). Además, el descuento de línea no se arrastra
   (`QuoteLine` no tiene `discount_percentage`; `SalesOrderLine` sí) — latente: si se añade descuento a
   `QuoteLine`, `convert_to_invoice` lo ignoraría (hardcodea `discount_percentage=0.0`, L354).
