# Auditoría Estática — Capacidades LLM y E2E

**Fecha:** 2026-05-05
**Alcance:** Estático (sin ejecutar LLM real). Backend FastAPI + LangGraph, todos los dominios de agentes.
**Método:** Glob + Grep + lectura selectiva. Sin runtime.

> **Addendum 2026-05-05:** Ver sección 13 al final — hallazgo runtime adicional descubierto al implementar tests E2E: el nodo `finalize` estaba declarado pero desconectado en los grafos de hr/billing/banking/accounting. Ya arreglado.
>
> **Addendum 2026-05-17:** Re-verificados los 3 hallazgos 🔴 Alto.
> - **#1 Tools sin docstring → ✅ RESUELTO**: `create_opportunity`, `update_opportunity_stage`, `create_client` (crm), `send_email` (email), `create_position`, `list_candidates` (recruitment) ya tienen docstring (commits posteriores los añadieron, con notas AI Act en recruitment).
> - **#2 `__init__.py` limpieza → 🟠 PARCIAL**: aplicada Opción A (mecánica, riesgo bajo) en 10 paquetes (banking, billing, compliance, crm, documents, excel, hr, marketing, rag, recruitment). Se conservan los símbolos consumidos externamente (`graph` por los dispatchers, tools individuales por `tool_registry.py`) y se eliminan `*_agent_node`, `*_finalize_node`, `workflow` uncompiled, `*_SYSTEM_PROMPT`, lista `tools`. Tests verificados verde. **Opción B (refactor completo con `run_agent()` envolviendo `AgentResult`) queda pendiente — se hace junto con #3.**
> - **#3 `AgentResult` en `agent.py` → 🔴 PENDIENTE**: 12/14 siguen devolviendo `{"status": "done", "agent_results": [...]}` desde `finalize`. Mitigación a nivel dispatcher sigue activa, no es bug. Plan dedicado en `tasks/todo.md` con coste real estimado (~5-7h, no 3-4h, por el entrelazado con `tool_registry` y dispatchers).

---

## TL;DR — Veredicto

| Área | Estado | Nota |
|------|--------|------|
| Configuración LLM centralizada | ✅ Sólido | `core/llm_factory.py` con multi-provider, prompt caching, per-tenant config |
| Contrato `AgentResult` | 🔴 **Crítico** | Solo 2 de 14 dominios lo usan en `agent.py` (email, workflow) — pendiente refactor combinado |
| `__init__.py` exports limpios | 🟠 **Parcial** | Opción A aplicada 2026-05-17 (símbolos internos retirados); Opción B pendiente con #3 |
| Aislamiento entre agentes | ✅ OK | Sin imports cruzados directos; `agent_tools/` es shared correctamente |
| Tools con docstring | ✅ OK | 6 huérfanas detectadas en 2026-05-05 ya tienen docstring (verificado 2026-05-17) |
| Dispatcher orchestrator | ✅ OK | 17 dominios mapeados con fallback `success=False` |
| Frontend → backend | ✅ OK | Cero `fetch()` directo fuera de `lib/api/*` |
| Tests E2E reales | 🟠 Parcial | Mayoría son tests de routes, no agentes con LLM real |

**Riesgo dominante:** los agentes no propagan errores de forma estructurada. Si el LLM falla o un tool revienta, la ruta no recibe un `AgentResult.success=False` — se pierde observabilidad y manejo controlado.

---

## 1. Configuración LLM (lo que está bien)

**`backend/app/core/llm_factory.py`** centraliza toda la instanciación:

- Providers soportados: Anthropic, OpenAI, Groq, OpenRouter, Mock (testing).
- Default: `claude-sonnet-4-6` (Anthropic) y `gpt-4o-mini` (OpenAI). Sin modelos retired.
- Selección de provider vía `settings.DEFAULT_LLM_PROVIDER` (env).
- **Per-tenant LLM** desde BD (`TenantLlmConfig`) con keys encriptadas — bien pensado para multi-tenant.
- **Prompt caching** Anthropic implementado en `make_cached_system_message()`.
- Fallback chain: groq → openai → openrouter → mock.

**Ningún agente instancia `ChatAnthropic`/`ChatOpenAI` directamente** — todos pasan por la factory. Esto es ejemplar.

---

## 2. Contrato de error (`AgentResult`) — Crítico

`AgentResult` está definido en [backend/app/agents/types.py](backend/app/agents/types.py) y se usa correctamente en:

- `agents/email/agent.py` ✅
- `agents/workflow/agent.py` ✅
- `agents/orchestrator/_dispatch_handlers.py` ✅ (envuelve excepciones de cada dispatcher)
- Todos los dispatchers individuales (`dispatchers/*.py`) ✅

**No se usa en los `agent.py` de:** accounting, banking, billing, compliance, crm, documents, excel, hr, marketing, rag, recruitment.

**Implicación práctica:**
El orchestrator captura excepciones a nivel dispatcher y devuelve `AgentResult(success=False)`, así que el endpoint sigue recibiendo respuesta. Pero **dentro** del agente individual no hay un patrón de error controlado: si una tool revienta, va por `try/except` genérico (en el mejor caso) o se traga en LangGraph (en el peor). No se distingue "el modelo no supo hacerlo" de "la tool falló por bug" de "DB caída".

**Recomendación:** todos los `agent.py` deben terminar devolviendo `AgentResult(success: bool, data, error)` en lugar de la salida cruda del grafo. Es un refactor de ~14 archivos pequeños.

---

## 3. `__init__.py` — incumplimiento generalizado

Regla CLAUDE.md: *"`__init__.py` ← exports only: `run_agent()`"*.

**Cumplen:** `email/__init__.py`, `workflow/__init__.py`.

**Incumplen** (exportan también `graph`, `tools`, `prompts`, helpers internos): accounting, banking, billing, compliance, crm, documents, excel, hr, marketing, rag, recruitment.

**Impacto:** filtran detalle de implementación. Si mañana se cambia LangGraph por otro motor, hay que tocar quien sea que importe `graph`. Refactor mecánico: limpiar 11 `__init__.py`.

---

## 4. Estructura `tools.py` — fachadas vacías

`tools.py` está pensado como "lo que el LLM ve". Hallazgos:

| Dominio | `tools.py` | `@tool` directos | Patrón |
|---------|-----------|------------------|--------|
| accounting | ❌ no existe | — | Tools en `_account_tools.py` (5) |
| banking | re-export | 0 | Tools reales en `_account_tools` (1), `_transaction_tools` (2), `_reconciliation_tools` (1) |
| billing | re-export | 0 | Tools reales en `_invoice_tools` (3), `_invoice_write_tools` (5), `_client_tools` (1), `_albaran_tools` (2), `_invoice_query_tools` (3) |
| compliance | con tools | 3 | OK |
| crm | con tools | 5 | ⚠️ 3 sin docstring |
| documents | con tools | 2 | OK |
| email | con tools | 3 | ⚠️ 1 sin docstring |
| excel | re-export | 0 | Tools reales en `_modify_tools` (2), `_import_tools` (1), `_export_tools` (2) |
| hr | re-export | 0 | Tools reales en `_employee_tools` (2), `_payroll_calc` (2), `_payroll_crud` (3) |
| marketing | con tools | 1 | OK |
| rag | con tools | 2 | OK |
| recruitment | con tools | 5 | ⚠️ 2 sin docstring |
| workflow | con tools | (ver compiler) | OK |

**Total:** 76 `@tool` repartidos en 29 archivos.

**Punto de fricción:** la regla del CLAUDE.md dice *"`tools.py` ← `@tool` + docstring (declared to LLM)"*. Si `tools.py` es una fachada que solo re-exporta de `_*.py`, técnicamente cumple, pero un revisor humano abre `tools.py` esperando ver las tools reales y se encuentra `from ._foo_tools import *`. Decisión arquitectónica a confirmar contigo: o se inlinea todo en `tools.py`, o se documenta el patrón en CLAUDE.md.

---

## 5. Tools sin docstring (el LLM las ve sin explicación)

| Archivo | Función |
|---------|---------|
| `crm/tools.py` | `create_opportunity` |
| `crm/tools.py` | `update_opportunity_stage` |
| `crm/tools.py` | `create_client` |
| `email/tools.py` | `send_email` |
| `recruitment/tools.py` | `create_position` |
| `recruitment/tools.py` | `list_candidates` |

**Impacto real:** el LLM puede invocar mal estas tools, o no invocarlas cuando debería, porque el schema autogenerado no tiene descripción. Es la causa más común de "el agente no funciona como esperaba" en producción.

**Acción:** añadir docstring a las 6. Es trabajo de 15 minutos y devuelve mucho.

---

## 6. Aislamiento entre agentes — OK

Búsqueda de `from app.agents.<otro>` dentro de `agents/<dominio>/`:

- Únicas referencias cruzadas son a `app.agents.agent_tools` (módulo compartido — patrón válido).
- Orchestrator importa de todos (correcto, es su rol).
- Submódulos privados (`_*.py`) usan imports relativos sin cruzar fronteras.

✅ Cero infracciones.

---

## 7. Orchestrator y dispatching

`agents/orchestrator/_dispatch_handlers.py` mapea 17 dominios:

```
billing, accounting, documents, compliance, banking, rag,
crm, hr, excel, email, workflow, report, recruitment,
marketing, skill, chat, team
```

- Cada dispatcher en `dispatchers/*.py` envuelve la llamada con `try/except` y devuelve `AgentResult` ✅
- `check_agent_budget()` (workers) corta si el tenant agotó presupuesto ✅
- Status transitions de AIEmployee: `idle → working → complete/failed` ✅

Esto compensa parcialmente la falta de `AgentResult` dentro de cada `agent.py`: el orchestrator es el que realmente garantiza la respuesta estructurada al endpoint.

---

## 8. Trazabilidad E2E (route → service → agent → tool)

**Patrón general:** el endpoint NO invoca `run_agent` directamente. Llama a un service, y el service decide si delega al agente. Esto desacopla bien, pero **oscurece** el flujo:

| Dominio | Endpoint | Service intermedio | Agente |
|---------|----------|--------------------|--------|
| billing | `routes/billing.py` | `services.billing.*` | `agents/billing` |
| hr | `routes/hr.py` | `services.hr.*` | `agents/hr` |
| banking | `routes/banking.py` | `services.banking` | `agents/banking` |
| documents | `routes/documents.py` | `services.documents` | `agents/documents` |
| accounting | `routes/accounting.py` | `services.billing.accounting` | `agents/accounting` |

**Problema:** ningún endpoint maneja explícitamente `AgentResult.success=False`. Si el agente devuelve error, depende de que el service lo convierta en HTTPException. Sería bueno un decorator/middleware que tradujera `AgentResult.success=False` → `502/422` automáticamente.

---

## 9. Tests E2E

20+ archivos de test. Mayoría son tests de **API routes** (mock de DB, sin LLM real). Coberturas:
- `test_accounting_agent.py` — único test que parece probar agente directamente.
- `test_api_billing.py`, `test_api_hr_*.py`, `test_api_banking.py`, `test_api_email.py`, `test_api_crm.py` — routes.
- `test_agent_metrics.py` — métricas.
- `conftest.py` ofrece `MockChatModel` (la factory devuelve mock cuando provider="mock").

**Hueco:** no hay tests E2E que ejerzan **un agente real** end-to-end con un LLM real (ni siquiera contra mock determinista) y validen que la cadena route → service → agent → tool → DB → respuesta funciona como un todo. Los E2E del commit `8ab4a01` cubren auth, factura, onboarding HR, pero a nivel HTTP, no a nivel "el LLM tomó la decisión correcta".

**Recomendación:** añadir 1 test E2E por dominio crítico (billing, hr, banking) que use `provider="mock"` con respuestas LLM scripteadas, ejercite la ruta completa y assert sobre el estado final en DB.

---

## 10. Frontend ↔ Backend — OK

- 32 módulos en `frontend/src/lib/api/*.ts`. Bien organizado por dominio.
- Cero `fetch()` directo en `app/` o `components/` saltándose `lib/api`. ✅
- Buen aislamiento, respeta CLAUDE.md.

---

## 11. Riesgos por severidad

### 🔴 Alto
1. **`AgentResult` ausente en 12/14 `agent.py`** — refactor invasivo recomendado (pre-producción, sin riesgo de rollback).
2. **`__init__.py` filtran detalle** en 11 dominios.
3. **6 `@tool` sin docstring** — degrada calidad de invocación del LLM.

### 🟠 Medio
4. Patrón `tools.py` como fachada en 5 dominios (banking/billing/hr/excel/accounting). Decisión a tomar.
5. Sin tests E2E que ejerzan el flujo completo con LLM (ni mock scripteado).
6. Endpoints no traducen `AgentResult.success=False` a HTTP de forma consistente.

### 🟢 Bajo
7. Algunos dominios sin `prompts.py` (banking, compliance, crm, documents, marketing, rag, recruitment) — pueden tener prompts inline en `agent.py`, hay que ver caso por caso.

---

## 12. Plan de acción sugerido (priorizado)

| # | Acción | Esfuerzo | Beneficio |
|---|--------|----------|-----------|
| 1 | Añadir docstrings a las 6 `@tool` huérfanas | 15 min | Alto (calidad invocación LLM) |
| 2 | Refactor `__init__.py` en 11 dominios para exportar solo `run_agent` | 1-2h | Medio (arquitectura limpia) |
| 3 | Adoptar `AgentResult` como retorno en los 12 `agent.py` faltantes | 3-4h | Alto (errores trazables) |
| 4 | Decorator/middleware que convierta `AgentResult.success=False` → HTTP error | 1h | Medio (consistencia API) |
| 5 | 1 test E2E por dominio crítico (billing/hr/banking) con `provider="mock"` y respuestas scripteadas | 3-5h | Alto (regresiones LLM detectables en CI) |
| 6 | Decidir y documentar patrón `tools.py` (fachada vs inline) | 30 min discusión | Medio (claridad arquitectónica) |

**Orden propuesto:** 1 → 3 → 4 → 5 → 2 → 6.

---

## Cómo continuar

Si quieres avanzar con runtime real (validación con LLM en vivo de los flujos críticos), me dices qué dominios y los pruebo contra mock primero, luego con clave Anthropic real para el happy path. Esa segunda pasada ya consumiría créditos.

---

## 13. Addendum runtime — finalize node desconectado (resuelto)

**Descubierto al implementar `tests/test_e2e_agent_flows.py`.**

Los grafos de **hr, billing, banking y accounting** declaraban un nodo `finalize` (`hr_finalize_node`, `billing_finalize_node`, etc.) cuyo único propósito es devolver `{"status": "done", "agent_results": [final_result]}`. Pero el grafo nunca lo invocaba:

```python
# Antes (desconectado):
workflow.add_conditional_edges("hr_agent", tools_condition)  # rutea a "tools" o END
workflow.add_edge("tools", "hr_agent")
# ↑ tools_condition retorna "__end__" cuando no hay tool_calls — finalize era código muerto
```

**Síntoma observable:** al ejecutar `await graph.ainvoke(state)`, el resultado tenía `status="running"` y los `agent_results` quedaban con lo que había acumulado el `*_agent_node` durante el loop, no el `final_result` del finalize.

**Fix aplicado:** path_map en `add_conditional_edges` que remappea `__end__` (de `tools_condition`) al nodo `finalize`, y conecta `finalize → END`:

```python
workflow.add_conditional_edges(
    "hr_agent", tools_condition, {"tools": "tools", "__end__": "finalize"}
)
workflow.add_edge("tools", "hr_agent")
workflow.add_edge("finalize", END)
```

Aplicado en los 4 archivos: `agents/hr/agent.py`, `agents/billing/agent.py`, `agents/banking/agent.py`, `agents/accounting/agent.py`.

**Verificación:** `tests/test_e2e_agent_flows.py` (nuevo) ejercita la cadena `agent_node → bind_tools → tool_call → ToolNode (DB SQLite) → agent_node → finalize` con mock LLM scripteado, y asserta que `result["status"] == "done"` y `result["agent_results"]` está poblado por el finalize node. Suite completa: 629 passed, 0 failed.

**Pendiente (no en este lote):** este fix mejora el contrato pero no resuelve por completo el hallazgo de la sección 2 sobre `AgentResult`. El finalize node devuelve un `StepResult` (en `agent_results`), no un `AgentResult` con el flag `success`. Para compliance total con el contrato, los 4 nodos `*_finalize_node` deberían devolver además `AgentResult(success=True/False, data, error)`. Esto sigue pendiente.
