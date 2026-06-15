# Auditoría arquitectónica AutomatizaCore — 2026-06-14

## Resumen ejecutivo

La arquitectura de AutomatizaCore está **sana en su núcleo y bien estratificada**, con cero ciclos de capa frontend→backend, una única base HTTP (`client.ts`), routes registradas al 100% (65/65) y módulos load-bearing (`db` I=0.02, `core` I=0.04) que son abstracciones estables y limpias. No hay código muerto que rompa nada. Los problemas reales son de **dos clases**: (a) **deriva documental severa** — el contrato central de la capa de agentes (`run_agent()` como único export) está documentado al revés del código real (el patrón vivo es `graph` + `tool_registry`), con conteos contradictorios en README/SCOPE/ARCHITECTURE; y (b) **fugas de encapsulación y acoplamiento puntual** — un módulo "privado" (`_pdf_base.py`) con 18 importadores externos, una función privada del Coordinador (`_invoke_dispatcher`) importada desde `services`, y 14 routes que mutan estado en la ruta en vez de delegar a un servicio. La salud global del acoplamiento es **ACEPTABLE**: sin ciclos tóxicos no resolubles, sin sesión DB global, e inestabilidad alta solo en hojas y composition roots legítimos.

| Severidad | Hallazgos confirmados/ajustados |
|-----------|-------------------------------|
| High | 3 (D2-01, D2-03, DOC-01) |
| Medium | 6 (D2-02, D2-04, D3-01, DOC-03, DOC-04, D5-N2, D5-N3, D6-04, D6-05, D6-08) |
| Low | 9 (D1-001, D1-002, D3-02, DOC-08, D5-N1, D5-N4, D5-N5, D6-03, D6-06, D6-09) |
| Info | varios (confirmaciones de buenas prácticas; no requieren acción) |

> Nota: los hallazgos `refuted` (p.ej. eliminar `backup_local.py`) quedan **excluidos** de este informe — son WIP cableado backend-first, no código muerto.

---

## 1. Flujo de información y conectividad

La cadena canónica (componente Next.js → `lib/api/*.ts` → `client.ts` → `api/v1/routes/*.py` → services/agents → db) se cumple de forma consistente. **CERO `fetch()` directo** en `frontend/src/app` o `frontend/src/components`. Las 65 routes están registradas. 51/52 módulos `lib/api` mapean a routes reales.

| ID | Hallazgo | Sev. | Evidencia | Acción |
|----|----------|------|-----------|--------|
| D1-001 | Route `telemetry` sin UI de opt-in/opt-out (gap de autoservicio RGPD; el endpoint `DELETE /telemetry/me` sigue invocable por API) | low | `router.py:103`; `telemetry.py:39,60`; eventos vivos en `services/analytics/events.py` (`telemetry.opted_out`), modelo `TelemetryOptOut` en `db/models/auth.py` + migración 0014. `grep telemetry` en `frontend/src` = 0 | Añadir `lib/api/telemetry.ts` + control en Configuración, o documentar vía alternativa de opt-out |
| D1-002 | Docstring engañoso: `backup_local.py:55-59` afirma que `postgres-manager.js` llama a `/backup-local/record`, integración inexistente | info/low | `desktop/postgres-manager.js` sin coincidencias `backup`/`record`. Contrato de integración aspiracional/obsoleto | Anotar el docstring como "pendiente (consumer Electron no implementado)" |

**Nota tolerada (no acción):** `/api/v1/verify/{huella}` es público por diseño (scanners QR VeriFactu), correcto que no tenga consumidor `lib/api`. Los 4 `fetch()` crudos restantes viven dentro de la propia capa `lib/api` (taskStream SSE, client_portal/scanner con JWT propio, error-reporter) con justificación documentada.

**Recomendación CI:** regla ESLint que prohíba `fetch()` fuera de `lib/api`.

---

## 2. Profundidad, estabilidad y acoplamiento

`db` (Ca=55, I=0.02) y `core` (Ca=44, I=0.04) son pilares estables y limpios (`db/base.py` y `core/config.py` sin imports de services/agents). La inestabilidad alta de los agentes hoja es esperada y saludable. El problema real es la **encapsulación**.

| ID | Hallazgo | Sev. | Evidencia | Acción |
|----|----------|------|-----------|--------|
| D2-01 | **Ciclo de paquete REAL (eager)**: `services/documents` ↔ `services/pdf` vía `_pdf_base` privado | high | `services/pdf/__init__.py:13` importa eager de `app.services.documents._pdf_base`; `services/documents/smart_chunker.py:13` importa eager `app.services.pdf.parser`. Doble dirección eager = ciclo genuino | Extraer `_pdf_base.py` a paquete neutro compartido (`services/pdf/_base.py` o `services/reporting_base/`) del que dependan AMBOS; renombrar sin `_` |
| D2-02 | **Fuga de encapsulación**: `_pdf_base.py` (nombre privado) importado por 18 ficheros externos en 4 paquetes (`pdf/` ×10, `pdf_reports/` ×8, `hr/schedule_export.py`, `accounting/libros_pdf.py`) | medium | Su propio docstring (línea 1-3) dice "Utilidades COMPARTIDAS para la generación de PDFs", contradice el nombre `_`. No define `__all__` | Promover a `pdf_base.py` (sin `_`) en paquete de reporting común |
| D2-03 | **Fuga de símbolo privado del Coordinador**: `_invoke_dispatcher` (de `agents/orchestrator/_dispatch_handlers.py`) importado desde `services` → ciclos `orchestrator`↔`services/workflow` y `orchestrator`↔`services/ai` | high | `services/workflow/_execution.py:11` y `services/ai/node_dispatch.py:13` importan `_invoke_dispatcher`. Invierte la dependencia esperada (services no debe conocer internals de un agente) | Exponer punto de entrada público en `services/workflow` (o `services/orchestration`) para "invocar dispatcher"; eliminar import del símbolo `_`-prefijado desde `services/*` |
| D2-04 | Norma obsoleta: "único export = `run_agent()`" — solo existe en 1 de 15 agentes (`marketing/agent.py:61`) | medium | El contrato real es exportar `graph` + funciones `@tool` registradas en `tool_registry.py`. Docstrings de cada paquete documentan el re-export como intencional | Ver sección 4 (DOC-01) — corregir doc, no código |

**Confirmado sano (no acción):** `agent_tools/` (Ca=16) y `agents/workflow/tools.py` son capa de herramientas compartidas, no agentes; las 96 aristas "agent→agent" son mayoritariamente hacia ellos (infra) o dispatch legítimo del Coordinador. El "ciclo" `email`↔`gmail_client` es una arista STALE del grafo (colisión con stdlib `email`).

---

## 3. Flujos y contratos de agentes

Flujo real verificado: `instrucción → classify_node → plan_node → dispatch_node → _execute_one → _invoke_dispatcher → DISPATCHER_MAP[agent] → graph.ainvoke()` (o `run_email_agent` / `run_workflow_agent`). El contrato **no-excepciones SÍ se cumple de facto**: 0 `raise` en `*/agent.py`, toda invocación envuelta en try/except con backstop en `_execute_one`.

| ID | Hallazgo | Sev. | Evidencia | Acción |
|----|----------|------|-----------|--------|
| D3-01 | Contrato "único export público = `run_agent()`" incumplido por los 15 dominios | medium | `accounting`/`inventory` exportan solo `graph`; `banking`/`billing`/`compliance`/`crm`/`documents`/`excel`/`hr`/`rag`/`recruitment` exportan `graph`+@tools; `email`=`run_email_agent`; `workflow`=`run_workflow_agent`; solo `marketing` define `run_agent` (y lo llama una route, no el dispatch). `tool_registry.py` importa @tools deliberadamente desde 10 `__init__.py` | Corregir doc (ver DOC-01); actualizar/eliminar ejemplo roto `ARCHITECTURE.md:110` |
| D3-02 | Inconsistencia de naming del punto de entrada: `graph.ainvoke` vs `run_email_agent` vs `run_workflow_agent` vs `run_agent` | low | `marketing.run_agent()` existe pero su único caller es `api/v1/routes/marketing.py:523`, no el orquestador | Documentar las 2 excepciones legítimas (email/workflow devuelven dataclasses tipadas); marcar `marketing.run_agent` como entrada de route |

**Confirmado sano (no acción):** 0 violaciones reales de "agents no importan agents"; los 3 `raise` en tools son `ValueError` en helpers privados capturados por `ToolNode`. `tool_registry.py:93` tiene una inconsistencia menor (importa `check_quarter_preventive` desde `compliance.tools` en vez de `__init__`, que ya lo re-exporta) — nit opcional.

---

## 4. Documentación

La visión de producto (local-first, IA agéntica) es coherente en README/ARCHITECTURE/SCOPE/MARKETING. El problema es **deriva doc↔código** en el contrato de agentes y conteos.

| ID | Hallazgo | Sev. | Evidencia | Acción |
|----|----------|------|-----------|--------|
| DOC-01 | **Contrato `run_agent()` documentado al revés del código**; ningún doc describe el patrón real `graph`+`tool_registry` | high | `ARCHITECTURE.md:98` ("run_agent es la única función pública... Nada externo los importa") y `README.md:197` ("run_agent(...) -> AgentResult") son falsos. `ARCHITECTURE.md:110` muestra `from app.agents.billing import run_agent` que FALLARÍA (símbolo inexistente). `marketing` es el único con `run_agent`, y su firma `(prompt, tenant_id) -> list[dict]` tampoco es conforme | Reescribir el contrato: export público = `graph` compilado + @tools en `tool_registry`; documentar dispatch vía `graph.ainvoke()`; eliminar ejemplo roto `:110` |
| DOC-03 | Conteos contradictorios doc vs código | medium | Agentes dominio reales=14; `SCOPE.md:172`=9; `README` (×4: :5,:192,:756,:793)=13 y el diagrama `:194-196` **omite `inventory`** (que existe con `agent.py`+dispatcher). Dispatchers: `DISPATCHER_MAP`=17 vs README=14. Tests: 215 ficheros / ~2102 funcs vs README=113. Routes: 66 ficheros vs "48+". Páginas: 109 vs "80+". Modelos: 32 vs 23 | Unificar conteos desde código; añadir `inventory` al diagrama; generar conteos en CI |
| DOC-04 | Routes "cero lógica" violada (ver D5-N3); `AGENTS.md` duplica el bloque GitNexus de `CLAUDE.md` pero `README:756` lo cita como detalle de 13 agentes; deuda de naming Coordinador/Orquestador repetida | medium | 76 aristas `db.add/select` en routes; `README:202` nota de naming | Documentar excepción read-only en ARCHITECTURE §5; regenerar/eliminar `AGENTS.md` y corregir `README:756`; centralizar nota de naming |
| DOC-08 | Transcripción de sesión Claude Code (186 KB) commiteada por error | low | `desktop/2026-04-09-191954-...txt` git-tracked, banner "Claude Code v2.1.92"; sin regla `*.txt` en `.gitignore` | `git rm` + patrón ignore `desktop/*.txt`. (Los README de `desktop/dist/` NO son needs-review: `dist/` ya está gitignored `:78`) |

---

## 5. Normas ambiguas (con propuestas de resolución concretas)

`ARCHITECTURE.md` (405 líneas) es más matizada que `CLAUDE.md` y ya resuelve dos ambigüedades (Domain vs Infra service §1.1; sesión en @tool §13), pero **no menciona** `agent_tools/`, `agents/shared/` ni la nota terminológica, pese a que `README:202` la remite ahí (cross-reference roto).

| ID | Norma | Sev. | Resolución propuesta concreta |
|----|-------|------|-------------------------------|
| D5-N1 | Naming `orchestrator`(dir)=Coordinador vs `services/workflow`=Orquestador — ambigüedad real, ya documentada en README+CLAUDE | low | **NO renombrar** (200+ usos). Añadir a `ARCHITECTURE.md` sección "0. Terminología canónica" con tabla `agents/orchestrator/`=Coordinador \| `services/workflow/`=Orquestador. Declarar el alias UNA vez |
| D5-N2 | "Agents NUNCA importan otros agents" choca con `agent_tools/`, `agents/shared/` (infra bajo `agents/`) | medium | Redefinir norma: "Los agentes de **DOMINIO** no se importan entre sí ni sus `_tools`. SÍ pueden importar infra compartida: `agents/agent_tools/`, `agents/shared/`". Documentar en ARCHITECTURE. Opcional: sacar `compile_deterministic_steps` del `__init__` público de `agents/workflow/` (solo uso interno, `agent.py:109`) |
| D5-N3 | "Routes: CERO lógica" es aspiracional — 42/56 routes con models son **read-only** (tolerable), 14 **mutan** en la ruta (violación real) | medium | Definir umbral en `ARCHITECTURE.md §5`: "una route PUEDE hacer SELECT read-only para componer respuestas, pero NUNCA `db.add/commit/flush/delete` ni orquestar transacciones → servicio de dominio". Backlog acotado: prioridad `marketing.py` (16 mutaciones), `email_marketing.py` (12), luego `onboarding_*`, `treasury.py`, `tenant.py` |
| D5-N4 | "Services reciben `db` como parámetro" **SE CUMPLE**; 21 aperturas de `AsyncSessionLocal` son entrypoints background/scheduler sin request | low | Solo cerrar ambigüedad documental: nota en `ARCHITECTURE.md §7/§13` legitimando `run_*`/fire-and-forget (`audit_log_result`) que abren `async with AsyncSessionLocal()`. 0 sesión global confirmado |
| D5-N5 | `README:202` remite a `ARCHITECTURE.md` para la nota terminológica, pero ARCHITECTURE no la contiene (cross-ref roto) | low | Corregir el enlace O (preferible) añadir la nota + mención de `agent_tools/`/`shared/` a ARCHITECTURE como fuente única de verdad |

**Corrección de grafo (info):** las aristas "agent imports agent" de `graph_facts.md` dirigidas a `agents/workflow/tools.py` son STALE/erróneas — 0 imports reales a `app.agents.workflow` desde dominios. El acoplamiento real es domain→`agent_tools` (37 líneas/15 ficheros), unidireccional, sin ciclos. Re-indexar el grafo.

---

## 6. Huérfanos y código muerto

**0 código muerto confirmado** que rompa algo. Las "468 huérfanas / 120 curadas" son falsos positivos: 77 `@tool` (registro dinámico vía `tool_registry`), 33 nodos `agent.py`, 10 vivos. Los 150 `Ca=0` son artefacto de grafo incompleto. Lo real son **artefactos de runtime/debug commiteados**.

| ID | Hallazgo | Sev. | Evidencia | Acción |
|----|----------|------|-----------|--------|
| D6-03 | 12 ficheros `tmp*.csv` (78-104 B) en la raíz | low | No trackeados; `.gitignore:38:*.csv`. Fixtures ERP generados en CWD | Borrar; generar vía `tempfile` en tmpdir del SO (patrón ya usado en `pdf/parser.py:186`) |
| D6-04 | `backend/test_tasks.py`: debug personal git-tracked con ruta hardcodeada a otra máquina (typo "atomatizacion") | medium | 926 B, `sys.path.insert(0, r"C:\...\atomatizacion...")`; sin funciones `test_*`; `pytest.ini` lo excluye explícitamente | `git rm`; mover a `scripts/` y renombrar si se conserva |
| D6-05 | `backend/celerybeat-schedule`: binario shelve de runtime git-tracked | medium | 16384 B, regenerado al arrancar el scheduler; NO gitignored | `git rm --cached` + gitignore patrón `celerybeat-schedule*` (no solo el fichero exacto) |
| D6-06 | Transcripción Claude Code 186 KB git-tracked (mismo que DOC-08) | low | `desktop/2026-04-09-191954-...txt`, 190966 B | `git rm` + patrón ignore |
| D6-08 | Acoplamiento agent→agent vía hubs `agent_tools`/`workflow` (Ca=16/15) | medium | Mayoría son dispatchers legítimos e infra compartida (ver D5-N2) | No alarmante; documentar como infra (D5-N2). Refactor opcional a `services/`/librería `shared_tools` |
| D6-09 | `orchestrator` Ce=25, I=0.89 (importa los 15 dominios) | low | Composition root del Coordinador, max fan-out | Aceptable; mantener `dispatchers/` por dominio. Gate CI "agent-imports-agent" |

**Ajustes de evidencia:** `imports.err` (160 KB, no trackeado) NO es stderr de GitNexus — es JSON byte-idéntico a `imports.json`, duplicado borrable sin riesgo. Riesgo adicional detectado: `.gitignore` ignora globalmente `*.csv`/`*.xlsx`/`*.pdf`, lo que puede **enmascarar fixtures legítimos** — restringir a rutas (`backend/generated/*.csv`) en vez de glob global. Todo `tasks/reports/_audit/` (artefactos de auditoría en el árbol) debería gitignorearse.

---

## Plan de acción priorizado

### P0 — Romper ciclos y corregir contrato (esfuerzo: ~1-2 días)
1. **D2-01 + D2-02** (high): extraer `_pdf_base.py` → `pdf_base.py` en paquete neutro compartido (rompe ciclo `documents`↔`pdf` y la fuga de 18 importadores). ~4-6 h.
2. **D2-03** (high): exponer entrada pública en `services/workflow` para invocar dispatcher; eliminar import de `_invoke_dispatcher` desde `services/*` (rompe ciclos `orchestrator`↔`workflow`/`ai`). ~4 h.
3. **DOC-01** (high): reescribir contrato de agentes en `ARCHITECTURE.md`/`README.md` (`graph`+`tool_registry`), eliminar ejemplo roto `:110`. ~2 h.

### P1 — Deriva doc y violaciones de capa (esfuerzo: ~1-2 días)
4. **DOC-03**: unificar conteos desde código, añadir `inventory` al diagrama README, generar en CI. ~3 h.
5. **D5-N3 / DOC-04**: documentar umbral read-only en ARCHITECTURE §5; backlog de refactor de las 14 routes que mutan (empezar `marketing.py`, `email_marketing.py`). Doc ~1 h + refactor por iteraciones.
6. **D5-N1/N2/N5**: añadir a ARCHITECTURE secciones "Terminología canónica" + "Infra de agentes" (`agent_tools`/`shared`), redefinir norma "agents no importan agents" a "agentes de DOMINIO". ~2 h.
7. **D6-04/D6-05/D6-06**: `git rm`/`git rm --cached` de debug y artefactos runtime + gitignore. ~30 min.

### P2 — Higiene y gaps de producto (esfuerzo: ~1 día)
8. **D1-001**: `lib/api/telemetry.ts` + control RGPD en Configuración. ~3 h.
9. **D6-03 + imports.err + `_audit/`**: borrar tmp CSV, duplicado JSON, gitignorear `tasks/reports/_audit/`; restringir globs `*.csv/*.xlsx/*.pdf` a rutas. ~1 h.
10. **CI gates**: regla ESLint "no fetch fuera de lib/api", gate "agent-imports-agent", conteos generados. ~3 h.
11. **D1-002**: corregir docstring engañoso `backup_local.py:55-59`. ~15 min.
