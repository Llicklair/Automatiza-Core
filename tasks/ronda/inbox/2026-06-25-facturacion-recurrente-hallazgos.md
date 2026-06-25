# Inbox /forja v2 — facturación recurrente / scheduler (2026-06-25, lente correctitud+idempotencia)

Flujo: job diario `_process_recurring_invoices` (`backend/app/workers/tasks_scheduler.py:326-396`) +
`commands.run_recurring` (path manual/API). Todo crea facturas reales → **revisión humana, no auto-fix**
(verificado en código, NO son falsos positivos).

## ⚠️ ALTA — facturas DUPLICADAS por falta de idempotencia
1. **`tasks_scheduler.py:326-396` `_process_recurring_invoices` sin guard por (plantilla, periodo)** —
   el `SELECT` toma todas las `RecurringInvoice` activas con `next_run_date <= today`, genera la factura,
   y SOLO al final del loop (línea 394) hace `db.commit()`. `next_run_date` se avanza en memoria (388) pero
   no se persiste hasta ese commit final. Si el job se relanza antes de commitear (reinicio del worker a
   mitad, doble disparo de APScheduler, o `run_recurring` manual concurrente sobre la misma plantilla), la
   condición `next_run_date <= today` sigue cierta → se generan facturas NUEVAS del mismo periodo con
   números REC correlativos distintos. El `UNIQUE(tenant_id, invoice_number)` protege el número, NO el
   periodo. Impacto: doble cobro al cliente + números de serie AEAT consumidos de más.
   **Fix recomendado (tu diseño, toca facturas):**
   - (a) **commit por plantilla** dentro del loop (factura + avance de `next_run_date` atómicos por
     iteración) → un reinicio a mitad solo deja sin procesar las que aún no avanzaron, nunca duplica las ya
     hechas; y
   - (b) **guard de skip** al inicio de la iteración: `if rec.last_run_date == today: continue` (no
     regenerar dos veces el mismo día); y/o
   - (c) tabla/columna de "última ejecución por periodo" con `UNIQUE(recurring_invoice_id, period_key)`.

## Media — fechas: scheduler diverge del path manual
2. **`tasks_scheduler.py:388` usa días fijos vs. `commands.run_recurring` usa meses reales** — el scheduler:
   `rec.next_run_date = today + timedelta(days=interval_map[...])` con `{"monthly":30,"quarterly":90,
   "yearly":365}`; mientras `commands.py:703-717` `run_recurring` usa `_add_months` con `calendar.monthrange`.
   Caso: plantilla mensual del 31-ene → scheduler la pone en `2-mar` (31+30d) en vez de `28-feb`; tras 12
   meses deriva ~5 días, y si se mezcla con una ejecución manual (que sí usa meses reales) las fechas se
   desalinean. Fix objetivo (toca fechas de facturación → revisión): unificar el scheduler en `_add_months`
   (reutilizar el de `commands.py`). Es el cambio más limpio del barrido pero cambia CUÁNDO se emite.

## Baja — timezone del servidor, no del tenant
3. **`tasks_scheduler.py:327-328` `date.today()` + `datetime.now(UTC)` server-side** — la comparación de
   vencimiento y la fecha de la factura usan la TZ del servidor (UTC en prod), no la del tenant
   (p.ej. Europe/Madrid). Una factura generada el 1-jul 22:00 UTC lleva fecha `01-jul` cuando en Madrid ya
   es `02-jul`. Ventana de error pequeña con job a las 08:00, pero la fecha de factura es fiscalmente
   relevante. No tocar sin política explícita de TZ por tenant.

## Revisado — correcto (NO es bug)
- ✅ #4 estados: el filtro `is_active.is_(True)` (línea 340) ya excluye plantillas canceladas/pausadas. Una
  factura generada y luego anulada no necesita bloquear el periodo aparte — eso lo cubriría el guard de #1.
