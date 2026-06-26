# Inbox /forja v2 — productos / catálogo (2026-06-26, lente correctitud+perf)

Flujo: alta/edición/búsqueda de producto. FIX #3 (escape de metacaracteres LIKE en `list_products`) ya hecho
→ PR #52, 55 tests verde. El finder confirmó SIN N+1 en el listado. Quedan tres:

## ⚠️ Media — sin validación de rango (precio/stock/IVA) — OJO trampa de schema
1. **`schemas/erp.py:41-58` `ProductCreate`** acepta `price: -50`, `tax_percentage: 99`, `stock_quantity: -10`
   sin validación (ni `Field(ge=...)` ni validador; el ORM tampoco tiene CHECK). Un precio negativo da líneas
   de factura con total negativo. **PERO no es un fix trivial**: `ProductResponse(ProductCreate)` (L61)
   HEREDA de `ProductCreate`, así que añadir validadores `ge=0` a Create también correría al SERIALIZAR
   `ProductResponse` desde BD → y un producto legacy con **`stock_quantity` negativo** (plausible: es justo el
   bug de sobreventa del inbox STOCK) **rompería el listado con 500**. (Mismo patrón en
   `InvoiceLineResponse(InvoiceLineCreate)`, L81.) Fix correcto: REESTRUCTURAR — `ProductBase` permisiva (sin
   validadores) de la que herede `ProductResponse`, y `ProductCreate(ProductBase)` con la validación
   (`price ge=0`, `stock_* ge=0`, `tax_percentage` en [0,100] o {0,4,10,21}). Aplicar lo mismo en
   `EmployeeBase` ya se hizo bien (validación solo en Create/Update). Requiere tocar la jerarquía → revisión.

## Media — SKU sin normalizar ni unique por tenant
2. **`models/inventory.py:29` + `schemas/erp.py:43-44`** — `sku`/`barcode` `String(100) index=True` SIN
   `UniqueConstraint("tenant_id","sku")`, y sin `.strip().upper()` en el schema. `"ABC123"` y `"abc123 "` →
   dos productos distintos en el mismo tenant; `get_product_by_barcode` usa `==` case-sensitive. Mismo patrón
   que clientes (NIF/email). Fix: normalizar en create/update + `UniqueConstraint` (migración → limpiar
   duplicados existentes ANTES). Cambia valores almacenados + migración → revisión humana.

## Baja — create_product sin manejo de IntegrityError
4. **`sales/commands.py:134-139` `create_product`** hace `Product(**data)` + commit sin try/except. Si se
   añade el unique de SKU (#2) o falla otra constraint (supplier_id inválido), el `IntegrityError` sube a 500
   en vez de 400/409. `create_client` (L54-59) ya tiene el patrón correcto (rollback + ConflictError). Fix:
   replicar ese patrón. Bajo valor hoy (no hay constraint que falle aún); encaja en un futuro "create→409"
   transversal análogo al `delete→409` ya hecho.
