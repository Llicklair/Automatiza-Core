# Cleanup candidates — informe consolidado

- **Fecha:** 2026-06-17
- **Rama:** `chore/cleanup-stale-reports`
- **HEAD del índice GitNexus:** `fc3dd32`
- **Alcance:** 4 tiers (código muerto, imports sin uso, cruft local, índice GitNexus).

> ⚠️ **Lectura obligatoria antes de borrar nada.** Este informe es de ANÁLISIS.
> La consulta GitNexus de TIER 1 detecta helpers `_*` sin aristas `CALLS`/`IMPORTS`/`STEP_IN_PROCESS`
> en el grafo, **pero el grafo no captura llamadas vía registries, dispatch-tables ni
> llamadas intra-fichero de forma fiable**. La validación dinámica por grep (repo completo)
> reclasifica cada candidato. **"ALTA confianza" significa "el nombre no aparece en NINGÚN
> otro fichero", NO "no se usa": un helper llamado solo dentro de su propio módulo o por una
> tabla de dispatch también da 0 apariciones externas.** Hay que abrir el fichero antes de borrar.

---

## Estado de ejecución (2026-06-17)

| Tier | Acción | Estado |
|---|---|---|
| 1 — Código muerto | 2º pase dinámico (grep repo completo, 1617 ficheros) | ✅ Analizado → **TRULY_DEAD = 0**. Ningún borrado. |
| 2 — Imports sin uso (backend) | `ruff check --select F401 --fix backend/` | ✅ **Aplicado** — 20 imports eliminados en 13 ficheros de `backend/tests/` (verificado: solo líneas `import`). |
| 2 — Exports sin uso (`lib/api.ts`) | `npx ts-prune` + workflow (68→30→3) | ✅ **Aplicado** — 68 verificados; 3 confirmados muertos; borrado **1** (`StockMovementResult`), 2 conservados (uso intra-módulo). `tsc` exit 0. |
| 2 — Exports sin uso (`components/`) | workflow Next.js-aware (23→9→6) | ✅ **Aplicado** — 6 confirmados muertos borrados: ficheros `NodeStatusBadge.tsx` + `Skeletons.tsx`, `API_URL`+`authHeaders` (shared.ts), componente `GenerativeUI` (conservado `sanitizeHTML`). `tsc` exit 0. |
| 3 — Cruft local | `rm -rf pytest-of-Marcos/ backend/scripts/_runs/` | ✅ **Aplicado** — 455 KB borrados de disco; git intacto (eran gitignored). |
| 4 — Índice GitNexus | — | Pendiente opcional: el índice referencia algunos ficheros ya borrados; `npx gitnexus analyze` lo refrescaría. |

---

## TIER 1 — Código muerto (helpers privados Python `_*` sin refs en el grafo)

**Resumen:** GitNexus marcó 118 helpers `_*` sin aristas; la validación por grep deja **78 ALTA / 35 REVISAR** (113 únicos tras colapsar duplicados de nombre `_do`/`_tenant`).
**Riesgo:** **MEDIO** (alto riesgo de falsos positivos por registries y llamadas intra-fichero).

### Hallazgo crítico: los 35 REVISAR son casi todos FALSOS POSITIVOS

| Subgrupo | Nº | Veredicto |
|---|---|---|
| Dispatchers `_dispatch_*` registrados en `dispatchers/__init__.py` → `DISPATCHER_MAP` | 16 | **NO BORRAR — vivos** |
| Helpers con refs cruzadas reales (`_resolve_client`, `_run`, `_headers`, `_enqueue_task`, `_build_skill_dispatch`, `_real_tx_filter`, `_sub`, `_on_page`, `_summary`, `_llm_type`) | ~11 | **NO BORRAR — usados** (grafo perdió la arista CALLS entre módulos) |
| `_tenant` (mismo nombre definido en 8 ficheros de test) | 8 | Colisión de nombre, no referencia. Cada uno es local a su test. |

Los `_dispatch_*` aparecen como REVISAR **precisamente porque la validación los salvó**: se importan en
`backend/app/agents/orchestrator/dispatchers/__init__.py`. Borrarlos rompería el orquestador (Coordinador).

### ALTA confianza — 78 helpers (0 apariciones fuera de su fichero)

**Importante:** muchos de estos NO son código muerto, solo no se referencian por nombre desde otro
fichero. Casos típicos a verificar manualmente antes de borrar:
- `_exec_*` (8) en `services/workflow/approval_actions.py` y `_billing_*`/`_hr_*` (6) en `db_query_providers.py` → casi seguro despachados por **diccionario/registry interno** del propio módulo.
- `_fetch_*` (6) en `agents/excel/_fetchers.py` → probable dispatch por tipo de dataset dentro del módulo.
- helpers de `services/ai/node_engine.py` (6), `db/rls.py` (2), `tenant_context.py` (2) → utilidades llamadas dentro de su propio fichero (intra-módulo, el grafo no lo capturó).
- overrides de framework: `_invoke`, `_identifying_params`, `_llm_type`, `_ainvoke_and_parse` (LangChain), `_link_callback`/`_on_page`/`_wrap` (xhtml2pdf/reportlab callbacks) → **invocados por la librería, nunca por nombre**. NO BORRAR.
- `_disable_rls_sql` en una **migración Alembic** → histórico, NO tocar.

#### ALTA — código fuente (53)

| Directorio | Helpers |
|---|---|
| `agents/excel/_fetchers.py` | `_fetch_payrolls`, `_fetch_clients`, `_fetch_invoices`, `_fetch_bank`, `_fetch_products`, `_fetch_employees` |
| `agents/inventory/tools.py` | `_apply` |
| `agents/orchestrator/_core.py` | `_route_after_load_knowledge` |
| `agents/tenant_context.py` | `_async_wrapper`, `_sync_wrapper` |
| `agents/tool_timeout.py` | `_timed` |
| `core/llm/claude_code.py` | `_identifying_params`, `_ainvoke_and_parse`, `_invoke_and_parse` |
| `core/llm/mock.py` | `_invoke` |
| `core/llm_factory.py` | `_try_groq_fallback` |
| `db/migrations/versions/0016_sec_rls.py` | `_disable_rls_sql` (migración — NO tocar) |
| `db/rls.py` | `_rls_set_tenant`, `_rls_reset_cache` |
| `middleware/rate_limit.py` | `_client_ip` |
| `services/ai/node_engine.py` | `_all_leaf_nodes_completed`, `_has_suspended_nodes`, `_get_predecessors`, `_skip_discarded_branch`, `_find_ready_nodes`, `_get_successors` |
| `services/analytics/dashboard.py` | `_dashboard_cache_key` |
| `services/backup/b2_client.py` | `_do` (closure de reintento) |
| `services/banking/service.py` | `_score_match` |
| `services/billing/backfill_verifactu.py` | `_is_backfill_needed` |
| `services/documents/docx_preview.py` | `_wrap` |
| `services/inventory/_fefo.py` | `_fefo_sort_key` |
| `services/migration/wizard.py` | `_validate_preview_for_commit` |
| `services/pdf_reports/_markdown.py` | `_link_callback` (callback lib) |
| `services/system/preconditions.py` | `_check_tables` |
| `services/tenant_service.py` | `_run_cmd` |
| `services/workflow/approval_actions.py` | `_exec_inventory_batch_update`, `_exec_send_email`, `_exec_create_invoice`, `_exec_reconcile_transaction`, `_exec_create_journal_entry`, `_exec_inventory_batch_adjust`, `_exec_approve_payroll`, `_exec_gated_tool_call` |
| `services/workflow/db_query_providers.py` | `_billing_invoice_count_by_status`, `_hr_draft_payroll_count`, `_billing_unpaid_total`, `_hr_employee_count`, `_billing_overdue_count`, `_hr_payrolls_this_month` |
| `backend/scripts/db_drift.py` | `_inspect` |
| `frontend/src/stores/notifications.ts` | `_persistedToLocal` |
| `scripts/generate_market_study.py` | `_style` |

#### ALTA — tests (25)

Helpers locales de test (fixtures/dobles/closures): `conftest.py` (`_visit_JSONB`, `_patch_bigint_for_sqlite`, `_override_get_db`), y dobles/closures en `test_orchestrator_dispatch.py`, `test_analytics_events.py`, `test_cache.py`, `test_compliance_business.py` (`_none`,`_boom`), `test_idempotency_guard.py`, `test_inventory_agent.py`, `test_onboarding_wizard.py` (`_fake_ready`,`_fake_not_ready`), `test_planner_custom_agents.py` (`_hangs`,`_fake_wait_for`), `test_recruitment_business.py` (`_text`,`_raise`,`_empty`,`_llm_down`), `test_request_context.py`, `test_service_workflow_approval.py` (`_ctx`), `test_service_workflow_db_providers.py` (`_broken`), `test_service_workflow_fiscal_approval.py` (`_tenant_user_task`), `test_service_workflow_parse_nl.py` (`_broken_invoke`), `test_service_workflow_recovery.py` (`_patch_session`), `test_tenant_context.py` (`_reset_context`).
La mayoría se referencian por **decorador `@pytest.fixture` o `monkeypatch.setattr` con string** → revisar caso a caso; muchos NO son muertos.

### Comando de limpieza propuesto (NO ejecutado)

No existe un borrado masivo seguro. Procedimiento por candidato:

```bash
# 1) confirmar 0 usos (incl. strings/getattr) en TODO el repo:
ruff check --select F811,F841 backend/        # redefiniciones / locals sin uso
grep -rn "NOMBRE_HELPER" backend/ frontend/ scripts/   # incluir comillas y getattr
# 2) solo si 0 usos reales y no es callback de librería ni fixture → borrar la def a mano.
```
Detalle completo por candidato (con dónde aparece cada nombre): `tasks/_tier1_validation.json`.

### 2º pase — verdictos (verificación de referencias indirectas)

**Método:** scan en Python puro de los 1617 ficheros del repo (sin `node_modules`/`.next`),
buscando para cada uno de los **78 ALTA**: (a) el nombre como **string** `"fn"`/`'fn'` (registry,
`getattr`/`setattr`, `monkeypatch.setattr`, `patch`), (b) uso del identificador en **otro fichero**,
(c) uso **intra-módulo**, (d) convención de **callback de librería** (`_invoke`, `_llm_type`,
`_identifying_params`, `_link_callback`…), (e) **migración Alembic**. Nota: `ripgrep` no está
instalado en este entorno (el primer intento devolvió `WinError 2`); se rehízo con `os.walk`.

**Resultado: 0 TRULY_DEAD / 78 FALSE_POSITIVE.** Ningún borrado recomendado.

| Categoría de FALSE_POSITIVE | Nº | Motivo |
|---|---|---|
| Usado en **otro fichero** (la arista CALLS/IMPORTS se perdió en el grafo) | 68 | Referencia directa real fuera del módulo de definición |
| **Callback de librería** (LangChain/reportlab) | 4 | `_invoke`, `_identifying_params`, `_link_callback`, `_visit_JSONB` — invocados por el framework |
| Uso **intra-módulo** vía string callback | 3 | `_fake_send_email` (`patch(..., side_effect=)`), `_broken_scrub` (`monkeypatch.setattr`), `_svc` (`patch.object(..., side_effect=)`) |
| **Migración Alembic** | 1 | `_disable_rls_sql` en `0016_sec_rls.py` |
| **Pytest fixtures `autouse=True`** (último filtro) | 3 | Ver nota abajo |

**Caso límite resuelto:** el scan dejó 3 candidatos con **cero** referencias por nombre en todo el repo:
`test_cache.py::_reset_redis_state`, `test_idempotency_guard.py::_clean_memory`,
`test_request_context.py::_reset`. Al abrir los ficheros, **los tres son
`@pytest.fixture(autouse=True)`** → pytest los inyecta por recolección automática, nunca por nombre.
**No son código muerto.** → reclasificados a FALSE_POSITIVE.

**Verdicto final TIER 1: TRULY_DEAD = 0.** La hipótesis del 1er pase se confirma: todos los "ALTA"
son falsos positivos (referencias cross-módulo que el grafo no capturó, callbacks de librería,
dispatch por string, migraciones, fixtures). **No se recomienda borrar ningún helper de TIER 1.**

Datos crudos del 2º pase: `tasks/_tier1_pass2c_out.json` (veredicto + muestra de referencia por candidato).

---

## TIER 2 — Imports/exports sin uso

**Resumen:** Backend `ruff F401` = **20 imports sin uso, todos en `backend/tests/`**; frontend `tsc --noEmit` limpio (0 errores).
**Riesgo:** **BAJO** (autofix de ruff es seguro; ts-prune pendiente de instalar).

### Backend Python — herramienta usada: **ruff 0.7.4** (`ruff check --select F401`)

20 errores, los 13 ficheros afectados (todos en tests):

| Fichero | nº F401 |
|---|---|
| `backend/tests/test_treasury.py` | 3 |
| `backend/tests/test_service_workflow_recovery.py` | 3 |
| `backend/tests/test_service_workflow_fiscal_approval.py` | 3 |
| `backend/tests/test_service_workflow_nlp_extra.py` | 2 |
| `backend/tests/test_service_workflow_scheduler.py` | 1 |
| `backend/tests/test_service_workflow_parse_nl.py` | 1 |
| `backend/tests/test_service_workflow_approval.py` | 1 |
| `backend/tests/test_service_sales_commands.py` | 1 |
| `backend/tests/test_modelo_200.py` | 1 |
| `backend/tests/test_modelo_100.py` | 1 |
| `backend/tests/test_core_datetime_utils.py` | 1 |
| `backend/tests/test_collections.py` | 1 |
| `backend/tests/integration/test_orchestrator_dispatch.py` | 1 |

Ejemplos: `pytest` sin usar, `datetime.timedelta`, `uuid.uuid4`, `app.db.models.billing.InvoiceLine`, `decimal.Decimal`, `contextlib`.

**Comando de limpieza (NO ejecutado) — es autofix seguro:**
```bash
ruff check --select F401 backend/ --fix
```

### Frontend TS — ts-prune ejecutado (`npx --yes ts-prune`, sin instalar global)

`npx --yes ts-prune` **sí funcionó** (exit 0) usando `frontend/tsconfig.json`. `tsc --noEmit` ya estaba limpio.

**Cifras brutas:** 432 líneas → **187 `(used in module)` (ruido)** + **245 exports "sin uso" reales**.
Pero la mayoría son **falsos positivos estructurales de ts-prune**, no código muerto:

| Grupo | Nº | ¿Borrable? |
|---|---|---|
| Exports de **framework Next.js** en `app/` (`default` de page/layout/error, `metadata`, `config`, `middleware`…) | 137 | **NO** — los consume el router de Next, no el código |
| Defaults de **config/i18n/.d.ts** (`playwright.config`, `vitest.config`, `request.ts`, `routing.ts`, `routes.d.ts`) | 7 | **NO** — los carga la herramienta |
| **Barrels `index.ts`** en `components/{data-table,layout,shared}` (re-exports) | ~21 | **NO (probable)** — ts-prune no ve consumidores vía barrel; revisar antes |
| **Tipos en `lib/api.ts`** (`AnalyticsRRHH`, `QuoteLine`, `InvoiceSuggestion`, `DeliveryNote`, `LlmProviderEntry`…) | 68 | **Candidatos reales** — son `type`/`interface` sin importar; borrado **sin impacto runtime** (solo tipos) |
| `default` de 2 componentes (`GenerativeUI.tsx`, `Workflows/NodeStatusBadge.tsx`) | 2 | Revisar — ¿import dinámico/lazy? |

**Review-worthy real ≈ 96** (73 en `lib/`, 23 en `components/`); de esos, los **68 tipos de `lib/api.ts`**
son el único grupo con borrado de bajo riesgo (type-only). Recomendación conservadora: **no borrar en bloque**;
si se quiere depurar `lib/api.ts`, verificar cada tipo con `tsc` tras quitarlo (ts-prune no detecta usos en
JSDoc ni en re-exports indirectos).

```bash
cd frontend && npx --yes ts-prune        # reproducir (usa tsconfig.json)
```
Listado completo legible: `tasks/_tsprune_top.py` (script de parseo); salida cruda regenerable con el comando de arriba.

### TIER 2b — Exports muertos confirmados en lib/api.ts (verificado por workflow, 2026-06-17)

**Total confirmados:** **3** exports type-only sin uso externo.

> **Nota de ubicación:** `frontend/src/lib/api.ts` es un barrel de 10 líneas (`export * from "./api/index"`).
> Los 3 símbolos NO se declaran ahí físicamente: viven en los módulos `frontend/src/lib/api/<modulo>.ts`
> y se re-exportan vía `frontend/src/lib/api/index.ts`, por lo que forman parte de la superficie pública
> de `@/lib/api`. La tabla indica el rango de la **declaración real** y, aparte, la línea del re-export en `index.ts`.

| Símbolo | Kind | Fichero de declaración | Líneas | Re-export en `api/index.ts` | Método de verificación |
|---|---|---|---|---|---|
| `StockMovementResult` | `interface` (type-only) | `frontend/src/lib/api/scanner.ts` | 32-42 | línea 213 | grep repo completo + refutador adversarial |
| `HRDocumentGeneratePayload` | `interface` (type-only) | `frontend/src/lib/api/hr_documents.ts` | 16-21 | línea 215 | grep repo completo + refutador adversarial |
| `GenerativeInterface` | `interface` (type-only) | `frontend/src/lib/api/generative_ui.ts` | 3-12 | línea 216 | grep repo completo + refutador adversarial |

**Sobrevivieron a refutación adversarial:** los 3 fueron sometidos a un refutador adversarial que intentó
encontrar cualquier uso externo (imports, JSDoc, re-exports indirectos, usos por string) y no halló ninguno.
Tras esa refutación siguen confirmados como muertos. Salvedad estándar de `ts-prune` para type-only:
borrado **sin impacto runtime** (solo tipos); aun así, verificar con `tsc --noEmit` tras quitar cada uno,
y recordar que `HRDocumentGeneratePayload` y `GenerativeInterface` se usan **dentro de su propio módulo**
(en `hrDocuments.generate` y en `generativeUI` respectivamente), por lo que al borrar el `export` hay que
decidir si el tipo se elimina por completo o solo se le quita la palabra `export` (uso intra-módulo). El
único 100% inerte es `StockMovementResult` (no se usa ni dentro de `scanner.ts`).

**Resultado de ejecución (2026-06-17):** se borró **únicamente `StockMovementResult`** (el único 100% inerte) — declaración `scanner.ts:32-42` + su entrada en el re-export `api/index.ts:213`. Verificado con `tsc --noEmit` (exit 0, sin errores). `HRDocumentGeneratePayload` y `GenerativeInterface` se **conservan**: se usan dentro de su propio módulo y son superficie pública coherente del cliente API (de-exportarlos sería churn con riesgo de romper imports futuros).

---

## TIER 2c — Exports muertos confirmados en components/ (workflow, 2026-06-17)

**Total confirmados:** **6** exports sin uso externo (verificados por grep repo completo + refutador adversarial).

> **Exclusión:** se excluyeron los entry points de Next.js (`default` de `page`/`layout`/`error`,
> `metadata`, `config`, `middleware`, etc.) — los consume el router de Next, no el código, así que
> ts-prune los marca como "muertos" siendo falsos positivos estructurales. Ninguno de los 6 de abajo
> es un entry point del framework.

| Símbolo | Fichero | Kind | Líneas | ¿Fichero entero borrable? |
|---|---|---|---|---|
| `default` (`GenerativeUI`) | `frontend/src/components/GenerativeUI.tsx` | `default function` (componente) | 19-39 | **No** — el fichero también re-exporta `sanitizeHTML` (línea 41) e importa el hook (línea 3); solo se borra la declaración del componente |
| `authHeaders` | `frontend/src/components/documentos/shared.ts` | `function` | 9-12 | **No** — conviven `STATUS_STYLE`, `fileIcon`, `formatSize` (en uso); solo se borra esta función |
| `API_URL` | `frontend/src/components/documentos/shared.ts` | `const` (export) | 7 | **No** — mismo fichero compartido con otros exports vivos; solo la línea 7 |
| `KpiCardSkeleton` | `frontend/src/components/shared/index.ts` (barrel) | re-export (decl real en `Skeletons.tsx` 4-17) | barrel: 6 · decl: `Skeletons.tsx` 4-17 | **No** — barrel re-exporta símbolos vivos; además `PageSkeleton` usa `KpiCardSkeleton` intra-módulo (`Skeletons.tsx:33`), así que quitar el `export` no permite borrar la función |
| `PageSkeleton` | `frontend/src/components/shared/index.ts` (barrel) | re-export (decl real en `Skeletons.tsx` 19-49) | barrel: 6 · decl: `Skeletons.tsx` 19-49 | **No** — barrel comparte línea 6 con `KpiCardSkeleton`; la decl real vive en `Skeletons.tsx` junto a otra función |
| `default` (`NodeStatusBadge`) | `frontend/src/components/Workflows/NodeStatusBadge.tsx` | `default function` (componente) | 20-33 | **Sí** — el `default` es el único export del fichero y todo su contenido (33 líneas) sirve a ese componente; sin re-exports ni otras decls públicas |

**Notas de seguridad:**
- `GenerativeUI.tsx` y `NodeStatusBadge.tsx` son `default function`: confirmar que NO se cargan vía
  `import()` dinámico / `next/dynamic` antes de borrar (el grep + refutador adversarial ya no halló ninguno).
- `KpiCardSkeleton` y `PageSkeleton` se exponen vía **barrel** `shared/index.ts` (línea 6 conjunta).
  La declaración real está en `Skeletons.tsx`; `PageSkeleton` consume `KpiCardSkeleton` dentro del propio
  fichero, por lo que de-exportar ≠ borrar la función. Decidir si se elimina el par completo o solo el barrel.
- `API_URL` y `authHeaders` comparten `documentos/shared.ts` con helpers en uso → borrado quirúrgico, nunca el fichero.

---

## TIER 3 — Cruft local ignorado (en disco, NO trackeado)

**Resumen:** dos directorios gitignored ocupan 455 KB en disco; `git ls-files` confirma 0 ficheros trackeados.
**Riesgo:** **NULO** (no está en git; borrar solo libera disco local).

| Directorio | Ficheros | Tamaño | ¿Trackeado? | ¿Gitignored? |
|---|---|---|---|---|
| `pytest-of-Marcos/` | 74 | 142K | No (0) | Sí |
| `backend/scripts/_runs/` | 39 | 313K | No (0) | Sí |

`git check-ignore` confirma ambos ignorados; `git ls-files | grep` → 0 en ambos.

**Comandos de borrado seguro de disco (NO ejecutados):**
```bash
rm -rf "c:/Users/Marcos/Desktop/automatizacion de empresas/Automatiza-pyme-main/pytest-of-Marcos"
rm -rf "c:/Users/Marcos/Desktop/automatizacion de empresas/Automatiza-pyme-main/backend/scripts/_runs"
```

---

## TIER 4 — Índice GitNexus

**Resumen:** índice fresco en HEAD `fc3dd32`; indexa 1703 ficheros (incluye algunos ignorados como dumps/logs) y contiene 2 repos AJENOS de otro proyecto.
**Riesgo:** **NULO** (decisión de mantenimiento, no toca código).

- Repos ajenos indexados: `MicroservicesGenerator-backend-master`, `MicroservicesGenerator-frontend-main`.
- Opciones (NINGUNA ejecutada):
  - **(a) Re-analizar tras borrar el cruft de TIER 3:** `npx gitnexus analyze` — limpia del índice los dumps/logs ignorados ya borrados.
  - **(b) Dejar el índice como está:** está fresco y operativo; el ruido de ficheros ignorados es cosmético.
- Limpiar repos ajenos del grafo es independiente de este repo (gestión global de GitNexus).

---

## Resumen ejecutivo

| Tier | Nº candidatos | Riesgo | Acción propuesta |
|---|---|---|---|
| **1** Código muerto `_*` | 78 ALTA / 35 REVISAR (113) | **MEDIO** | Verificar caso a caso; **NO borrado masivo**. 16 dispatchers + callbacks de librería + providers de registry son falsos positivos. |
| **2** Imports sin uso | 20 (backend) / 0 (frontend) | **BAJO** | `ruff check --select F401 backend/ --fix` (autofix). ts-prune pendiente de instalar. |
| **3** Cruft local | 2 dirs (455 KB, 113 ficheros) | **NULO** | `rm -rf` los dos dirs gitignored (libera disco). |
| **4** Índice GitNexus | n/a | **NULO** | Opción (a) re-`analyze` tras TIER 3, u (b) dejar como está. |

**Decisiones que requieren al usuario:**
1. ¿Instalar `ts-prune` en frontend para completar TIER 2 (exports TS)?
2. TIER 1: confirmar si quiere que un segundo pase abra los ficheros de los `_exec_*`/`_fetch_*`/`_billing_*` para descartar dispatch interno antes de proponer borrados concretos.
3. ¿Aplicar el autofix de ruff (TIER 2) y el `rm -rf` (TIER 3) ahora, o solo documentar?
