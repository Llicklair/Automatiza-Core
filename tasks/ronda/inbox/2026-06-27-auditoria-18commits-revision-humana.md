# Auditoría de 18 commits /forja — hallazgos para revisión humana

Fecha: 2026-06-27
Origen: auditoría adversarial (3 lentes: seguridad, correctitud, working-tree) sobre los
últimos 18 commits (11 sin push) + cambios sin commitear.

Resueltos en esta sesión (NO requieren acción):
- 🔴 #1 CSV formula-injection en libro registro fiscal → `services/reports/fiscal.py`
  (counterpart_nif/name/inv_number con `sanitize_spreadsheet_cell`).
- Barrido por clase del mismo patrón: `services/orchestration/context.py`
  (`save_ai_result_as_csv`) también saneado. Resto de `writerow/append` son PDF
  reportlab (no vector). `_writer.py` y `schedule_export.py` ya estaban cubiertos.

---

## Pendientes — requieren criterio humano (NO auto-fix)

### #2 — Gaps en numeración correlativa de facturas · MEDIA · FISCAL
`services/.../tasks_scheduler.py:356` (y `commands.run_recurring`).
`next_invoice_number()` hace `db.flush()` que persiste `InvoiceSeries.last_number`
ANTES de confirmar el Invoice. El `except Exception` por-tenant (línea ~390) no hace
rollback → si la creación falla tras consumir el número, queda **hueco en la serie**
(viola RD 1619/2012, justo el motivo del fix original). Además, un flush fallido en
async SQLAlchemy envenena la transacción compartida de la batch → riesgo de
`PendingRollbackError` en iteraciones siguientes.
Acción sugerida: rollback/savepoint por iteración + reservar número solo tras commit
del invoice. Decisión de semántica fiscal → revisar con responsable.

### #3 — Modelo 200 (IS) resta retenciones de facturas EMITIDAS · MEDIA · FISCAL
`services/reports/modelos_aeat.py:1059-1061`.
`retenciones = sum(retencion_irpf_amount for i in issued)`. La retención IRPF en
facturas emitidas solo aplica a autónomos/profesionales, no a sociedades (sujetos del
M200). Para una sociedad lo deducible son retenciones *soportadas* sobre sus ingresos.
Es preview con `_warning`, pero **altera el resultado de la declaración**.
Acción sugerida: validar el criterio con asesor fiscal antes de mantenerlo.

### #4 — OCR uploads sin cap de tamaño · MEDIO · DoS
`api/v1/routes/invoices.py:62,184` y `hr_expenses.py:78,144`.
`validate_ocr_upload` solo valida extensión ("no lee el cuerpo"). Luego
`content = await file.read()` sin límite de bytes, y no hay middleware de tamaño global.
Un `.pdf/.jpg` de cientos de MB se carga en memoria y se manda al LLM (DoS memoria+coste).
El helper `_read_upload_capped` (introducido para `admin.restore_backup`) solo se aplicó
a 1 de ~13 rutas de upload (faltan: hr_employees, hr_expenses, documents, invoices,
tenant, import_bulk, aeat_presentation).
Acción sugerida: decidir umbral por tipo y aplicar el helper en todas las rutas.

### #5 — TOCTOU en guard de doble-ejecución de workflow · MEDIA-BAJA
`services/workflow/_execution.py:200-209` (`run_workflow_with_context`).
`SELECT status IN (running,pending)` + `INSERT` sin UNIQUE ni `FOR UPDATE`. Dos POST
concurrentes a `/run-with-context` crean 2 ejecuciones. El test
`test_workflow_double_run_guard.py` solo cubre el caso secuencial, no la carrera.
Acción sugerida: índice parcial UNIQUE (requiere migración) o advisory lock.

---

## Nota de proceso para el loop
Patrón recurrente detectado: el loop **arregla la instancia, no la clase**. El #1 es una
regresión del propio commit `d33125e` ("saneo formula-injection CSV/Excel") que dejó
fuera el sitio hermano. Recomendación: cuando un fix sea de un patrón (injection, caps,
escapes), pedir explícitamente un **barrido exhaustivo** (`grep` de todos los sitios)
antes de cerrar. Zona fiscal/contable: marcar como **solo-hallazgo** (reportar, no
parchear) por riesgo de semántica.
