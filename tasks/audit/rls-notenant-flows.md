# RLS fail-closed — no-tenant DB flows audit

Context: today the RLS policy is fail-OPEN
(`tenant_id = app.current_tenant OR app.current_tenant IS NULL OR = ''`).
After switching to fail-CLOSED, any DB statement that runs while the
`current_tenant` ContextVar is empty/None returns ZERO rows (and writes
violate WITH CHECK). The RLS listener (`app/db/rls.py`) re-asserts the GUC on
**every** statement of **every** session (async + sync), reading the ContextVar.

Key infra facts:
- `get_db()` (`app/db/base.py:41`) does **NOT** set tenant — it just yields a session.
  Tenant is set later by the auth dependency, inside the same request/transaction.
- `set_current_tenant()` / `tenant_context()` live in `app/core/tenant_context.py`.
- There is **no `rls_bypass()` helper yet** — it must be created. It needs to set the
  GUC to the bypass sentinel (e.g. a dedicated value the new policy treats as "see all"),
  NOT just `set_current_tenant(None)`, because under fail-closed `None` → zero rows.

Legend: **MUST-BYPASS** = legit global/pre-auth flow that must keep cross-tenant or
no-tenant access; **SAFE** = already sets tenant before any tenant-table query;
**SUSPICIOUS** = queries a tenant table with no tenant set and no clear reason.

---

## 1. Auth / login (user/tenant loaded BEFORE tenant known) — MUST-BYPASS

These query `users` / `tenants` (both have `tenant_id`; `tenants.tenant_id` = own id)
before any tenant can be known. Under fail-closed they return zero rows → total auth lockout.

- `app/core/dependencies.py:62-65` — `get_current_user`: `select(User).where(User.id==...)`
  runs with NO tenant; `set_current_tenant()` only called at line **78**, AFTER the query. **MUST-BYPASS** (the SELECT user lookup).
- `app/core/dependencies.py:108-115` — `get_current_client_portal`: `select(Client)` at line ~115
  runs BEFORE `set_current_tenant(tenant_id)` at line 122. tenant_id comes from token but is
  applied only after the lookup. **MUST-BYPASS** (the lookup SELECT).
- `app/services/auth/service.py:64` — `register`: `select(User).where(email==...)` (pre-tenant, dedupe). **MUST-BYPASS**
- `app/services/auth/service.py:69` — `register`: `select(Tenant).where(nif==...)` (pre-tenant). **MUST-BYPASS**
- `app/services/auth/service.py:113` — `login`: `select(User).where(email==...)` (no tenant yet). **MUST-BYPASS**
- `app/services/auth/service.py:146` — `forgot_password`: `select(User).where(email==...)`. **MUST-BYPASS**
- `app/services/auth/service.py:157` — `forgot_password`: `select(PasswordResetToken)`. **MUST-BYPASS**
- `app/services/auth/service.py:180` — `reset_password`: `select(PasswordResetToken).where(token_hash==...)` (token-only). **MUST-BYPASS**
- `app/services/auth/service.py:192` — `reset_password`: `select(User).where(id==reset_token.user_id)`. **MUST-BYPASS**
- `refresh` (`auth/service.py:128`, route `auth.py:58`) — pure JWT decode, no DB. SAFE (no bypass needed).

Entry routes: `app/api/v1/routes/auth.py:33` register, `:48` login, `:70` forgot, `:80` reset.

---

## 2. Client portal — MUST-BYPASS (token lookup only)

- `app/api/v1/routes/client_portal.py:47` — `select(ClientPortalToken).where(token==...)`: token-based, NO `get_current_*` dep on this endpoint → no tenant set. **MUST-BYPASS**
- `app/api/v1/routes/client_portal.py:108`, `:132` — more `select(ClientPortalToken)` token flows (pre-auth magic-link). **MUST-BYPASS**
- `client_portal.py:158+`, `:215+` — these depend on `get_current_client_portal` which sets tenant. SAFE once #1 portal lookup is bypassed.
- `app/api/v1/routes/portal.py` (employee portal) — all endpoints use `get_current_user` (sets tenant). SAFE.

---

## 3. Webhooks (external callbacks, no JWT) — MUST-BYPASS for the lookup

- `app/api/v1/routes/messaging.py:29` — `telegram_webhook`: verifies secret header, then
  `svc.find_integration_by_chat(db, chat_id)` and `handle_link_command` query by chat_id with
  NO tenant. tenant_id is read from the integration row AFTER. **MUST-BYPASS** (chat→tenant resolution).
- `app/api/v1/routes/signing.py:109` — `autofirma_callback`: explicitly no auth;
  `process_signed_callback(db, session_token, payload)` resolves the signing session by token,
  no tenant in context. **MUST-BYPASS** (session_token resolution).
- `app/api/v1/routes/integrations.py:132` — `google_callback` (OAuth, public):
  `svc.handle_oauth_callback(code, state, ...)` resolves tenant from `state` with no tenant set. **MUST-BYPASS** (state→tenant).
- `app/api/v1/routes/marketing.py:290` — `zernio_callback` (OAuth, public): `_zernio_unstate(state)`
  decodes tenant_id from state, then `select(SocialAccount)` at :314. The query at :314 runs with no
  tenant set in ContextVar (state is decoded locally, never `set_current_tenant`). **MUST-BYPASS** (or set tenant from decoded state before the query — SUSPICIOUS-leaning: it knows the tenant, it just never sets it).
- PSD2 connect/disconnect, email/gmail/gdrive disconnect (`integrations.py`) all use `get_current_user`. SAFE.

---

## 4. Scheduler / workers — mostly SAFE (already wrap per-tenant)

`app/services/scheduler.py:22` `register_jobs` schedules these APScheduler jobs. Workers in
`app/workers/tasks_scheduler.py` already follow the pattern `set_current_tenant(None)` then
`set_current_tenant(str(row.tenant_id))` per item. Under fail-closed the **initial global read**
breaks unless bypassed:

- `tasks_scheduler.py:201/208` — `_check_scheduled_workflows`: `get_active_scheduled_workflows(db)` is a
  CROSS-TENANT read after `set_current_tenant(None)`. Comment says "RLS se desactiva con set_current_tenant(None)" —
  that assumption is FALSE under fail-closed. **MUST-BYPASS** (the global workflow list read; per-wf ops already scoped).
- `tasks_scheduler.py:265/270` — `_catchup_missed_workflows`: same global `get_active_scheduled_workflows`. **MUST-BYPASS** (global read).
- `tasks_scheduler.py:325/332` — `process_recurring_invoices`: `select(RecurringInvoice)` cross-tenant after `set_current_tenant(None)`. **MUST-BYPASS** (global read; per-rec generation already scoped at :340).
- `tasks_scheduler.py:449/452` — `publish_scheduled_posts`: `select(ScheduledPost)` global. **MUST-BYPASS** (global read; per-post at :462 scoped).
- `tasks_scheduler.py:499/504` — `cleanup_stuck_executions`: `select(WorkflowExecution)` global. **MUST-BYPASS** (global read).
- `tasks_scheduler.py:568/571` — `emit_month_end_events`: `select(Tenant.id).where(is_active)` global tenant enumeration. **MUST-BYPASS** (global read; per-tid loop at :579 scoped).
- `tasks_scheduler.py:610` — `send_scheduled_email_campaigns`: global `select` of due campaigns. **MUST-BYPASS** (global read).
- `app/services/workflow/recovery.py:50` — `recover_stale_executions` (called in lifespan startup, main.py):
  `select(Task)` :58, `select(WorkflowExecution)` :82, `select(Task.id)` :93 — all CROSS-TENANT, no tenant set, runs before traffic. **MUST-BYPASS**.
- `app/workers/backfill_alerts.py:34` — `check_pending_verifactu_backfills`: `list_tenants_pending_backfill(db)`
  is a cross-tenant scan with no tenant set; per-tenant loop only logs/track_event. **MUST-BYPASS** (the scan).
- `app/workers/tasks_orchestrator.py:193/196/203`, `:289/292/297` — set tenant from hint/task BEFORE the
  AIEmployee/Task select. Note: at :196 the session opens and the AIEmployee select happens after
  `set_current_tenant(tenant_id_hint)` — if `tenant_id_hint` is None the task lookup (`select(Task)` to learn its
  tenant) would break. **MUST-BYPASS** narrowly: the "load task to discover its tenant" select when hint is absent.
- `app/workers/tasks_node_engine.py:109-122`, `:146-157` — `set_current_tenant(tenant_id)` then load WorkflowExecution;
  if `tenant_id` arg is None it loads the execution to resolve tenant → that resolving select needs bypass. **MUST-BYPASS** (resolve-tenant select when arg None), else SAFE.

---

## 5. Startup / bootstrap / health / license — MUST-BYPASS (startup) / SAFE (license)

- `app/main.py` lifespan: calls `recover_stale_executions()` (see #4 — MUST-BYPASS), then
  `llm_usage_tracker.load_from_db()`, `start_scheduler()`, `refresh_app_license_state()`.
- `app/services/llm_usage_tracker.py` — `load_from_db()` opens `AsyncSessionLocal()` at startup with no tenant;
  if it reads a per-tenant usage table it breaks. **MUST-BYPASS / verify** (cross-tenant usage restore).
- `app/core/license.py:277` `refresh_app_license_state` / `:173` `validate_license` — license state is file/HTTP based
  (cache + license server), no DB tenant tables. SAFE.
- `app/api/v1/routes/license.py` (status/activate/warmup) — no DB tenant access. SAFE.
- `app/api/v1/routes/system.py` — `frontend-errors` (:32) writes diagnostics with no auth: **verify** if target
  table has tenant_id (if so, MUST-BYPASS). backups/restore (:70-120) are filesystem ops. `preconditions`/`backfill`/
  `diagnostic-bundle` (:135,:192,:216) use `get_current_user` → SAFE.

---

## 6. Middleware — NO TenantContextMiddleware exists

- `app/middleware/`: only `license_check.py`, `rate_limit.py`, `request_logger.py`, `scanner_auth.py`,
  `security_headers.py`. **There is NO TenantContextMiddleware.** Tenant is set inside the FastAPI
  dependency `get_current_user` / `get_current_client_portal`, i.e. AFTER routing, in the same request
  transaction. So in the HTTP path the FIRST DB query (the user/portal lookup itself, category #1/#2)
  runs with no tenant → must bypass. Everything after the dependency resolves is SAFE.
- `request_logger.py` / `scanner_auth.py` — verify whether they touch tenant tables before the dep runs.
  scanner_auth likely authenticates a scanner device by token pre-tenant → **verify / likely MUST-BYPASS**.

---

## 7. The 67 direct-session sites — categorization

`grep -rl "AsyncSessionLocal()|SessionLocal()"` → **67 files**. Categorized by how they get tenant:

- **Agent tools** (`app/agents/**/tools.py`, `_*_tools.py`, ~40 files): invoked by the orchestrator/TaskRunner
  which calls `set_current_tenant()` at the worker entry point (`tasks_orchestrator.py`, `tasks_node_engine.py`)
  BEFORE the agent runs. They inherit tenant via ContextVar. **SAFE** (tenant set upstream). They have NO local
  `set_current_tenant` (count 0) by design — they rely on the entry point. Also protected by `enforce_tenant`
  decorator (`app/agents/tenant_context.py`).
- **Scheduler workers** (`tasks_scheduler.py`, `recovery.py`, `backfill_alerts.py`): the per-item work is SAFE,
  the INITIAL global read is MUST-BYPASS — see #4.
- **Services invoked from HTTP** (`services/billing/commands.py`, `services/hr/commands.py`,
  `services/inventory/reorder_service.py`, etc.): receive tenant via ContextVar set by the request dep. **SAFE**,
  but those that open their OWN `AsyncSessionLocal()` inside a request still inherit the ContextVar → SAFE.
- **Cross-cutting/global services — VERIFY:**
  - `app/services/llm_usage_tracker.py` — startup global restore → **MUST-BYPASS** (see #5).
  - `app/services/idempotency.py` — `idempotency_keys` table; check if it has tenant_id and whether keys are
    written under a tenant. If global, **MUST-BYPASS**; the table likely has no tenant_id → unaffected by RLS.
  - `app/services/integration/heartbeat.py` — integration heartbeat poller; if it scans integrations across
    tenants with no context → **MUST-BYPASS / verify**.
  - `app/services/banking/psd2.py` — if a background sync iterates connections cross-tenant → **verify**.
  - `app/services/ai/employee_provisioning.py` — provisioning may run pre/cross tenant → **verify**.
  - `app/db/session.py` (sync `SessionLocal`) — used by sync tools/scripts; same RLS listener installed; any
    script that runs without `tenant_context()` → **verify per call site**.

### SUSPICIOUS (probable real bugs to flag, not blanket-bypass)
- `marketing.py:314` `zernio_callback` — knows the tenant (decoded from state) but never calls
  `set_current_tenant` before `select(SocialAccount)`. Fix = set tenant from decoded state, NOT a blanket bypass.
- Any agent tool that is ALSO reachable from a non-request, non-worker path (e.g. a CLI/script) would run with
  no tenant — those specific invocations are SUSPICIOUS and need an explicit `tenant_context()` at the caller.

---

## Recommended next steps
1. Create `rls_bypass()` context manager in `app/db/rls.py` (or `tenant_context.py`) that sets the GUC to a
   dedicated bypass sentinel the new fail-closed policy treats as "all rows", and restores on exit.
2. Wrap the MUST-BYPASS lookups above — auth/login user/tenant SELECTs, portal/webhook token resolutions, and
   scheduler/recovery/startup global reads.
3. Fix `marketing.py:314` by setting tenant from decoded state instead of bypassing.
4. VERIFY items: `llm_usage_tracker.load_from_db`, `system.py:frontend-errors`, `scanner_auth`, `idempotency`,
   `integration/heartbeat`, `banking/psd2`, `ai/employee_provisioning`, sync `db/session.py` callers.
