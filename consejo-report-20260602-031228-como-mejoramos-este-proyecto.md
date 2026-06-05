# Consejo de los 7 Sabios — Reporte

**Atasco (ES):** ¿Cómo mejoramos este proyecto?
**Rondas usadas:** 3
**Unánime:** sí

## Resumen ejecutivo

Consenso unánime alcanzado en 3 ronda(s) (21 turnos).

## Plan priorizado

| # | Tarea | Sabios | Discrepó (resuelto) | Blast | Verif. | Auto |
|---|-------|--------|---------------------|-------|--------|------|
| 1 | **Persist LLM usage tracker to DB instead of in-memory dict** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `MEDIUM` | ⚠️ parcial | ⛔ |
| 3 | **Research: profile LLM client instantiation cost before adding cache to llm_factory.py** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | producto | `SAFE` | ✅ medido | ⛔ |
| 4 | **Extract route-layer email helpers out of agents/email/tools.py into services/email_credentials.py** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `MEDIUM` | ⚠️ parcial | ⛔ |
| 5 | **Audit and wire isConnectivityError across all AI-dependent pages** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ⚠️ parcial | ⛔ |
| 6 | **Add integration smoke tests for the orchestrator → agent dispatch path** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ✅ medido | ⛔ |
| 8 | **Add inline amount-cap checks on financial-write agent tools** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | — | `SAFE` | ⚠️ parcial | ⛔ |
| 10 | **Add tenant-facing LLM usage dashboard component and API endpoint** | estructurador, conservador, modernizador, simplificador, guardian, optimizador, producto | simplificador | `MEDIUM` | ⚠️ parcial | ⛔ |

_Columna **Discrepó**: sabios que bloquearon el item en alguna ronda y luego firmaron tras enmiendas — la textura del debate aunque el resultado final sea unánime._

## ❌ Refutadas por la verificación

_Estas tareas se apoyaban en afirmaciones que NO resistieron el contraste con el código real. Fuera del plan accionable._

- **Wire tenant-level LLM budget gate as middleware before agent dispatch** — [auto: premisa central refutada → tarea refutada] The core premise that a tenant-aggregate budget gate is missing is verified. However, the stated trigger — 'config.py defines LLM_MONTHLY_BUDGET_EUR' — is fabricated; config.py has no such variable. The task's justification is built on a phantom config key. The need for a tenant gate stands, but the rationale's starting claim is false, weakening the task's framing.
- **Swap threading.Lock for asyncio.Lock in 4 service modules (mechanical fix)** — The core claim that the fix is 'mechanical: replace threading.Lock with asyncio.Lock, change with to async with' is false. llm_trace.py uses the lock in sync callback methods (BaseCallbackHandler) where asyncio.Lock cannot be used. exec_log_store.py has zero async functions. The lock in llm_trace.py guards file I/O, not trivial dict operations. idempotency.py is 89 LOC, not ~50.
- **Implement rule-based dunning workflow over Invoice.due_date** — The task's entire premise — that rule-based dunning is a NEW feature that doesn't exist yet — is false. backend/app/services/collections/reminders.py already implements the exact D-3/D+0/D+15/D+30 schedule with 4 email templates, escalation language, interest calculations, DB queries, and an API endpoint. The collections module is labeled F3.9 and is substantially complete. The proposed NEW file services/dunning.py would duplicate existing functionality.

## Verificación de afirmaciones

_Cada cifra del debate recontrastada contra el repo por un verificador con presupuesto de tools SIN límite. '❓' = no comprobable con Read/Glob/Grep (no es un aprobado)._

### ⚠️ parcial · Persist LLM usage tracker to DB instead of in-memory dict
_Core premise holds: llm_usage_tracker.py does use in-memory defaultdict + threading.Lock (blocking in async), and data is lost on restart. However, three peripheral claims are wrong: _dispatch_handlers.py has 25 awaits not '40+', it has 2 sync functions not 'zero sync paths', and the table is 'token_ledger' not 'llm_usage'. None of these invalidate the task's reason to exist, but the quantitative embellishment is notable._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| llm_usage_tracker.py uses an in-memory defaultdict behind a threading.Lock | `Read backend/app/services/llm_usage_tracker.py` | Line 13: _lock = threading.Lock(); Lines 16-18: _store = defaultdict(lambda: defaultdict(...)). Confirmed exactly. | ✅ verified |
| _dispatch_handlers.py has 40+ await calls | `Grep 'await' _dispatch_handlers.py output_mode=count` | 25 await occurrences, not 40+. Materially fewer than claimed. | ❌ refuted |
| _dispatch_handlers.py has zero sync paths | `Grep '^(async )?def ' _dispatch_handlers.py` | 2 sync def functions: _make_error_result (line 28) and _process_gathered_results (line 406). Not zero. | ❌ refuted |
| every record() call blocks the event loop thread, serializing all concurrent tenant requests | `Read llm_usage_tracker.py lines 33-57` | record() is a sync def using 'with _lock:' (threading.Lock). If called from an async context without run_in_executor, it would block the event loop. The function is indeed sync and uses a blocking lock. | ✅ verified |
| All metering data is lost on restart | `Read llm_usage_tracker.py` | _store is a module-level defaultdict in memory. No persistence mechanism. File header says 'Los datos son efímeros (se pierden al reiniciar)'. Confirmed. | ✅ verified |
| Grep asyncio.Lock → 0 matches in the entire backend | `Grep 'asyncio\.Lock' backend/` | No files found. Confirmed 0 matches. | ✅ verified |
| agent_budget.py already queries DB for per-employee spend via TokenLedger | `Read backend/app/services/agent_budget.py` | Lines 21, 57: imports TokenLedger, queries func.sum(TokenLedger.cost_usd) filtered by employee_id and month. Confirmed. | ✅ verified |
| the existing llm_usage table | `Grep 'llm_usage' backend/app/db/models/ + Grep '__tablename__' ai_employees.py` | No 'llm_usage' table exists. The table is 'token_ledger' (__tablename__ = 'token_ledger' at line 106 of ai_employees.py). The rationale names a nonexistent table. | ❌ refuted |

### ❌ refutado · Wire tenant-level LLM budget gate as middleware before agent dispatch
_[auto: premisa central refutada → tarea refutada] The core premise that a tenant-aggregate budget gate is missing is verified. However, the stated trigger — 'config.py defines LLM_MONTHLY_BUDGET_EUR' — is fabricated; config.py has no such variable. The task's justification is built on a phantom config key. The need for a tenant gate stands, but the rationale's starting claim is false, weakening the task's framing._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| config.py defines LLM_MONTHLY_BUDGET_EUR | `Grep for LLM_MONTHLY_BUDGET_EUR and BUDGET/budget in backend/app/core/config.py` | No matches found. config.py contains zero references to any budget variable (EUR or otherwise). | ❌ refuted |
| No code path reads LLM_MONTHLY_BUDGET_EUR at runtime to block calls | `Grep for LLM_MONTHLY_BUDGET_EUR across entire backend` | The variable does not exist at all, so trivially nothing reads it. The claim's premise (that the variable exists but is unread) is false — it simply doesn't exist. | ❌ refuted |
| agent_budget.py enforces per-AIEmployee limits via check_agent_budget | `Read backend/app/services/agent_budget.py` | Confirmed. check_agent_budget (line 80) checks per-employee budget_limit_usd via get_budget_status and returns False + pauses employee when exhausted. | ✅ verified |
| check_agent_budget is called from _dispatch_handlers.py | `Grep for check_agent_budget in _dispatch_handlers.py` | Confirmed. Line 71 imports it, line 109 calls it: `has_budget = await check_agent_budget(str(employee.id), db)`. | ✅ verified |
| There is no tenant-aggregate budget check | `Grep for tenant.*budget\|MONTHLY_BUDGET\|tenant_budget\|aggregate.*budget across backend` | No tenant-level aggregate budget gate found. Only per-employee budget checks exist. The heartbeat notifies about per-employee budget status. Confirmed: no tenant-wide cap enforcement. | ✅ verified |
| budget_guard.py is a backward-compat shim at agents/workers/budget_guard.py | `Read backend/app/agents/workers/budget_guard.py` | Confirmed. File is 18 lines, docstring says 'Backward-compatibility shim — implementacion en services/agent_budget.py', re-exports check_agent_budget/get_budget_status/record_token_usage from services.agent_budget. | ✅ verified |

### ✅ medido · Research: profile LLM client instantiation cost before adding cache to llm_factory.py
_The two factual claims about existing code (lru_cache on mock fallback, ContextVar for tenant propagation) are verified. The core claim is a research proposal ('nobody has profiled ChatOpenAI construction cost') which is inherently unverifiable via static analysis but is a reasonable task premise — it proposes research, not a code change. No factual claims are refuted._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| llm_factory.py already uses lru_cache for the mock fallback | `Read backend/app/core/llm_factory.py` | Line 30: @lru_cache(maxsize=1) decorates _mock_fallback() which returns MockChatModel(). Confirmed. | ✅ verified |
| llm_factory.py uses ContextVar for per-request propagation | `Read backend/app/core/llm_factory.py` | Line 12: from contextvars import ContextVar; Line 27: _tenant_llm_ctx: ContextVar = ContextVar('_tenant_llm_ctx', default=None). Used in set_tenant_llm_context() and get_llm(). Confirmed. | ✅ verified |
| ChatOpenAI construction may just be a dict merge + httpx client reuse internally (instantiation may be cheap, <5ms) | `N/A — requires runtime profiling` | This is the central research question proposed by the task. Cannot be measured via static code inspection of this repo; it depends on langchain_openai internals and runtime behavior. | ❓ unverifiable |
| Adding a TTL-bounded tenant-keyed cache introduces stale-connection risk and memory-leak surface under multi-tenant load | `N/A — architectural judgment` | This is an engineering opinion about a proposed (not yet existing) cache. Cannot be verified or refuted against the repo. | ❓ unverifiable |

### ⚠️ parcial · Extract route-layer email helpers out of agents/email/tools.py into services/email_credentials.py
_Core premise (architecture violation: routes importing private agent helpers that are not @tool-decorated) is verified. However, the count '8 hits' / '8 call sites' is wrong — there are 10 call sites and 6 import lines (16 total references). The task is justified but the quantitative detail is inaccurate._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| messaging.py imports private _get_oauth_token and _get_email_credentials from agents/email/tools.py | `Grep pattern='from.*agents\.email\.tools.*import' in messaging.py` | 6 import statements found at lines 213, 241, 306, 349, 400, 504. All import _get_oauth_token; line 213 also imports _get_email_credentials. | ✅ verified |
| 8 hits (Grep → 8 hits) for these imports/usages | `Grep pattern='_get_oauth_token\|_get_email_credentials' in messaging.py` | 16 total hits: 6 import lines + 10 call sites. No counting method yields 8. | ❌ refuted |
| These credential-fetching functions are not agent tools declared to the LLM, but reusable service logic | `Grep pattern='@tool' and 'def _get_oauth_token\|def _get_email_credentials' in agents/email/tools.py` | _get_email_credentials (line 41) and _get_oauth_token (line 76) are plain async def, NOT decorated with @tool. @tool is on check_inbox, check_unread, send_email. | ✅ verified |
| This violates the architecture rule that agents only export run_agent() | `Verified via grep: messaging.py imports _get_oauth_token/_get_email_credentials directly from agents/email/tools.py` | 6 import statements confirm routes layer directly imports private (_-prefixed) helpers from an agent module, violating CLAUDE.md architecture rules. | ✅ verified |
| The 8 call sites in messaging.py update their imports | `Grep pattern='_get_oauth_token\|_get_email_credentials' in messaging.py, counting call sites (not imports)` | 10 call sites (lines 216,217,218,246,270,309,352,404,424,511), not 8. Plus 6 import lines to update. | ❌ refuted |

**Archivos citados que no existen:** `backend/app/services/email_credentials.py`

### ⚠️ parcial · Audit and wire isConnectivityError across all AI-dependent pages
_The core premise — that isConnectivityError is not wired into pages — is partially true but overstated. GlobalErrorListener.tsx already provides global coverage for unhandled connectivity errors. The real gap is narrower: only pages with explicit catch blocks (mi-equipo ~12, compliance ~3) swallow errors without checking isConnectivityError. Pages like escaner that don't catch are already covered. The '~5-10 pages' count is unverifiable and likely inflated — 2-3 page areas have the actual gap._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| errors.ts infrastructure (AI_DEGRADATION_MESSAGE, isConnectivityError, errorType) is already built | `Read frontend/src/lib/api/errors.ts` | All three exist: AI_DEGRADATION_MESSAGE (line 22), isConnectivityError (line 31), errorType in ApiError constructor (line 10). client.ts imports ApiError and constructs it with errorType on lines 195-198, 222-230. | ✅ verified |
| The gap is wiring isConnectivityError into the pages that call agents — it is not consumed by dashboard pages | `Grep isConnectivityError\|AI_DEGRADATION_MESSAGE in frontend/src (all files)` | Only 2 files use these: errors.ts (definition) and GlobalErrorListener.tsx (global catch). Zero dashboard pages import or use them. However, GlobalErrorListener.tsx does provide a global catch for unhandled connectivity errors via window.onerror/unhandledrejection. The real gap is narrower: only pages with explicit catch blocks that swallow errors (mi-equipo hooks: .catch(() => {}), catch { toast.error() }; compliance: catch(err) { setError(err.message) }) miss the degradation signal. Pages that let errors bubble (like escaner/page.tsx which has no catch) are already covered by the global listener. |  weakened |
| ~5-10 pages call agents and need wiring | `Grep catch blocks across mi-equipo, escaner, compliance pages/hooks` | mi-equipo hooks (useTaskPanel, useMiEquipo) have ~12 catch blocks swallowing errors with generic messages. compliance has 3 catch blocks (ConsultaTab, CalendarioTab, BOETab). escaner/page.tsx has ZERO catch blocks (already covered by GlobalErrorListener). That's 2 page areas with the gap (mi-equipo, compliance), not 5-10 pages. Other pages (banca/useAgentPolling, automatizaciones hooks) may also have catch blocks but weren't listed in files_touched. | ❓ unverifiable |
| mi-equipo, escaner, compliance are AI-dependent dashboard pages | `Grep agent\|orchestrat in those directories` | mi-equipo: calls api.tasks.*, api.aiEmployees.*, api.tasks.chat — AI-dependent. compliance: calls agent endpoints (ConsultaTab, BOETab). escaner: page.tsx references agent-related functionality. All three are AI-dependent. | ✅ verified |

### ✅ medido · Add integration smoke tests for the orchestrator → agent dispatch path
_All core and peripheral claims verified. The integration test directory indeed does not exist (0 files), SC-10 is real and documented, all touched files exist (the NEW file correctly does not exist yet). The only unverifiable item is the dependency-direction prescription, which is a design rule for new code, not a factual claim._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| lessons.md SC-10 documents that multi-agent context passing breaks silently | `Grep SC-10 in tasks/lessons.md + Read lines 206-230` | SC-10 is documented at line 208. It describes ExecutionContext losing response text between multi-step plan steps because _extract_entities only picks up _EXTRACTABLE_KEYS, not free-text markdown. This is a real silent failure (step 2 gets no data from step 1). Claim accurate. | ✅ verified |
| No integration test directory exists today (Glob backend/tests/integration/**/*.py → 0 files) | `Glob backend/tests/integration/**/*.py and backend/tests/integration/**/*` | Both globs returned 0 files. No integration test directory or files exist. | ✅ verified |
| File exists: backend/scripts/smoke_orchestrator.py | `Glob backend/scripts/smoke_orchestrator.py` | File exists. | ✅ verified |
| File exists: backend/tests/integration/test_orchestrator_dispatch.py (NEW) | `Glob backend/tests/integration/**/*` | Does not exist yet — marked as NEW in the task, which is correct. | ✅ verified |
| File exists: backend/app/agents/orchestrator/_dispatch_handlers.py | `Glob backend/app/agents/orchestrator/_dispatch_handlers.py` | File exists. | ✅ verified |
| File exists: backend/app/services/agent_budget.py | `Glob backend/app/services/agent_budget.py` | File exists. | ✅ verified |
| Dispatch handler returns structured AgentResult | `Grep AgentResult in _dispatch_handlers.py` | AgentResult is imported (line 14) and used as return type in multiple functions (lines 68, 228, 267, 289). Claim accurate. | ✅ verified |
| Dependency direction: tests → services → db, never tests → agents directly | `N/A — this is a design prescription for the NEW test file, not a factual claim about existing code` | This is a requirement/design constraint for the new file, not a verifiable claim about existing state. | ❓ unverifiable |

**Archivos citados que no existen:** `backend/tests/integration/test_orchestrator_dispatch.py`

### ❌ refutado · Swap threading.Lock for asyncio.Lock in 4 service modules (mechanical fix)
_The core claim that the fix is 'mechanical: replace threading.Lock with asyncio.Lock, change with to async with' is false. llm_trace.py uses the lock in sync callback methods (BaseCallbackHandler) where asyncio.Lock cannot be used. exec_log_store.py has zero async functions. The lock in llm_trace.py guards file I/O, not trivial dict operations. idempotency.py is 89 LOC, not ~50._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| exec_log_store.py is 45 LOC | `Read backend/app/services/exec_log_store.py` | File has exactly 45 lines. | ✅ verified |
| idempotency.py is ~50 LOC | `Read backend/app/services/idempotency.py` | File has 89 lines, nearly double the claimed ~50. | ❌ refuted |
| All 4 files use threading.Lock | `Read all 4 files` | exec_log_store.py: `_lock = threading.Lock()` (line 12). idempotency.py: `_lock = threading.Lock()` (line 31). llm_cache.py: `_lock = threading.Lock()` (line 26). llm_trace.py: `self._lock = threading.Lock()` (line 104). All confirmed. | ✅ verified |
| The locks guard trivial dict operations in all 4 files | `Read all 4 files, inspecting every `with _lock` / `with self._lock` block` | exec_log_store.py: dict read/write/pop — trivial. idempotency.py: dict read/write/pop — trivial. llm_cache.py: dict read/write/del — trivial. llm_trace.py: the lock guards FILE I/O (`self._today_path().open('a')` at line 120), not just dict operations. This is not a trivial dict operation — it serializes concurrent writes to a JSONL file on disk. | ❌ refuted |
| The fix is mechanical: replace threading.Lock() with asyncio.Lock(), change 'with _lock' to 'async with _lock' | `Read backend/app/core/llm_trace.py — check if lock-using methods are async` | In llm_trace.py, the lock is used inside `_write()` (line 119), which is called from `on_chat_model_start`, `on_llm_end`, `on_llm_error` — all are SYNC methods (they inherit from BaseCallbackHandler, not AsyncCallbackHandler). You cannot use `async with` in a sync method. Swapping to asyncio.Lock in llm_trace.py is NOT mechanical — it would require rearchitecting the callback class to be async. For the other 3 files, idempotency.py and llm_cache.py have sync helper functions (_evict_expired, _evict_oldest) that use `with _lock` and would also need to become async, though their callers are already async. exec_log_store.py has NO async functions at all — every function is sync, so asyncio.Lock cannot be used without making them all async. | ❌ refuted |

### ⚠️ parcial · Add inline amount-cap checks on financial-write agent tools
_All files exist and all three target functions (create_journal_entry, create_invoice, approve_payroll) are confirmed. However, the rationale says tools should 'return AgentResult(success=False)' — in reality AgentResult is only used at the orchestrator/dispatcher layer, not inside domain tool functions. The tool functions would need to import and adopt AgentResult, or use a different error-return pattern. The core premise (add inline cap checks to these three tools) is sound; the AgentResult detail is a minor mismatch in how errors are currently returned from tools._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| create_journal_entry exists as a financial-write agent tool in accounting/tools.py | `Grep 'create_journal_entry' in backend/app/agents/accounting/tools.py` | Found at line 17: 'async def create_journal_entry(' | ✅ verified |
| create_invoice exists as a financial-write agent tool in billing/_invoice_write_tools.py | `Grep 'create_invoice' in backend/app/agents/billing/_invoice_write_tools.py` | Found at line 171: 'async def create_invoice(' and line 229 delegates to _create_invoice_async | ✅ verified |
| approve_payroll exists as a financial-write agent tool in hr/_payroll_crud.py | `Grep 'approve_payroll' in backend/app/agents/hr/_payroll_crud.py` | Found at line 119: 'async def approve_payroll(' and line 136: 'async def _approve_payroll_async(' | ✅ verified |
| No tool_output_validator.py service layer exists currently | `Grep 'tool_output_validator' in backend/` | No files found — confirmed it does not exist | ✅ verified |
| Agents return AgentResult(success=False) on errors | `Grep 'AgentResult' in backend/app/agents/ (files_with_matches) + Read state.py` | AgentResult is a TypedDict in orchestrator/state.py with 'success' field. Used in 20 files, all in orchestrator/dispatchers and workflow agent — NOT in the individual domain tool files (accounting/tools.py, billing/_invoice_write_tools.py, hr/_payroll_crud.py). The tool functions themselves don't currently return AgentResult; they return plain dicts or strings. AgentResult is used at the dispatcher layer. |  weakened |
| An existing exec_log_store exists that could be appended to for audit trail | `Grep 'exec_log_store' in backend/` | Found in 4 files: services/workflow/service.py imports from app.services.exec_log_store, workers/tasks_orchestrator.py, workers/_orchestrator_context.py, and tests/test_service_exec_log.py. The store exists and is operational. | ✅ verified |
| Pre-production with zero customers | `N/A — stated in project memory` | MEMORY.md confirms: 'Estado del proyecto: pre-producción — sin clientes en prod aún' | ✅ verified |

### ❌ refutado · Implement rule-based dunning workflow over Invoice.due_date
_The task's entire premise — that rule-based dunning is a NEW feature that doesn't exist yet — is false. backend/app/services/collections/reminders.py already implements the exact D-3/D+0/D+15/D+30 schedule with 4 email templates, escalation language, interest calculations, DB queries, and an API endpoint. The collections module is labeled F3.9 and is substantially complete. The proposed NEW file services/dunning.py would duplicate existing functionality._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| billing.py already has Invoice.due_date | `Grep 'due_date' in backend/app/db/models/billing.py` | Line 51: due_date = Column(DateTime(timezone=True)) — confirmed. | ✅ verified |
| scheduler.py provides the cron backbone | `Grep 'cron\|schedule\|periodic' in backend/app/services/workflow/scheduler.py` | File exists, has get_active_scheduled_workflows() for schedule_based workflows. It's DB helpers for APScheduler tasks, not a full cron engine itself, but does support the scheduler layer. | ✅ verified |
| agents/email/ handles sending | `Grep 'send\|email' in backend/app/agents/email/tools.py` | send_email function at line 244, build_tools_list at line 272 with real_send_fn. Confirmed. | ✅ verified |
| This is a NEW user-facing feature — email template design, business-rule configuration (which intervals? which escalation language?), and tenant opt-in UX — none of which exist yet | `Read backend/app/services/collections/reminders.py; Read backend/app/api/v1/routes/collections.py` | reminders.py (231 lines) ALREADY implements exactly the D-3/D+0/D+15/D+30 schedule described in the task. It has 4 fully designed email templates (friendly_pre, reminder_due, formal_d15, formal_d30) with escalation language, interest calculations per Ley 3/2004, ReminderStep dataclass, build_reminder_schedule() pure function, and invoices_due_for_reminder() async DB query. API route /collections/due-reminders exists. The __init__.py labels this as F3.9. This is NOT a new feature — it's already substantially built. | ❌ refuted |
| Shipping it 'now' alongside 6 infrastructure items risks half-baking the highest-ROI feature | `Read backend/app/services/collections/__init__.py` | The module already exports ReminderStep, build_reminder_schedule, invoices_due_for_reminder, ClientRiskScore, compute_client_risk, rank_tenant_collections. Both reminder scheduling and risk scoring are implemented. The feature is not half-baked — it's substantially complete. | ❌ refuted |
| F3.9 (predictor de morosidad) is parked as 'ML someday' | `Read backend/app/services/collections/__init__.py lines 1-14` | __init__.py docstring explicitly says: 'Sin ML — heurísticas robustas sobre datos del ERP. Si más adelante hay >500 facturas/cliente... se puede entrenar logistic regression.' The rule-based version is implemented NOW; only ML is deferred. The claim conflates the ML predictor with the rule-based dunning. | ❌ refuted |

**Archivos citados que no existen:** `backend/app/services/dunning.py (NEW)`

### ⚠️ parcial · Add tenant-facing LLM usage dashboard component and API endpoint
_Core premise is solid: llm_usage.py exists with /llm-usage/stats calling get_monthly_stats(). However, the rationale references config.LLM_MONTHLY_BUDGET_EUR as an existing config field to read budget_cap/usage_ratio from — this field does not exist anywhere in the codebase, so it would need to be created (not just 'read from'). The two NEW files (UsageDashboard.tsx, api/ai.ts) correctly don't exist yet._

| Afirmación | Comando | Observado | Veredicto |
|------------|---------|-----------|-----------|
| The backend route ALREADY EXISTS at backend/app/api/v1/routes/llm_usage.py | `Glob: backend/app/api/v1/routes/llm_usage.py` | File exists at backend\app\api\v1\routes\llm_usage.py | ✅ verified |
| llm_usage.py has a /llm-usage/stats endpoint | `Read: backend/app/api/v1/routes/llm_usage.py` | router = APIRouter(prefix="/llm-usage", ...) with @router.get("/stats") — endpoint is /llm-usage/stats. Confirmed. | ✅ verified |
| The /llm-usage/stats endpoint calls llm_usage_tracker.get_monthly_stats() | `Read: backend/app/api/v1/routes/llm_usage.py line 25` | Line 25: stats = llm_usage_tracker.get_monthly_stats(tenant_id, months=months). Confirmed. | ✅ verified |
| Extend the existing route to include budget_cap and usage_ratio fields from config.LLM_MONTHLY_BUDGET_EUR | `Grep: LLM_MONTHLY_BUDGET_EUR in backend/` | No matches found. config.LLM_MONTHLY_BUDGET_EUR does not exist anywhere in the backend codebase. The rationale proposes reading from a config field that hasn't been created yet. | ❌ refuted |
| Creating a new ai_usage.py would be redundant duplication (implying no ai_usage.py exists) | `Glob: backend/app/api/v1/routes/ai_usage.py` | No file found. No ai_usage.py exists, so the claim that creating one would be redundant is consistent — the existing llm_usage.py covers the same domain. | ✅ verified |
| The new frontend api/ai.ts module MUST be re-exported from lib/api.ts per the double-barrel rule | `Read: frontend/src/lib/api.ts` | lib/api.ts uses `export * from './api/index'`, so any new module added to api/ and re-exported from api/index.ts is automatically available. The double-barrel rule is real but the mechanism is now `export *` — no manual re-export in api.ts needed, only in api/index.ts. | ✅ verified |

**Archivos citados que no existen:** `frontend/src/components/ai/UsageDashboard.tsx`, `frontend/src/lib/api/ai.ts`


## Puntos de impacto (archivos por tarea)

- **Persist LLM usage tracker to DB instead of in-memory dict** → `backend/app/services/llm_usage_tracker.py`, `backend/app/services/agent_budget.py`, `backend/app/db/models/ai_employees.py`
- **Research: profile LLM client instantiation cost before adding cache to llm_factory.py** → `backend/app/core/llm_factory.py`
- **Extract route-layer email helpers out of agents/email/tools.py into services/email_credentials.py** → `backend/app/api/v1/routes/messaging.py`, `backend/app/agents/email/tools.py`, `backend/app/services/email_credentials.py (NEW)`
- **Audit and wire isConnectivityError across all AI-dependent pages** → `frontend/src/lib/api/errors.ts`, `frontend/src/lib/api/client.ts`, `frontend/src/app/(dashboard)/mi-equipo/page.tsx`, `frontend/src/app/(dashboard)/escaner/page.tsx`, `frontend/src/app/(dashboard)/compliance/page.tsx`, `frontend/src/app/(dashboard)/error.tsx`
- **Add integration smoke tests for the orchestrator → agent dispatch path** → `backend/scripts/smoke_orchestrator.py`, `backend/tests/integration/test_orchestrator_dispatch.py (NEW)`, `backend/app/agents/orchestrator/_dispatch_handlers.py`, `backend/app/services/agent_budget.py`
- **Add inline amount-cap checks on financial-write agent tools** → `backend/app/agents/accounting/tools.py`, `backend/app/agents/billing/_invoice_write_tools.py`, `backend/app/agents/billing/_invoice_create_async.py`, `backend/app/agents/hr/_payroll_crud.py`
- **Add tenant-facing LLM usage dashboard component and API endpoint** → `backend/app/api/v1/routes/llm_usage.py`, `backend/app/services/llm_usage_tracker.py`, `frontend/src/components/ai/UsageDashboard.tsx (NEW)`, `frontend/src/lib/api/ai.ts (NEW)`, `frontend/src/lib/api.ts`

## 🔭 Visión estratégica

**AutomatizaPyme must become a metered, trust-safe multi-tenant AI platform before onboarding its first paying tenant — the tactical sprint hardens the money path (LLM spend tracking, budget gates, financial-write caps) that justifies the 39€ tier.**

### Hacia dónde encauzarlo

The council debate revealed a project at a specific inflection point: pre-production with substantial domain agents (accounting, billing, HR, email, compliance) already built, but missing the operational scaffolding that turns a demo into a product a CFO would trust with real money. The user persona is a Spanish PyME owner (5-50 employees) who delegates bookkeeping, invoice chasing, and payroll to AI employees — but will never adopt if spend is invisible, financial writes are uncapped, or errors produce cryptic 403s instead of actionable guidance. The distribution channel is a SaaS tier (the 39€ price point producto referenced) where consumption visibility IS the product differentiator against generic automation tools.

The dominant tension in the debate was Conservador vs. Producto: infrastructure hardening versus shipping customer-facing value. The council resolved it correctly — default to infrastructure-first, but insist every infrastructure item has a user-facing surface. The tracker persistence (item 1) feeds the usage dashboard (item 10). The budget gate (item 2) mandates 80%-warning UX, not just a backend guard. The error boundary audit (item 5) ensures AI degradation shows a message, not a crash. This is the right default for pre-production: you cannot ship dunning workflows to tenants who don't yet trust the platform's spend controls. Producto's dunning deferral to next-quarter (item 9) was the pivotal concession — especially since verification revealed the collections/reminders module already implements the D-3/D+0/D+15/D+30 schedule with four email templates, meaning the 'next-quarter' work is wiring and UX polish, not greenfield development.

The moat is vertical integration depth: AutomatizaPyme's agents share a single orchestrator with unified budget controls, execution logging, and credential management across accounting, billing, HR, and email domains. A PyME using separate tools for each domain gets no cross-domain intelligence and no unified spend cap. The architectural discipline the council enforced — routes→services→db dependency direction, agents communicating only through the orchestrator, services owning reusable logic — is what makes this vertical integration maintainable as agent count grows. Estructurador's email helpers extraction (item 4) and the budget gate's correct placement in services/ (not in the backward-compat shim) are not aesthetic preferences; they're load-bearing walls for a system where 6+ agents share credential and budget infrastructure.

The async correctness sweep (items 1, 7) deserves strategic framing beyond 'cleanup.' The entire backend is async, yet five modules use threading.Lock — a pattern that serializes concurrent tenant requests through the event loop. Verification exposed that the 'mechanical swap' claim was overstated (llm_trace.py uses sync BaseCallbackHandler callbacks, exec_log_store.py has zero async functions), but the direction is non-negotiable for multi-tenant concurrency. This is foundational work that must complete before the first tenant hits concurrent agent calls.

### Features futuros propuestos

| Horizonte | Feature | Por qué | Sabios |
|-----------|---------|---------|--------|
| `next-quarter` | **Rule-based dunning activation with tenant opt-in UX** | The collections/reminders module already implements D-3/D+0/D+15/D+30 schedules with four escalation templates and interest calculations per Ley 3/2004 — verification refuted the council's claim this was greenfield. The remaining work is tenant configuration UI (which intervals, which language tone), opt-in toggle per client, and wiring the scheduler to trigger reminders automatically. This is the highest-ROI feature producto identified: automated invoice chasing directly reduces DSO for PyMEs. | producto, simplificador, conservador |
| `next-quarter` | **Human-in-the-loop approval gates for financial writes above configurable thresholds** | Item 8 adds inline amount caps as a stopgap, but the real product need is a configurable approval workflow where the AI employee requests human sign-off for transactions above tenant-defined thresholds. Guardian flagged zero matches for human_in_the_loop or requires_approval across the entire backend. This bridges the trust gap between 'AI assistant' and 'AI employee' — the tenant must feel in control of the money path. | guardian, producto, conservador |
| `next-year` | **Cross-domain AI intelligence: billing→collections→accounting closed loop** | Today each agent domain operates independently. The next differentiation step is closed-loop workflows: an overdue invoice triggers a dunning reminder (email agent), the payment receipt auto-reconciles in accounting (accounting agent), and the client risk score updates in collections. The orchestrator and shared services architecture the council hardened in this sprint is the prerequisite for this cross-domain coordination. | estructurador, modernizador, producto |
| `next-quarter` | **Tenant-facing AI employee performance dashboard with ROI metrics** | Beyond raw LLM token usage (item 10), tenants need to see what their AI employees accomplished: invoices sent, payments collected, journal entries created, hours saved. This transforms the 39€ tier from a cost center into a measurable investment. The exec_log_store and token_ledger already capture the raw data; the gap is aggregation and presentation. | producto, optimizador |

### Hilos de investigación abiertos

- **What is the actual ChatOpenAI instantiation cost under multi-tenant load, and does ContextVar-per-request create measurable overhead versus a tenant-keyed cache?** — The council correctly demoted the llm_factory cache to a research thread (item 3). llm_factory.py already uses lru_cache for mock and ContextVar for tenant propagation. If ChatOpenAI construction is <5ms (as conservador hypothesized), caching adds stale-connection risk for zero gain. But if it's >50ms under concurrent tenant load, the ContextVar-per-request pattern becomes a scaling bottleneck before the first 10 tenants. Profile before committing to either direction.
- **How should the threading.Lock→asyncio.Lock migration handle sync callback handlers (llm_trace.py) and fully-sync modules (exec_log_store.py)?** — Verification refuted the council's claim that the swap is mechanical across all four files. llm_trace.py inherits from BaseCallbackHandler (sync), not AsyncCallbackHandler — asyncio.Lock cannot be used in sync methods without rearchitecting the class. exec_log_store.py has zero async functions. The migration strategy needs per-file analysis: some files need asyncification of their callers, others may need run_in_executor wrapping, and llm_trace.py may need to switch to AsyncCallbackHandler entirely.
- **Does the existing GlobalErrorListener.tsx already cover enough AI-degradation scenarios to make per-page isConnectivityError wiring unnecessary?** — Verification revealed that GlobalErrorListener.tsx catches unhandled connectivity errors via window.onerror/unhandledrejection globally. The real gap is narrower than the council assumed: only pages with explicit catch blocks that swallow errors (mi-equipo ~12, compliance ~3) miss the degradation signal. Pages that let errors bubble are already covered. The audit (item 5) should measure the actual gap before wiring every page — a centralized error boundary enhancement might be simpler than touching 15+ catch blocks.
