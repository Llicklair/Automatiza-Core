# Inbox /forja v2 — CRM / clientes (2026-06-25, lente correctitud+seguridad)

Flujo: alta/edición/borrado de cliente, validación, dedup. Aplicada la lente RLS (toda tabla con
`tenant_id` está bajo RLS fail-closed vía `security_bootstrap.py`). FIX 1 (scope tenant en PDF albarán,
defensa en profundidad) + FIX 3 (nombre vacío) ya hechos → PR #52. Quedan dos objetivos:

## ✅ RESUELTO (2026-06-26, PR #52 commits f3b0e05+ab529a4) — delete_client ahora devuelve 409 (ConflictError) + test de regresión `test_delete_conflict_409.py`. Nota original abajo como registro.

## Media — borrar cliente con facturas devuelve 500 en vez de 409
2. **`sales/commands.py:121` `delete_client` no distingue FK violation** — `Invoice.client_id`
   (`billing.py:62`) es `ForeignKey("clients.id")` SIN `ondelete`, y `Client.invoices` no tiene cascade.
   Borrar un cliente con facturas → PostgreSQL lanza FK violation → se captura como `SQLAlchemyError` y se
   relanza `RuntimeError("Error al eliminar el cliente")` → el frontend recibe **500 genérico** en vez de un
   **409/422 accionable** ("el cliente tiene facturas asociadas"). Mismo patrón para `Quote` (billing.py:190),
   `SalesOrder` (orders.py:23), `Opportunity` (crm.py:66). Fix objetivo: capturar `IntegrityError`
   específicamente en `delete_client` → `ValueError`/excepción de dominio → la ruta mapea a 409 con mensaje.
   (Bajo riesgo, pero toca flujo de borrado + capa de ruta → siguiente turno o tu revisión.)

## Media — NIF/email sin normalizar → duplicados silenciosos
4. **`sales/commands.py:52` `create_client` persiste NIF/email tal cual** — el índice único
   `clients_unique_nif_per_tenant` (`crm.py:31`) compara el valor LITERAL: `"B12345678"` vs `"b12345678"`
   vs `"B12345678 "` (con espacio) son tres clientes distintos; el unique no es case-insensitive ni hace
   trim. Igual con `email` (`"CLI@ACME.COM"` vs `"cli@acme.com"`). → dedup roto, clientes duplicados.
   Fix objetivo: normalizar antes de instanciar el ORM en `create_client` Y `update_client`
   (`nif = nif.strip().upper()` si no None; `email = email.strip().lower()` si no None). ⚠️ OJO: cambia
   valores ALMACENADOS → revisar datos existentes / posible colisión con el unique al normalizar registros
   ya duplicados antes de aplicarlo en masa. Por eso a inbox y no auto-fix directo.

## Revisado — NO es fuga (RLS lo cubre)
- ⚠️→✅ #1 "`get_albaran_pdf_data` resuelve cliente sin tenant": la tabla `clients` tiene `tenant_id` →
  RLS fail-closed ya filtra a nivel BD. NO es explotable. Se arregló igualmente por consistencia/defensa en
  profundidad (el vecino `get_albaran` sí filtraba explícito) → PR #52. Severidad real: baja/higiene.
  Nota: el NIF español (DNI/NIE/CIF) tampoco valida check-digit en el alta (`ClientCreate.nif`) — delicado
  (semántica fiscal), no auto-fix; apuntar si se quiere endurecer.
