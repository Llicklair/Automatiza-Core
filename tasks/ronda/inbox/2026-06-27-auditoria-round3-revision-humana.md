# Auditoría round3 /forja (29 prod + 22 tests) — hallazgos para revisión humana

Fecha: 2026-06-27
Origen: auditoría adversarial 4 lentes (info-leak/authz, idempotencia/locks,
timeouts/caps, cobertura) sobre la tanda sin commitear. AST OK 51/51.
Veredicto global: buena tanda, nada bloqueante. Commiteada tal cual.

## Pendientes (NO auto-fix sin tu criterio)

### #1 — Catchup scheduler: TOCTOU + comentario sobre-afirma · MEDIA · concurrencia
`workers/tasks_scheduler.py:310` (`already_executed`) + `:144/:177` (`mark_executed`).
El guard es check-then-act y `mark_executed` corre al FINAL del dispatch. El comentario
(:299-307) promete proteger "deploy rolling con dos instancias vivas a la vez" → FALSO:
dos arranques concurrentes pasan ambos el check, ambos despachan, ambos marcan después.
El test `test_catchup_idempotency.py` solo cubre el caso secuencial.
Fix real: claim-first (mark ANTES del dispatch, con PK constraint que aborte el 2º).
Toca semántica de reintentos → revisar.

### #2 — Reconcile sin lock de fila · MEDIA · concurrencia · FIX 1 LÍNEA
`services/banking/service.py:164-183`. El SELECT de `BankTransaction` no tiene
`with_for_update()`. Dos `reconcile_transaction` concurrentes leen `unreconciled`, ambos
pasan; el asiento duplicado lo frena `_has_entry`, pero la re-asociación de
`tx.invoice_id` a otra factura NO está protegida. Fix: añadir `.with_for_update()` al
select de la tx. Bajo riesgo, alta recomendación.

### #3 — Provisioning AgentSkill delete+insert sin UNIQUE · BAJA · concurrencia
`services/ai/employee_provisioning.py:249`. Sin `UNIQUE(employee_id, tool_module)` el
patrón es idempotente solo secuencialmente; dos tareas BG concurrentes pueden duplicar.
Fix real: constraint UNIQUE (migración).

### #4 — marketing.add_account filtra detalle del error · BAJA · info-leak
`routes/marketing.py:392`: `raise HTTPException(400, detail=f"...{e}")`. El barrido
no_leak arregló connect/disconnect (502) pero olvidó este hermano (400). `e` es
`ZernioError` (mensaje curado, no stacktrace) → BAJA. Patrón "instancia, no clase".

## Notas de calidad (no defectos)
- `services/sales/pos.py`: el hunk es SOLO docstring; admite que la race simultánea de
  `reference` POS sigue SIN arreglar (no hay UNIQUE). No es un fix. Commiteado igual.
- Sin test: `services/integration/service.py`, `migration/holded_client.py`,
  `email/credentials.py` (timeouts reales pero sin cobertura; b2/oauth sí tienen).

## Recordatorio de proceso
Patrón recurrente: comentarios de "idempotencia/multi-instancia" sobre guards
check-then-act sin lock ni UNIQUE (#1, #3). Los que calibran bien la afirmación son los
que usan `with_for_update()` real (purchase_receiving, stock_service, scanner) o que
admiten honestamente la limitación (pos.py). Para el loop: que ningún comentario nuevo
prometa garantía concurrente que un SELECT-then-act no puede dar.
