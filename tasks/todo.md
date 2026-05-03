# Multi-tenancy hardening — estado final

## Hecho (commit `7de2bf5`)

### Fase 1 — Auditoría
Documento `docs/multitenancy/tenant_scoped_tables.md` con 34 tablas tenant-scoped, 100% UUID, mapa de queries vulnerables. Tras verificación línea-por-línea quedaron como hallazgos reales:
- `node_engine.py:332-345` — añadido filtro `Workflow.tenant_id` defensivo en `_load_workflow` y `_load_execution`.
- `GeneratedUI` y `HRDocument` — añadido `ForeignKey("tenants.id")`.

### Fase 2 — Tenant context centralizado
- `core/tenant_context.py`: ContextVar + `set_current_tenant`, `get_current_tenant`, `require_current_tenant`, `tenant_context()`.
- `agents/tenant_context.py`: consolidado, ahora delega en core (alias retro-compat).
- `core/dependencies.py`: `get_current_user` setea el tenant tras autenticar.
- `workers/tasks_node_engine.py`, `workers/tasks_orchestrator.py`, `workers/tasks_scheduler.py`: setean tenant en sus entry points.
- `tests/test_tenant_context.py`: 8 tests, incluido aislamiento concurrente.

---

## Descartado — Fases 3 a 6 (RLS en Postgres)

**Decisión 2026-05-03:** AutomatizaPyme es **single-tenant local** — cada PYME corre su propia instalación desktop con su propia BD aislada. RLS no aporta seguridad porque no hay otros tenants en la misma BD de los que protegerse.

**Reverts:** commits `9bac626` y `09475c1` (revierten `1bc2a15` y `485803c`). El git log preserva el código por si se construye un SaaS multi-tenant en backend en el futuro — entonces se cherry-pickean.

**Lo que se quitó:**
- `backend/app/db/rls.py` (listener Postgres)
- `backend/app/db/migrations/versions/0003_enable_rls.py` (policies)
- `backend/app/db/{base,session}.py` — llamadas a `register_rls_listener`
- `backend/app/core/tenant_context.py` — `system_context()` / `is_system_context()`
- `backend/tests/test_rls_isolation.py`
- `backend/scripts/setup_postgres_rls.sql`
- `backend/app/workers/tasks_scheduler.py` — wrappers `system_context()`

**Lo que se conservó:** todo lo de Fase 1+2, que es valor real independientemente del modelo (defense in depth, FKs íntegras, ContextVar para propagación limpia).

**Pre-requisitos para reintroducir RLS si surge SaaS:**
1. Existir un escenario multi-tenant real (varios clientes en una misma BD).
2. Crear rol app `pyme_app` (sin BYPASSRLS) además del owner `pyme_user`.
3. Migración Alembic equivalente a la 0003 reverteada.
4. Engine admin separado para scheduler y queries cross-tenant.
5. Verificar overhead del listener `before_cursor_execute` con benchmarks.
