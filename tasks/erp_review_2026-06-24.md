# Revisión ERP — informe consolidado (2026-06-24)

Dos fuentes: **(A)** diagnóstico de los síntomas que reportaste usando la app, y
**(B)** revisión atómica multi-agente (16 áreas, 139 hallazgos, **23 confirmados**
tras verificación adversarial; la síntesis automática y parte de la verificación
murieron por límite de sesión — 9 verify quedaron sin correr, sus hallazgos van
como "sin verificar" en el fichero de salida `wkohju62h.output`).

---

## A. Síntomas reportados (uso real) — causa raíz

| # | Síntoma | Causa raíz | Fichero | Estado |
|---|---------|-----------|---------|--------|
| A1 | **Alertas no funcionan** | El job corre desde el scheduler (global, sin tenant) y **nunca** llama `set_current_tenant`/`rls_bypass`. Bajo RLS fail-closed cada `WHERE tenant_id=…` devuelve **0 filas** → 0 alertas. Es el único job que olvidó el patrón de `tasks_scheduler.py`. | `services/alerts/service.py:34,47` | ✅ confirmado |
| A2 | **Aprobaciones no funcionan** | El resume ramifica `if payload.get("kind")`. Las aprobaciones creadas por **detección de la frase** «requiere aprobación» (`ensure_pending_approval`) no llevan `kind` → caen al `else` = `_create_invoice_from_approval` → **fabrican una factura borrador de 0 €** en vez de ejecutar la acción real. | `workers/tasks_orchestrator.py:376` ↔ `services/orchestration/context.py:140` | ✅ confirmado |
| A3 | **Tareas: se mueven pero no se borran** | El delete individual = `cancel_task`: **lanza 400** si la tarea está en estado terminal, y si no solo pone `status="cancelled"` — **no marca `is_deleted`**. El tablero filtra por `is_deleted=False`, no por status → la tarjeta sigue visible. Solo el "borrar TODO" hace soft-delete real. | `services/workflow/task.py:149` | ✅ confirmado |
| A4 | **Horarios: «Input should be a valid UUID … found `i` at 2; Field required»** | `POST /schedules/ai-suggest` valida `ScheduleAISuggestRequest(instruction:str [req], employee_ids:list[UUID])`. El frontend "generar horarios" manda `employee_ids` con un **nombre** (no UUID) y omite `instruction`. Desajuste contrato frontend↔schema. | `api/v1/schemas/hr.py:73` · `routes/hr_time.py:95` | ⚠️ backend confirmado; falta ver el caller en frontend |
| A5 | **Asesor Jurídico/Fiscal: la tarea acaba bien pero el widget muestra «No pude obtener una respuesta»** | Sin investigar (se interrumpió). Hipótesis: el endpoint responde async (task_id) o en un campo que el widget no lee. | `routes/advisory.py` + componente frontend | ⏳ pendiente |
| A6 | **Analítica no refleja inventario** | El dashboard cubre ventas/top-productos/coste-de-bajas pero (al parecer) **no hay KPI de estado de stock actual** (valor/unidades/stock bajo). Ver también B8/B17 (la analítica de ingresos tiene otros fallos). | `services/analytics/dashboard.py` | ⚠️ probable gap; a confirmar |

---

## B. Hallazgos confirmados de la revisión profunda (23)

### 🔴 HIGH — correctitud fiscal/contable (prioridad máxima)

- **B1/B5 · Asiento de cobro duplicado al reconciliar** — `create_invoice_payment_entry` NO es idempotente (a diferencia de las otras del módulo, que sí). Reconciliar dos veces la misma factura ya pagada crea un 2º asiento 572/430 → duplica el movimiento en contabilidad. Reachable vía `POST /transactions/{id}/reconcile` y la acción aprobable. Mismo defecto en `create_payroll_payment_entry`. → guarda por `reference_id=PAY-INV-{id}`. `services/billing/auto_accounting.py:91`
- **B2 · El agente edita base/IVA saltándose `compute_invoice_totals` y sin re-encadenar VeriFactu** — `_update_invoice_async` recalcula IVA con float, muta importes en estado draft donde la huella VeriFactu YA existe → cadena desincronizada (debería ser rectificativa). `agents/billing/_invoice_write_tools.py:122`
- **B3 · La tool del agente `create_journal_entry` NO comprueba cierre de periodo** — bypass del bloqueo fiscal; instancia el asiento a mano en vez de delegar en `commands.create_journal_entry`. `agents/accounting/tools.py:58`
- **B4 · `update_payroll` deriva el %IRPF como `irpf/base`** (debería ser sobre gross) → tipo erróneo con jornada parcial/extras; además rompe si base==0. → leer `payroll.pct_irpf`. `agents/hr/_payroll_crud.py:69`
- **B6 · El matcher de conciliación ignora `invoice_type` y signo** — casa cargos (pagos) con facturas emitidas (cobros). → filtrar por dirección (`amount>0`→issued, `<0`→received). `services/banking/service.py:322`
- **B7 · Segundo motor de conciliación en el agente** con datos inventados, sin filtrar `invoice_type`, con double-apply. → eliminarlo y delegar en `service.auto_reconcile`. `agents/banking/_reconciliation_tools.py:44`
- **B8 · La analítica EXCLUYE las rectificativas/abono** (`invoice_type` filtra solo 'issued') → ingresos y beneficio **sobreestimados**. → `invoice_type.in_(("issued","rectificativa"))`. `services/analytics/dashboard.py:122`
- **B9 · 🚨 LÍNEA ROJA: el dry-run de AEAT fabrica un CSV ficticio y lo persiste como presentación `accepted`** → justificante falso. → en dry-run nunca `status='accepted'` ni rellenar `csv_justificante`. `services/aeat/sede_client.py:121`
- **B10 · El acuse descargable no distingue CSV simulado de real** (sin marcador dry-run). → marcar y abortar/avisar «JUSTIFICANTE SIMULADO — SIN VALIDEZ». `services/aeat/presentation_service.py:206`

### 🟠 MEDIUM

- **B11** Tabla de transiciones de estado duplicada/divergente agente↔`state_machine` (el agente deja cancelar una factura pagada). `agents/billing/_invoice_write_tools.py:27`
- **B12** Asiento de nómina se descuadra (debe≠haber) con horas extra / cuota solidaridad / anticipos. `services/billing/auto_accounting.py:135`
- **B13** Lógica de creación de asiento duplicada agente↔servicio. `agents/accounting/tools.py:35`
- **B14** `update_payroll` recalcula el neto sobre `base_salary` en vez de `gross_salary` y no actualiza devengos. `agents/hr/_payroll_crud.py:98`
- **B15** El agente HR re-implementa CRUD/aprobación de nómina contra la BD (viola límites de capa). `agents/hr/_payroll_crud.py:49`
- **B16** `auto_reconcile` marca la factura 'paid' pero **NO genera el asiento de cobro** (la manual sí) → contabilidad incompleta. `services/banking/service.py:448`
- **B17** Comparación `timestamptz` vs `date` sin `func.date()`: se pierden facturas del último día del periodo; incoherente con `aggregation.py`. `services/analytics/dashboard.py:123`
- **B18** `deduct_fefo` deduce lotes ignorando el almacén: una venta puede vaciar lotes de OTRO almacén. `services/inventory/lot_service.py:111`
- **B19** El stock del almacén por defecto puede quedar **negativo silenciosamente** (sin clamp a 0). `services/inventory/stock_service.py:101`
- **B20** Revertir un albarán confirmado restaura el agregado pero **NO recrea los lotes** deducidos por FEFO. `services/sales/commands.py:606`
- **B21** La previsualización OCR (confirm=False) lee claves inexistentes → siempre muestra todo en blanco / «no detectado». `agents/documents/tools.py:128`

### 🟢 LOW

- **B22** Tres implementaciones divergentes de creación/edición de nómina (servicio + 2× agente). `agents/hr/_payroll_calc.py:71`
- **B23** Modelo 347 hace N+1 por factura (reclasificado de fuga-demo a performance). `services/reports/modelos_aeat.py:151`

---

## C. Veredictos de flujo de datos ERP (todos **PARCIAL**)

- **Factura→libros:** creación/numeración/cadena VeriFactu = correcto y robusto. Se rompe en: analítica/modelos no excluyen borradores; y B2 (edición desincroniza la huella).
- **Nómina:** cálculo y gating de aprobación correctos; se rompe en la propagación a contabilidad (el asiento PGC se crea en estado 'draft', antes de aprobar) + B4/B12/B14.
- **Analítica/dashboard:** esqueleto correcto (tenant, demo, div/0, redondeo); se rompe en las agregaciones de ingreso (B8 rectificativas + B17 fechas).
- **Banca→tesorería:** signos y no-doble-aplicación correctos; se rompe en el matching (B6) y en B16 (auto_reconcile sin asiento).
- **Modelos AEAT:** aislamiento/demo/casillas mayormente correctos; se rompe en 2 puntos del 303 + B9/B10 (dry-run falso).
- **Errores/orquestación:** correcto para lecturas y creates que pasan por `_run_graph_agent→detect_failure`; el resto sin verificar (límite de sesión).

---

## D. Plan de arreglo sugerido (por prioridad)

1. **Línea roja AEAT (B9/B10)** — el justificante simulado no debe parecer real. Riesgo legal.
2. **Asiento de cobro duplicado (B1/B5) + auto_reconcile sin asiento (B16)** — corrompen la contabilidad.
3. **Síntomas de uso A1–A4** (alertas RLS, aprobaciones, borrado de tareas, horarios) — bloquean el día a día.
4. **Analítica (B8/B17/A6)** — cifras erróneas en el panel.
5. **Inventario (B18/B19/B20)** y **VeriFactu en edición (B2/B11)**.
6. **Deuda de diseño** (B13/B14/B15/B22 — el agente habla con la BD saltándose la capa de servicios; es la causa común de la mitad de los bugs fiscales).

---

## E. Actualización 2026-06-25 — barrera fiscal del agente

- **B2 ✅ cerrado** — `agents/billing/_invoice_write_tools.py::_update_invoice_async`:
  (a) si la factura ya tiene `VerifactuRecord`, el agente RECHAZA cambiar base/IVA
  y exige rectificativa (mismo invariante que `delete_invoice`); (b) cuando no hay
  registro, recalcula con `compute_invoice_totals` (Decimal), no float crudo.
- **B11 ✅ cerrado** — `_update_invoice_status_async` delega en
  `services/state_machine.validate_transition("Invoice", …)`; se elimina la tabla
  duplicada que permitía `paid → cancelled` y que ignoraba el estado `sent`.
- Regresión: `tests/test_agent_invoice_barrier.py` (5 tests, en verde).
- **A4 (horarios IA): ya estaba resuelto** — el schema `employee_ids` es opcional y
  la ruta `/schedules/ai-suggest` cae a "todos los empleados activos" cuando no se
  envían IDs; el frontend manda `instruction` y aplica `suggestions`. No requería cambio.
- Pendiente de raíz: B13/B14/B15/B22 (el agente sigue tocando la BD saltándose la
  capa de servicios en HR/contabilidad); B12 (asiento de nómina, falla ruidoso) y
  B20 (revertir albarán no recrea lotes FEFO).
