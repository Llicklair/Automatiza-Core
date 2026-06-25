# Inbox /forja v2 — importación de datos tabulares (2026-06-25, lente correctitud+errores+seguridad)

Flujo: subida de fichero (CSV/Excel/JSON) → `_tabular.parse_tabular_file` → `erp_import.apply_import`
(crea productos/clientes/empleados). El #4 (DoS sin tope de filas) ya ARREGLADO + 81 tests verde → PR #52.
Estos quedan (tocan datos/semántica de import):

## ⚠️ ALTA — re-importar duplica TODO
1. **`documents/erp_import.py:226` `apply_import` no deduplica** — el bucle hace
   `db.add(model_cls(tenant_id=tenant_id, **rec))` por fila sin ningún `SELECT` previo. Re-importar el
   mismo CSV (error humano frecuente) inserta productos/clientes/empleados DUPLICADOS. No hay `ON CONFLICT`,
   ni `UNIQUE`, ni comparación por nombre/NIF/SKU. Contraste: `billing/invoice_import.py` SÍ es idempotente
   (comprueba `proveedor + invoice_number`). Fix (decisión tuya, toca catálogo/CRM/importes): dedupe por
   clave natural por target (producto→SKU/nombre, cliente→NIF, empleado→DNI) con skip o upsert. Difícil de
   deshacer a mano una vez duplicado → conviene antes de que lo usen clientes.

## Media — perf/memoria en matching de factura
3. **`billing/invoice_import.py:113-116` `_match_product` carga TODO el catálogo activo por cada línea** —
   fallback normalizado: `select(Product).where(tenant, is_active)` dentro del bucle de líneas. Catálogo de
   10k productos × 50 líneas × N facturas en lote = cientos de miles de objetos ORM por import → posible OOM
   con catálogos grandes. Fix: materializar un índice normalizado {nombre/SKU→producto} UNA vez antes del
   bucle de líneas (o por draft). Toca la ruta de importación de stock → revisión antes de tocar.

## Descartado (revisado, NO es bug)
- ❌ #2 "atomicidad parcial en `apply_import`": FALSO. El constructor `model_cls(**rec)` lanza ANTES de
  `db.add`, así que un objeto inválido nunca entra en la sesión; los errores por fila se capturan y se
  cuentan como `skipped`; el `commit` final es todo-o-nada con `rollback` (devuelve `created=0`). La
  atomicidad es correcta. Único nice-to-have (no bug): `flush` por fila para reportar QUÉ fila viola una
  constraint de BD — diferible.
