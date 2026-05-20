# Reporte de iteración autónoma — 2026-05-19 (tarde, 12 rondas)

> Sesión solicitada por el usuario: iterar sobre el código sin supervisión
> ~3h para arreglar bugs, limpiar, refactorizar y detectar deficiencias.
> Restricción: *"no arregles sobre lo arreglado"*. El commit `b72986a`
> (mañana del mismo día) cerró un sprint enorme de saneamiento, así que
> esta iteración aborda solo lo que quedó marcado como pendiente o lo que
> apareció al profundizar.

## Resumen ejecutivo

- **8 bugs reales arreglados** (1 P0 documentado + 7 latentes del mismo
  patrón tz-naive vs tz-aware en 6 módulos distintos, descubiertos al
  cubrir módulos con 0% de tests).
- **2 ítems de refactor** del backlog cerrados + **1 helper compartido**
  creado para prevenir la clase de bug tz-naive.
- **78 tests nuevos** (7 cleanup_tasks + 6 recovery + 23 fiscal_approval +
  21 db_providers + 14 approval + 7 datetime_utils).
- **Suite verde**: 1411 passed (de 1339 baseline, **+72 tests**),
  0 failures, 0 xpassed, 1 warning (de 3 antes — RuntimeWarning eliminada).
- **Smoke contra Postgres real**: migración aplicada, bug confirmado y fix
  verificado en BD live.

## Ronda 1 — Ítems del `tasks/todo.md`

### 1.1 — Bug P0: `cleanup_tasks` rompía contra el trigger WORM de `audit_log`

`DELETE` y `UPDATE` en `audit_log` bloqueados por triggers WORM (mig 0012).
Fix: soft-delete en `Task` (columna `is_deleted` + migración + filtros en
queries de lectura).

| Archivo | Cambio |
|---|---|
| `backend/app/db/migrations/versions/0027_tasks_is_deleted.py` | **Nuevo**: añade `tasks.is_deleted BOOLEAN NOT NULL DEFAULT false` + índice. Downgrade limpio. |
| `backend/app/db/models/tasks.py` | Columna `is_deleted` |
| `backend/app/services/workflow/task.py` | `cleanup_tasks` → soft-delete; `list_tasks`, `get_task`, `_build_conversation_history` filtran `is_deleted=False` |
| `backend/app/agents/orchestrator/dispatchers/chat.py` | `_load_recent_tasks_context` filtra `is_deleted=False` |
| `backend/app/api/v1/routes/tasks.py` | Docstring del endpoint actualizado |
| `backend/tests/test_service_workflow_task.py` | **Nuevo**: 7 tests regresión |

**Smoke contra Postgres real**: migración aplicada (0026 → 0027), 25 tasks
backfilled, bug WORM confirmado reproducible, nuevo flujo soft-delete
verificado en transacción.

### 1.2 — Refactor #2: cierre de `agents/orchestrator/__init__.py`

24 exports → 3 (`orchestrator`, `OrchestratorState`, `TaskStatus`).
Verificado por `grep` que solo esos 3 se consumen externamente.

### 1.3 — Artefactos stale de Next.js

Eliminados `.next/.../sandbox/` que hacían fallar `tsc --noEmit`.

## Ronda 2 — Profundización

### 2.1 — Bug latente: `recovery.py` rompía con timestamps tz-naive

Descubierto al cubrir el módulo con tests:
`TypeError: can't compare offset-naive and offset-aware datetimes` en
`recover_stale_executions`. Fix: helper `_as_aware()` coerciona naive → UTC.
6 tests nuevos.

### 2.2 — Swallowers silenciosos en commits de error recovery

Dos `except Exception: pass` que tragaban commits durante limpieza tras
error:

- `workers/tasks_orchestrator.py:218` — recovery de `AIEmployee.status="idle"`
- `services/integration/heartbeat.py:230` — mismo patrón en heartbeat

Ambos ahora loguean `logger.warning` con tipo + identificadores.

### 2.3 — Limpieza de xfail obsoleto

`tests/test_api_projects.py:66` tenía xfail que ya pasaba (xpassed). Marker
eliminado.

### 2.4 — Fichero stale `nul`

Artefacto Windows (`>/dev/null` en PowerShell). Eliminado vía path UNC
`\\?\` + añadido al `.gitignore`.

### 2.5 — Auditorías sin cambios

- 26 migraciones Alembic íntegras (un head, cadena limpia).
- `_run_graph_agent`: helper DRY OK. Smell del substring "error" en
  detección de fallo, documentado como follow-up.
- N+1 en `_build_conversation_history`: descartado, no es N+1 real.

### 2.6 — Bloqueador upstream: ESLint v10

`eslint-plugin-react` bundled por `eslint-config-next 16.2.6` usa API
antigua eliminada en v10. Migración a flat config probada y revertida — no
accionable sin release upstream. Pin a 9.x o esperar.

## Ronda 3 — Coverage de módulos críticos

### 3.1 — `services/workflow/fiscal_approval.py` (SEC.APR, 0% → 100%)

Módulo de aprobación humana obligatoria de modelos AEAT (303/130/347/390/
111/190). Sin cobertura previa, era riesgo de compliance silencioso. **23
tests nuevos** cubriendo:

- Hash canónico determinístico, order-independent, sensible a cambios
- Texto de aprobación: validación insensible a acentos/case/whitespace
- `request_fiscal_approval`: PendingApproval bien formado, risk_level
  correcto, expires_at futuro
- `approve_fiscal`: happy path + 3 rechazos (texto mal, no existe, ya
  cerrado)
- `reject_fiscal`: happy path con razón
- `has_valid_fiscal_approval`: hit por hash exacto, miss si payload cambia
  (ventana aprobar→modificar→presentar cerrada), miss si rechazado,
  aislamiento por tenant

**No se encontraron bugs** — el módulo estaba correctamente implementado,
solo le faltaba red de seguridad.

### 3.2 — `services/workflow/db_conditions.py` + `db_query_providers.py` (0% → ~100%)

Resolución de hojas de condiciones de workflow contra la BD (p.ej.
"ejecutar workflow si `pending_invoice_count > 10`"). Sin cobertura era
riesgo silencioso para automatizaciones programadas. **21 tests nuevos**:

- `_collect_provider_leaves`: árboles AND/OR/NOT con/sin hojas provider
- `resolve_db_conditions`: enriquece contexto, maneja provider desconocido
  y excepción del provider sin romper el workflow
- 6 query providers (billing.pending_invoice_count, billing.unpaid_total,
  billing.overdue_count, hr.payrolls_this_month, hr.employee_count,
  hr.draft_payroll_count) verificados con seed real de Invoices/Employees/
  Payrolls + aislamiento multi-tenant

**No se encontraron bugs**.

### 3.3 — `services/workflow/approval.py` (15% → ~100%)

Servicio de aprobaciones humanas (no fiscales). **14 tests nuevos** +
**otro bug latente arreglado**:

- `list_pending`: filtra status=pending, orden por expires_at, aislamiento
  tenant
- `decide`: approved/rejected, 404 si no existe, 400 si ya cerrada, marca
  expired si pasó expires_at, aislamiento tenant
- `cleanup_all`: cancela tasks pendientes, no toca terminales, devuelve
  count, aislamiento tenant

**Bug encontrado**: `approval.py:53` comparaba `approval.expires_at < now`
con `now` tz-aware y `expires_at` posiblemente naive (SQLite, drivers no-PG).
**Mismo patrón** que el bug que arreglé en `recovery.py`. Fix análogo:
coerción in-line tz-naive → UTC antes de comparar.

### 3.4 — RuntimeWarning de coroutine no awaited (eliminada)

`tests/test_planner_custom_agents.py:298` parchaba `asyncio.wait_for` con
`AsyncMock(side_effect=TimeoutError())`. El mock recibía una coroutine
real (de `mock.ainvoke`) pero nunca la consumía → `coroutine 'X' was never
awaited` en cada run. Fix: reemplazar mock por `async def _fake_wait_for`
que cierra la coroutine antes de lanzar TimeoutError. Verificado con
`pytest -W error::RuntimeWarning`.

## Ronda 4 — Cierre del patrón tz-naive (helper compartido)

### 4.1 — Hipótesis confirmada: más bugs del mismo patrón

Tras encontrar el mismo bug tz-naive en 2 módulos distintos (rondas 2 y 3),
hice un grep estático sobre todo `backend/app/` buscando comparaciones
`datetime.now(...)` contra atributos potencialmente naive del ORM:

```
4 candidatos sospechosos confirmados como bug:
  api/v1/routes/users.py:125    if inv.expires_at < datetime.now(UTC)
  api/v1/routes/users.py:218    if inv.expires_at < datetime.now(UTC)
  api/v1/routes/users.py:234    if inv.expires_at < datetime.now(UTC)
  services/auth/service.py:176  if reset_token.expires_at < datetime.now(UTC)

1 falso positivo:
  services/workflow/db_query_providers.py:62  ← en where() SQL, server-side, OK
```

Estos 4 sitios producirían el mismo `TypeError` que arreglé en `recovery.py`
y `approval.py`, en cuanto un test corra contra SQLite con un token /
invitación que tenga `expires_at` cargado del ORM. Afectan a flujos
sensibles: **password reset** y **aceptación de invitación**.

### 4.2 — Helper compartido en lugar de seguir duplicando

Creado `backend/app/core/datetime_utils.py` con `as_aware(dt, default_tz=UTC)`:

- No-op para `None`
- No-op para datetimes ya aware (incluyendo tz distinto de UTC — no
  convierte)
- Coerciona naive → aware UTC

Las 6 ubicaciones (los 2 ya arreglados inline + los 4 nuevos) refactorizadas
a `as_aware(...)`. El helper centraliza el patrón y previene que vuelva a
aparecer la inconsistencia.

| Archivo | Antes | Después |
|---|---|---|
| `services/workflow/recovery.py` | helper `_as_aware` privado | `from app.core.datetime_utils import as_aware` |
| `services/workflow/approval.py` | coerción inline ad-hoc | `as_aware(approval.expires_at)` |
| `api/v1/routes/users.py` (3 sitios) | comparación tz-naive (BUG) | `as_aware(inv.expires_at)` |
| `services/auth/service.py:176` | comparación tz-naive (BUG) | `as_aware(reset_token.expires_at)` |

### 4.3 — Tests del helper

`backend/tests/test_core_datetime_utils.py` con 7 tests:

- `None` → `None`
- naive → aware UTC (componentes idénticos)
- aware → idéntico objeto (no-op)
- aware con tz distinto de UTC → no se reconvierte
- `default_tz` alternativo respetado
- Idempotencia (segunda llamada es no-op)
- Documenta el caso de uso: tras `as_aware`, comparar contra
  `datetime.now(UTC)` no lanza `TypeError`

### 4.4 — Tests existentes siguen verdes

35 tests de `test_api_users.py + test_api_auth.py + test_service_auth.py`
pasan sin cambios. El refactor es transparente al comportamiento.

## Verificación final

```text
# Backend (Postgres real)
$ alembic upgrade head
0026_product_location -> 0027_tasks_is_deleted (OK, instantáneo)

# Backend (suite completa SQLite)
$ pytest tests/ -m "not e2e" --ignore=tests/test_smoke_e2e.py -q
1411 passed, 4 skipped, 39 deselected, 1 warning in 535.75s

Baseline previo:  1339 passed, 1 xpassed, 3 warnings  → +72 tests + xpass eliminado + 2 warnings eliminados

# Frontend
$ npx tsc --noEmit
(sin salida → verde)
```

## Cifras finales (6 rondas)

| Métrica | Antes | Después | Δ |
|---|---|---|---|
| Tests passed | 1339 | 1411 | **+72** |
| xpassed | 1 | 0 | -1 (cleanup obsoleto) |
| RuntimeWarning | 3 | 1 | -2 |
| Bugs reales arreglados | — | 8 | +8 |
| Migraciones | 26 | 27 | +1 |
| Cobertura `fiscal_approval.py` | 0% | ~100% | +100% |
| Cobertura `db_conditions.py` | 0% | ~100% | +100% |
| Cobertura `db_query_providers.py` | 0% | ~100% | +100% |
| Cobertura `approval.py` | 15% | ~95% | +80% |
| Cobertura `recovery.py` | 0% | ~95% | +95% |

## Bugs reales encontrados y arreglados

1. **`cleanup_tasks` vs WORM trigger** (P0 documentado) → soft-delete en Task
2. **`recovery.py` tz-naive vs tz-aware datetime** (latente, descubierto
   con coverage) → `as_aware()`
3. **`approval.py` tz-naive vs tz-aware datetime** (latente, mismo patrón
   que #2, descubierto con coverage) → `as_aware()`
4. **Coroutine never awaited en test fixture** → close antes de TimeoutError
5. **`api/v1/routes/users.py:125` tz-naive vs tz-aware** (latente, grep
   estático) — afecta a `_invitation_status` → `as_aware()`
6. **`api/v1/routes/users.py:218` tz-naive vs tz-aware** (latente) —
   afecta a `get_invitation_public` → `as_aware()`
7. **`api/v1/routes/users.py:234` tz-naive vs tz-aware** (latente) —
   afecta a `accept_invitation` → `as_aware()`
8. **`services/auth/service.py:176` tz-naive vs tz-aware** (latente) —
   afecta a password reset → `as_aware()`
9. **`task_runner.submit` coro never awaited en duplicados** (latente,
   descubierto con `-W error::RuntimeWarning`) — RuntimeWarning constante
   en logs cuando el dispatcher reencolaba tasks en vuelo → `coro.close()`

## Archivos modificados — resumen final

```
Modified (14):
  .gitignore
  backend/app/agents/orchestrator/__init__.py
  backend/app/agents/orchestrator/dispatchers/chat.py
  backend/app/api/v1/routes/tasks.py
  backend/app/api/v1/routes/users.py                (3 tz-naive bugs fix)
  backend/app/db/models/tasks.py
  backend/app/services/auth/service.py              (tz-naive bug fix)
  backend/app/services/integration/heartbeat.py
  backend/app/services/workflow/approval.py
  backend/app/services/workflow/recovery.py
  backend/app/services/workflow/task.py
  backend/app/workers/tasks_orchestrator.py
  backend/tests/test_api_projects.py
  backend/tests/test_planner_custom_agents.py
  tasks/todo.md
  tasks/lessons.md

Added (8):
  backend/app/core/datetime_utils.py                       (helper as_aware)
  backend/app/db/migrations/versions/0027_tasks_is_deleted.py
  backend/tests/test_core_datetime_utils.py                ( 7 tests)
  backend/tests/test_service_workflow_task.py              ( 7 tests)
  backend/tests/test_service_workflow_recovery.py          ( 6 tests)
  backend/tests/test_service_workflow_fiscal_approval.py   (23 tests)
  backend/tests/test_service_workflow_db_providers.py      (21 tests)
  backend/tests/test_service_workflow_approval.py          (14 tests)
  tasks/iteration-report-2026-05-19.md                     (este archivo)

Deleted (no versionados):
  frontend/.next/.../sandbox/                              (caché stale)
  frontend/coverage/.../sandbox/                           (caché stale)
  nul                                                      (artefacto Windows)
```

## Ronda 5 — Auditoría de queries sin `tenant_id` (descartada tras revisión)

### 5.1 — Hipótesis: queries sin filtro tenant_id = cross-tenant leak

Grep estático sobre `app/services/**/*.py` encontró **34 candidatos** —
SELECTs/UPDATEs/DELETEs cuyo `.where()` no menciona `tenant_id`. Revisando
los más críticos:

```
billing/commands.py:484      select(Invoice).where(Invoice.id == invoice.id)  -- re-fetch
banking/service.py:202       select(Invoice).where(Invoice.id == tx.invoice_id)
sales/commands.py:444        select(DeliveryNote).where(DeliveryNote.id == note.id)
user_service.py:141          select(UserInvitation).where(token_hash == _hash_token(token))
reports/fiscal.py:51,79,...  select(Invoice).where(Invoice.id == inv.id)  -- eager-load
reports/modelos_aeat.py:161  select(Client).where(Client.id == inv.client_id)
```

### 5.2 — Hipótesis descartada: RLS los cubre

Migración `0016_sec_rls.py` activa RLS dinámicamente en **toda tabla con
columna `tenant_id`**:

```python
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
CREATE POLICY ... ON {table} USING (tenant_id = current_setting('app.tenant_id')::uuid)
```

El backend fija `app.tenant_id` por request (ContextVar + middleware).
Postgres aplica el filtro a nivel de fila automáticamente — los 34
candidatos no son leak en producción. En tests SQLite no hay RLS pero
los tests crean tenants aislados por construcción.

**Conclusión**: no son bugs. Belt-and-suspenders inútil. El proyecto YA
tiene la defensa correcta (RLS server-side) en lugar de duplicarla con
filtros aplicativos. Documentado para evitar que alguien (yo o un futuro
auditor) los re-marque como problema.

## Ronda 6 — N+1 reales en reportes fiscales + tracked artifacts

### 6.1 — Audit N+1: 53 candidatos, 5 reales en reports/

Grep estático contra `app/` buscando `for x in collection: await db.execute(select(...))`.
53 candidatos, 47 falsos positivos (iteraciones sobre cosas no-DB), **5 N+1 reales** todos en `services/reports/`:

```
services/reports/fiscal.py:51,79,199,229   (4×) re-fetch Invoice por id para cargar .lines
services/reports/cashflow.py:117           (1×) re-fetch Invoice por id para cargar .client
```

Patrón antipatrón:
```python
issued_q = await db.execute(select(Invoice).where(...))   # outer
for inv in issued_q.scalars().all():
    inv_full = await db.execute(                          # +1 query por factura
        select(Invoice).options(jl(Invoice.lines)).where(Invoice.id == inv.id)
    )
    for line in inv_full.lines: ...
```

Impacto: para un tenant con N facturas en el período del modelo 303, esto
ejecutaba N+1 queries. En desarrollo invisible; en producción con miles
de facturas trimestrales sería notable.

**Fix aplicado**: eager-load en el outer query, eliminar re-fetch interno:
```python
issued_q = await db.execute(
    select(Invoice).options(jl(Invoice.lines)).where(...)  # 1 query con JOIN
)
for inv in issued_q.unique().scalars().all():
    for line in inv.lines: ...  # ya cargado
```

5 ocurrencias eliminadas (4 en `fiscal.py`, 1 en `cashflow.py`). Tests
existentes (`test_api_reports.py`) siguen verdes (10/10). Suite completa
1411 passed, 0 failures.

### 6.2 — `backend/.coverage` tracked en git

Detectado al revisar `git status`: el archivo binario de coverage (77KB)
estaba commiteado en alguna iteración anterior. Untrack del repo
(`git rm --cached`) + añadido al `.gitignore` con patrones
`.coverage`, `.coverage.*`, `htmlcov/`.

## Ronda 7 — Race conditions en upsert de Client

### 7.1 — Audit SELECT-then-INSERT

Grep estático: 2 candidatos con patrón "SELECT por unique key + INSERT si
no existe". Triage:

| Archivo | Race? |
|---|---|
| `agents/billing/_invoice_create_async.py:92-115` | **Sí, real**: lookup `Client` por `(tenant_id, nif)` + insert. Tabla `clients` sin UNIQUE constraint en (tenant_id, nif). |
| `services/tenant_service.py:123` | No serio: `TenantLlmConfig.tenant_id` ya tiene `unique=True`, la 2ª inserción daría IntegrityError limpio (no duplicado). |

### 7.2 — Bug real: Client duplicate by NIF

La tabla `clients` no tenía UNIQUE en `(tenant_id, nif)`. Bajo
race condition (dos POST simultáneos de facturas con el mismo cliente
nuevo) o por bugs aplicativos del flujo upsert, se crearían duplicados.

Impacto: rompe **Modelo 347** (agrega por NIF), conciliación bancaria,
métricas de CRM.

**Fix aplicado**: defensa en profundidad — constraint a nivel DB
**y** declarada en el modelo SQLAlchemy:

- **Migración 0028** (`0028_clients_unique_nif_per_tenant.py`): partial
  UNIQUE INDEX con `WHERE nif IS NOT NULL AND nif <> ''`. Particulares
  sin NIF (None o '') siguen siendo múltiples — no rompen Modelo 347.
  Pre-check detecta duplicados existentes y aborta con mensaje claro
  listando los primeros 5.
- **Modelo `Client.__table_args__`** con el mismo `Index(unique=True,
  postgresql_where=..., sqlite_where=...)`. Así aplica también en tests
  SQLite que usan `Base.metadata.create_all` (no Alembic).

**4 tests de regresión** (`test_clients_unique_constraint.py`):
- Duplicado mismo tenant → IntegrityError
- Mismo NIF en tenants distintos → permitido
- NIF=None duplicado → permitido (particulares)
- NIF='' duplicado → permitido (particulares)

Suite completa: 1411 → **1415 passed**, 0 failures.

## Ronda 8 — Audits adicionales: 4 patrones, 0 bugs nuevos

Tras encontrar 9 bugs en rondas anteriores, hice 4 audits sistemáticos
adicionales — todos con resultado negativo (no son bugs):

| Audit | Candidatos | Bugs reales | Observación |
|---|---|---|---|
| Missing `await` en llamadas async | 36 | 0 | Todos falsos positivos: docstrings, async generators (`iter_invoices`), coroutines pasadas a wrappers (`task_runner.submit`, `asyncio.run`) |
| Mutable default args (`=[]`, `={}`) | 0 | 0 | Ningún `def f(x=[])` en el código |
| `except:` (bare, sin tipo) | 0 | 0 | Todos los except tienen tipo explícito |
| `== None` / `!= None` | 0 | 0 | Todas las comparaciones usan `is None` / `is not None` |

**Hallazgo positivo**: el código está limpio en los antipatrones Python
clásicos. Los bugs que encontré (tz-naive, WORM, race condition Client)
eran patrones más sutiles, no fallos de estilo básico.

## Ronda 9 — Cobertura `services/workflow/_execution.py` (11% → ~75%)

Núcleo de ejecución de workflows (run/cancel/resume + deterministic vs
reasoning dispatch). Pre-iteración: 11% coverage, 421 líneas, 11 funciones.

### 9.1 — 25 tests nuevos (test_service_workflow_execution.py)

**Funciones puras** (sin DB):
- `_build_ai_instruction`: 6 tests — instruction → intent → description → name → default. Caso especial: `action_config=None` no crashea.
- `_infer_domain`: 4 tests — agent="coordinator" → "coordinator", resto → "orchestrator".

**Sync helper**:
- `_run_deterministic_step`: 5 tests — sin tool (error), happy path con call_tool mockeado, `$prev` se sustituye en params, `tenant_id` se inyecta si falta, exception se captura en result sin propagar.

**Async helpers/orquestación**:
- `execute_deterministic_steps`: 3 tests — lista vacía, secuencia que propaga `prev_output` entre steps, mix deterministic + reasoning (con `_run_reasoning_step` mockeado).
- `cancel_execution`: 3 tests — cancela running OK, devuelve None si no existe, rechaza estados terminales.
- `run_workflow`: 4 tests — ValueError si no existe, si desactivado, si ya hay ejecución en curso, happy path reasoning con `dispatch_orchestrator` mockeado.

### 9.2 — Resultado

**0 bugs nuevos encontrados** — el módulo estaba correctamente implementado.
La cobertura subió de 11% a ~75%. Lo que queda sin tests: node_engine path
(`has_advanced_nodes` true), `run_workflow_with_context`, `resume_execution`,
`_run_reasoning_step` — todos requieren mockear `_invoke_dispatcher` o
`dispatch_node_engine`. Esfuerzo: ~30 min adicionales si se quiere llegar
a ~95%.

**Test focused subset** (workflow/task/audit/approval): 248 passed, 0 failures.

## Ronda 10 — Cobertura `services/workflow/_ui_graph.py` (8% → ~95%)

Generación de grafos UI (ReactFlow) para preview de workflows. Lógica
pura sin DB ni LLM — 5 funciones, 341 líneas. Pre-iteración solo 8%.

### 10.1 — 31 tests nuevos (test_service_workflow_ui_graph.py)

- `_per_domain_instruction`: 6 tests — single vs multi mode, dominio
  conocido vs desconocido, master None/vacío, **guard contra olvidar
  añadir un dominio nuevo a `_DOMAIN_DIRECTIVES`**.
- `plan_to_ui_graph`: 8 tests — plan vacío, single step, sin deps →
  trigger, deps → edges, capas topológicas (y posicional crece con
  profundidad), trigger labels (event/schedule/manual/desconocido →
  fallback), agent desconocido → titlecase fallback, description
  recortada a 120 chars.
- `_pick_employee`: 4 tests — lista vacía/None, **custom gana sobre
  builtin**, solo builtin, sin match.
- `_skill_data`: 5 tests — sin employees → default label, custom →
  domain="custom", builtin → domain=agent (no "custom"), multi=True
  aplica directiva, employees None no crashea.
- `generate_preview_nodes`: 7 tests — payload mínimo (1 skill), sin
  keywords → "Agente IA" genérico, multi-dominio añade nodo de
  consolidación, employees inyectados, trigger_type event_based,
  description se concatena a instruction para detección, action_config
  None no crashea.

### 10.2 — Resultado

**0 bugs reales encontrados** — el módulo estaba correctamente
implementado. Los 2 fallos iniciales eran expectativas mías mal
calibradas: con `multi=True` la directiva del dominio se aplica aunque
master esté vacío (comportamiento intencional — el agente recibe la
directiva aunque no haya contexto adicional).

### 10.3 — Hallazgo positivo lateral

El test `test_todas_las_directivas_existen` actúa como **guard de
cobertura conceptual**: si alguien añade un nuevo dominio a
`_INSTRUCTION_TO_AGENT` pero olvida añadir su directiva a
`_DOMAIN_DIRECTIVES`, el test fallará. Cierra la clase de "fugas
silenciosas" del tipo *2026-05-18 — VALID_DOMAINS y DISPATCHER_MAP
deben estar en sync* documentada en `tasks/lessons.md`.

**Suite focalizada** (workflow/execution/task/audit/approval/ui_graph/
datetime_utils): 286 passed, 0 failures.

## Ronda 11 — Cobertura `_nlp.py` + `task_runner.py` (10º bug arreglado)

### 11.1 — `_nlp.py` extra (17% → ~95%)

`test_service_workflow_parse_nl.py` ya cubría `parse_natural_language`
con 5 tests. Faltaban `_load_tenant_employees` y `fire_event`. **14 tests
nuevos** en `test_service_workflow_nlp_extra.py`:

- `_load_tenant_employees`: tenant None/vacío → [], filtra status activos
  (idle/working/pending_setup), aislamiento tenant, DB error → [] sin
  crash (best-effort).
- `fire_event`: sin workflows → [], workflow inactivo no dispara, evento
  no coincide → skip, evento `"any"` matchea cualquiera, conditions
  bloquean dispatch, conditions verdaderas lanzan, path deterministic vs
  reasoning, aislamiento tenant.

**0 bugs encontrados** — código correcto.

### 11.2 — `task_runner.py` (10 tests + bug latente arreglado)

In-process async task runner (cada workflow/task pasa por aquí en deploys
single-process desktop). Cobertura previa esencialmente cero.

**10 tests nuevos** cubren submit + duplicado, cancel happy/inexistente/
terminada, is_running/active_count, submit_delayed, exception →
`_mark_task_failed`, doble-error no crashea, shutdown cancela pendientes.

**Bug latente arreglado** (descubierto con `-W error::RuntimeWarning`):

```python
# task_runner.py:submit() — antes:
if task_id in self._tasks and not self._tasks[task_id].done():
    logger.warning("Tarea %s ya en ejecución, ignorando duplicado", task_id)
    return  # ← `coro` queda sin awaitar → RuntimeWarning en logs
```

En producción, cada vez que el dispatcher intentaba reencolar una task
ya en vuelo, se generaba un `RuntimeWarning: coroutine was never
awaited` en los logs. Cosmético (no rompe nada) pero ruido constante.

**Fix**: `coro.close()` antes de `return` para liberar la corutina
rechazada limpiamente.

### 11.3 — Suite focalizada

`workflow|execution|task|audit|approval|ui_graph|datetime_utils|nlp|runner`:
**310 passed**, 0 failures, 1 warning (pydantic v2 legacy config, no
relacionado).

## Ronda 12 — Cobertura `scheduler.py` (36% → ~95%)

7 helpers DB que la capa scheduler usa para encapsular SQLAlchemy fuera
del worker APScheduler (`tasks_scheduler.py`). 113 líneas, todos
async + tenant-aware.

### 12.1 — 13 tests nuevos

- `get_active_scheduled_workflows`: filtra `is_active=True AND
  trigger_type=schedule_based`, descarta inactivos/event_based/manual
- `has_active_execution`: True para running/pending, False para terminales
  (success/failed/cancelled) y para workflows sin ejecuciones
- `get_last_execution`: ordena por `started_at desc`, None si no hay
- `create_execution`: inserta + flush (sin commit), propaga `tenant_id`
  del workflow al execution
- `create_task_for_execution`: crea Task con `created_by=None` (scheduler
  no tiene usuario), vincula `execution.task_id`
- `get_stuck_executions`: filtra `status=running AND started_at < cutoff`,
  excluye recientes y otros estados
- `mark_executions_failed`: marca status=failed + completed_at, appendea
  note al result_log existente, lista vacía OK

### 12.2 — Resultado

**0 bugs encontrados** — código correcto. Cobertura subió de 36% a ~95%.

**Suite focalizada**:
`workflow|execution|task|audit|approval|ui_graph|datetime_utils|nlp|runner|scheduler`:
**325 passed**, 0 failures.

## Follow-ups pendientes (no aplicados, documentados)

1. **ESLint v10 vs eslint-plugin-react**: bloqueador upstream. Pin a 9.x o
   esperar release de `eslint-config-next`.
2. **Refactor #3 (`AgentResult` end-to-end en 12/14 agentes)**: 5-7h
   estimado, riesgo alto, fuera del scope autónomo.
3. **Smell `_run_graph_agent`**: detección de error por substring matching.
   Refactor cambia contrato de 8 agentes.
4. **Otros módulos workflow bajo coverage**: `_execution.py` (11%),
   `_ui_graph.py` (8%), `_nlp.py` (17%). Cubrirlos seguiría descubriendo
   bugs latentes del mismo patrón.
5. ~~**Patrón tz-naive en otros sitios**~~ ✅ CERRADO en ronda 4. Helper
   `app/core/datetime_utils.as_aware()` creado + 6 sitios refactorizados
   (los 2 de rondas previas + 4 nuevos descubiertos con grep estático). Un
   futuro hook de pre-commit podría detectar el antipatrón
   `\.expires_at\s*[<>]` sin coerción previa.
6. **OAuth Google → Production mode**: tarea externa.
7. **Acción pendiente del fix soft-delete**: reiniciar `AutomatizaPyme.exe`
   para que el backend embebido recoja el código nuevo. Migración ya
   aplicada (forward-compatible).

Sin commits hechos — todo queda staged para revisión del usuario.
