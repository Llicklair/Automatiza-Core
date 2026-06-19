# RLS fail-closed — bypass/set wiring changes

Wrapping the no-tenant flows that query/write tenant tables BEFORE any tenant
is set, per `rls-notenant-flows.md`. Tighter option chosen per site (set tenant
when derivable; bypass only when genuinely global/pre-tenant).

Import check (all 7 target modules): **IMPORT_OK**.

## Webhooks / public callbacks

| File:line (post-edit) | Flow | Option | Why |
|---|---|---|---|
| `backend/app/api/v1/routes/messaging.py:50` | `telegram_webhook` `/start <token>` → `handle_link_command` | `rls_bypass()` | Webhook sin JWT; resolución token→tenant es pre-tenant. |
| `backend/app/api/v1/routes/messaging.py:67` | `telegram_webhook` `find_integration_by_chat` | `rls_bypass()` then `set_current_tenant` | chat_id→tenant es pre-tenant (bypass); una vez resuelto, `set_current_tenant(tenant_id)` (L82) scope el resto del handler. |
| `backend/app/api/v1/routes/signing.py:148` | `autofirma_callback` → `process_signed_callback` | `rls_bypass()` | Sin auth (AutoFirma no manda cookies); sesión se resuelve por `session_token` pre-tenant. |
| `backend/app/api/v1/routes/integrations.py:140` | `google_callback` → `handle_oauth_callback` | `rls_bypass()` | El tenant se decodifica del `state` (in-memory) DENTRO del service, que además hace upsert; no disponible antes de llamar → bypass. |
| `backend/app/api/v1/routes/marketing.py:311` | `zernio_callback` `select(SocialAccount)` + upsert | `set_current_tenant` | **Bug latente corregido**: el tenant viene firmado en `state` (`_zernio_unstate`), se conoce ANTES de la query → set (tighter que bypass). |

## Scheduler / startup global reads (initial cross-tenant enumeration only)

| File:line (post-edit) | Flow | Option | Why |
|---|---|---|---|
| `backend/app/workers/tasks_scheduler.py:208` | `_check_scheduled_workflows` `get_active_scheduled_workflows` | `rls_bypass()` | Enumeración global; per-wf loop ya hace `set_current_tenant(wf.tenant_id)`. |
| `backend/app/workers/tasks_scheduler.py:271` | `_catchup_missed_workflows` idem | `rls_bypass()` | Idem; loop per-wf scoped. |
| `backend/app/workers/tasks_scheduler.py:336` | `_process_recurring_invoices` `select(RecurringInvoice)` | `rls_bypass()` | Enumeración global materializada en bypass; generación per-rec scoped en loop. |
| `backend/app/workers/tasks_scheduler.py:459` | `_publish_scheduled_posts` `select(ScheduledPost)` | `rls_bypass()` | Enumeración global; per-post scoped en loop. |
| `backend/app/workers/tasks_scheduler.py:404` | `_cleanup_stuck_executions` get/mark stuck | `rls_bypass()` (todo el cuerpo) | Mantenimiento cross-tenant SIN loop per-tenant (lee y escribe global). |
| `backend/app/workers/tasks_scheduler.py:512` | `_check_failed_workflow_executions` SELECT | `rls_bypass()` (SELECT) + per-item `set_current_tenant` | **No estaba en los 7 del spec pero tiene el MISMO bug**: SELECT cross-tenant + writes per-item (`create_notification`, `ex.notified`) que nunca fijaban tenant. SELECT en bypass; cada item ahora hace `set_current_tenant(ex.tenant_id)`. |
| `backend/app/workers/tasks_scheduler.py:571` | `_emit_month_end_events` `select(Tenant.id)` | `rls_bypass()` | Enumeración global de tenants; loop per-tid scoped. |
| `backend/app/workers/tasks_scheduler.py:613` | `_send_scheduled_email_campaigns` `select(EmailCampaign)` | `rls_bypass()` | Enumeración global; per-campaña scoped en loop. |

## Startup (lifespan, pre-traffic)

| File:line (post-edit) | Flow | Option | Why |
|---|---|---|---|
| `backend/app/services/workflow/recovery.py:54` | `recover_stale_executions` (3 SELECTs + writes + commit) | `with rls_bypass():` envolviendo el `async with` | Reconcilia tasks/executions de TODOS los tenants pre-tráfico; sin loop per-tenant → toda la unidad va en bypass (sync CM fuera del async with). |
| `backend/app/workers/backfill_alerts.py:36` | `check_pending_verifactu_backfills` `list_tenants_pending_backfill` | `rls_bypass()` (scan) | Escaneo cross-tenant pre-tenant; loop posterior solo loggea/trackea. |

## Extra finding (pre-existing bug fixed)

- `backend/app/workers/backfill_alerts.py:20,36` importaba `async_session` de
  `app.db.base`, que SOLO exporta `AsyncSessionLocal`. El módulo crasheaba al
  importar (único consumidor). Corregido a `AsyncSessionLocal`. Necesario para
  que pase el import-check; bug independiente de RLS.

## Files NOT touched (per instructions, already done)

`dependencies.py`, `services/auth/service.py`, `core/tenant_context.py`,
`db/rls.py`, `db/security_bootstrap.py`.
