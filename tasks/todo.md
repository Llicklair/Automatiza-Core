# P0 — Multi-tenancy hardening (RLS + tenant context async)

**Objetivo:** Eliminar el riesgo crítico de fuga de datos entre tenants. Hoy el aislamiento depende 100% del filtro manual `where(tenant_id == ...)` en cada query. Una sola query olvidada filtra datos de todas las PYMEs. Solución: defensa en profundidad con contextvars + Row-Level Security en Postgres + validación automática.

**Riesgo actual confirmado:** `services/ai/employee_crud.py:298` y patrones similares donde el filtro no es inmediatamente visible.

---

## Fase 1 — Auditoría (1 día)

- [ ] 1.1 Listar todos los modelos con `tenant_id` (SQLAlchemy). Generar `docs/multitenancy/tenant_scoped_tables.md` con la lista completa.
- [ ] 1.2 Identificar tablas globales (sin tenant): `User` (tiene tenant_id pero también es tabla de auth), `Tenant`, tablas de catálogo. Documentar la decisión por tabla.
- [ ] 1.3 Grep de queries potencialmente vulnerables: `select(Model)` sin `.where(...tenant_id...)` en el mismo archivo. Reportar candidatas, NO arreglar todavía (Fase 4 lo hará automático).
- [ ] 1.4 Verificar que todos los `tenant_id` en BD son `UUID` (no mezcla con `Integer`). Si hay mezcla, decidir tipo único antes de RLS.

---

## Fase 2 — Tenant context con contextvars (1 día)

- [ ] 2.1 Crear `backend/app/core/tenant_context.py` con `ContextVar[Optional[UUID]]` y helpers `set_current_tenant(tenant_id)`, `get_current_tenant()`, `require_current_tenant()`.
- [x] 2.2 ~~Middleware FastAPI~~ → Implementado como side effect en `get_current_user` (`core/dependencies.py:36-39`). Más simple que un middleware: aprovecha que toda ruta autenticada pasa por esa dependencia. Las rutas públicas (login, /health) NO setean tenant — comportamiento correcto.
- [ ] 2.3 Propagar a Celery: `task_dispatch.py` debe pasar `tenant_id` como argumento de la tarea. El worker hace `set_current_tenant()` al inicio de cada `@shared_task`.
- [x] 2.4 Propagar a agentes LangGraph. **Estado:** la cadena HTTP request → orquestador (`_init_handlers.py:38`) → dispatcher (`_dispatch_handlers.py:~135`) ya setea el ContextVar antes de invocar al agente, y las tools usan `enforce_tenant` que lee del mismo ContextVar consolidado en Fase 2.1. Los `agent_node` individuales (billing, hr, documents, email, banking) NO setean por sí mismos pero heredan el contexto por asyncio. Añadir defensa adicional en cada `agent_node` se traslada a Fase 5 (auditoría exhaustiva). También revisar en Fase 5 el timing de `chat.py:_build_extra_context` que el subagente flagó como sospechoso.
- [ ] 2.5 Tests unitarios: aislamiento entre requests concurrentes (asyncio.gather con tenants distintos no debe contaminarse).

---

## Fase 3 — Row-Level Security en Postgres (2-3 días)

- [ ] 3.1 Crear rol de aplicación en Postgres: `automatizapyme_app` (sin privilegios de BYPASSRLS). El pool de SQLAlchemy se conectará con este rol, NO con el owner de las tablas.
- [ ] 3.2 Migración Alembic `enable_rls_phase1.py`:
  - **Pendiente de Fase 1 (decisión opción B):** añadir `FOREIGN KEY (tenant_id) REFERENCES tenants(id)` en `generated_uis` y `hr_documents` ANTES de habilitar RLS. Validar que no haya filas huérfanas (`SELECT COUNT(*) FROM generated_uis g LEFT JOIN tenants t ON t.id = g.tenant_id WHERE t.id IS NULL` debe dar 0).
  - Para cada tabla tenant-scoped: `ALTER TABLE x ENABLE ROW LEVEL SECURITY;`
  - `CREATE POLICY tenant_isolation ON x USING (tenant_id = current_setting('app.current_tenant', true)::uuid);`
  - `CREATE POLICY tenant_insert ON x FOR INSERT WITH CHECK (tenant_id = current_setting('app.current_tenant', true)::uuid);`
- [ ] 3.3 Listener SQLAlchemy `before_cursor_execute` que ejecute `SET LOCAL app.current_tenant = '<uuid>'` desde el contextvar antes de cada operación. Si no hay tenant en contexto, lanzar excepción (con whitelist para queries del sistema/health).
- [ ] 3.4 Aplicar primero en entorno de desarrollo. Verificar que las queries normales funcionan (smoke test del dashboard, listado de invoices, alta de empleado).
- [ ] 3.5 Fixtures de test: conectarse como `automatizapyme_app` y verificar que SIN setear `app.current_tenant`, las queries devuelven 0 filas.

---

## Fase 4 — Validación automática en desarrollo (1 día)

- [ ] 4.1 Listener SQLAlchemy `before_execute` que en `ENVIRONMENT=development|test` inspeccione la query: si toca tabla tenant-scoped y NO hay `tenant_id` en `WHERE` ni `app.current_tenant` seteado, registrar warning con stacktrace.
- [ ] 4.2 En tests, convertir el warning en error (pytest fixture).
- [ ] 4.3 Ejecutar la suite completa de tests. Cada warning encontrado se arregla agregando el filtro explícito (defensa en profundidad: aunque RLS lo bloquearía, el filtro explícito mejora rendimiento del query planner).

---

## Fase 5 — Tareas en background y agentes (1 día)

- [ ] 5.1 Auditar `app/workers/` y `app/agents/*/agent.py`. Confirmar que cada entry point setea el tenant context antes de la primera query.
- [ ] 5.2 APScheduler: revisar tareas programadas que iteran sobre todos los tenants. Estas deben usar un patrón explícito `with tenant_context(tid): ...` y NO el rol `automatizapyme_app` por defecto, o usar un rol de superadmin con BYPASSRLS controlado.
- [ ] 5.3 Tests de integración: ejecutar un agente con tenant A y verificar que NO puede acceder a datos de tenant B aunque la query esté mal escrita.

---

## Fase 6 — Rollout (1 día)

- [ ] 6.1 Despliegue en staging. Smoke test manual de los flujos críticos: login, dashboard, alta de invoice, ejecución de agente, generación de reporte.
- [ ] 6.2 Monitorear logs durante 48h en staging buscando: queries bloqueadas por RLS, warnings del listener de Fase 4, latencia de queries (RLS añade overhead — medir).
- [ ] 6.3 Despliegue en producción con migración Alembic. Plan de rollback documentado: `ALTER TABLE x DISABLE ROW LEVEL SECURITY` por tabla.
- [ ] 6.4 Actualizar `ARCHITECTURE.md` y `CLAUDE.md` con la regla: "Toda query a tabla tenant-scoped DEBE incluir filtro `tenant_id` explícito; RLS es defensa secundaria, no excusa para omitirlo".

---

## Criterios de aceptación

1. Un test de integración que conecta como `automatizapyme_app` SIN setear `app.current_tenant` recibe 0 filas en cualquier tabla tenant-scoped.
2. Las queries existentes siguen pasando todos los tests sin cambios funcionales.
3. La latencia P95 del dashboard no aumenta más del 15% respecto al baseline.
4. La suite de tests no emite warnings del listener de Fase 4.
5. Documentación actualizada en `ARCHITECTURE.md`.

---

## Fuera de alcance (queda para después)

- Caché Redis del dashboard (P1 del plan general).
- Repository pattern y Unit of Work (P4).
- Migrar a schema-per-tenant (no necesario con RLS bien hecho).

---

## Antes de empezar — Preguntas para confirmar

1. ¿El proyecto está en producción con clientes reales hoy? Esto define el ritmo del rollout y si conviene feature flag por tenant.
2. ¿Postgres es la BD oficial en todos los entornos (dev, staging, prod)? RLS es específico de Postgres.
3. ¿Existe un job de migración de datos pendiente que requiera bypass de RLS? Si sí, planificar cómo correrlo (rol superadmin temporal).
