# Auditoría brutal del backend — 2026-06-10

> ✅ **COMPLETADA 2026-06-11** — 16/16 hallazgos resueltos.
> CRÍTICOS (97e90bd, 6a86a3a, 139da4b) · ALTOS H5-H10 (23b2931, 2475418,
> 37cad07, eb9ad96, b42e652+af9cef2, c831d29) · MEDIOS H11-H14 (8fe917f,
> 5965b7c, 2ab79ae, a6ae0d1) · BAJOS H15-H16 (371cc53; H16 sin acción).
> Bonus: los tests de H8 destaparon 2 bugs reales de vocabulario de estados
> de factura, arreglados en b9f1611.

Pregunta marco: "¿qué haría distinto si lo reescribiera de cero?" → Respuesta corta: **una sola
frontera transaccional (Unit of Work), un módulo compartido de autonomy-gate para agents, y el
scheduler con estado en DB, no en memoria**. Todo lo demás es deuda corregible incrementalmente.

---

## CRÍTICO

### 1. `backup.py` y `backup/legacy_local.py` son el MISMO archivo duplicado (331 líneas × 2)
- **Archivos:** `app/services/backup.py` y `app/services/backup/legacy_local.py` (idénticos: mismo wc, mismo `create_subprocess_exec` en líneas 122 y 313 de ambos).
- **Qué está mal:** código que ejecuta `pg_dump` por subprocess duplicado byte a byte. Un fix de seguridad o de rutas se aplicará a uno y el otro seguirá vivo. Además conviven `backup.py`, `backup_local.py` Y el paquete `backup/` — tres entradas para el mismo concepto.
- **Refactor:** borrar `backup.py`, redirigir imports a `backup/legacy_local.py` (o viceversa), y fusionar `backup_local.py` dentro del paquete. 1 commit, riesgo bajo (grep de imports primero).

### 2. Idempotencia del scheduler vive en memoria → duplicados garantizados tras reinicio
- **Archivos:** `app/workers/tasks_scheduler.py:201` (`IdempotencyGuard(ttl=120)`), `:549`; `app/services/idempotency.py`.
- **Qué está mal:** el guard es in-process. Si la app desktop se reinicia dentro de la ventana del cron (o algún día hay 2 workers), una factura recurrente se emite dos veces. `has_active_execution()` mitiga workflows pero no facturas recurrentes (`Idempotente por tenant+mes vía IdempotencyGuard` — solo en RAM). En un ERP que emite facturas con cadena Verifactu, un duplicado es incidente fiscal.
- **Refactor:** tabla `idempotency_keys (key UNIQUE, expires_at)` + INSERT ... ON CONFLICT DO NOTHING como lock. ~50 líneas + migración.

### 3. `_should_run_now` compara el minuto exacto del tick → ejecuciones perdidas silenciosamente
- **Archivo:** `app/workers/tasks_scheduler.py` (función `_should_run_now`) + `app/services/scheduler.py:64` (`IntervalTrigger(minutes=1)`).
- **Qué está mal:** si el tick de APScheduler se retrasa >60s (suspensión del portátil — es una app desktop—, GC, DB lenta), el cron de ese minuto no coincide y el workflow NO se ejecuta, sin log de error. El patrón correcto es `next_run <= now` contra el `last_execution`.
- **Refactor:** calcular `next_run` desde `get_last_execution()` y disparar si `next_run <= now` (catch-up de 1 ejecución). Ya existe `get_last_execution` — es cambiar la condición.

### 4. 41 `db.commit()` en routes con lógica de negocio dentro (viola tu propia regla de capas)
- **Archivos:** `app/api/v1/routes/marketing.py` (8 commits; el `oauth_callback` hace intercambio de token, resolución de FB Page/IG y upsert de `SocialAccount` — ~80 líneas de negocio en la route), `email_marketing.py` (6), `onboarding_regap.py` (5), `client_portal.py`, `autonomy.py`, `notifications.py`, `onboarding_wizard.py`, `backup_local.py`.
- **Qué está mal:** CLAUDE.md dice "Routes: ZERO business logic" y los dominios nuevos (marketing, onboarding) lo ignoran. Consecuencia real: el flujo OAuth no es testeable sin levantar HTTP, y los commits dispersos impiden una transacción por request.
- **Refactor:** extraer `services/marketing/oauth.py` con `complete_oauth_callback(db, platform, code, state)`; la route queda en ~15 líneas. Repetir dominio a dominio (marketing primero, es el peor).

## ALTO

### 5. 167 usos de `AsyncSessionLocal()` manual en 64 archivos — cada tool abre 1-2 sesiones propias
- **Archivos:** todos los `agents/*/tools.py` y `_*.py` (p.ej. `agents/inventory/tools.py:201` abre una sesión solo para `check_autonomy` y otra para `apply_fn`), `workers/*`, `services/workflow/*`.
- **Qué está mal:** sin frontera transaccional única: una tool que hace 3 escrituras puede fallar a mitad dejando estado parcial committeado. Además cada sesión nueva debe re-aplicar el RLS contextvar — si un worker olvida `set_current_tenant`, la sesión queda sin tenant (RLS bloquea, pero el fallo es silencioso y confuso).
- **Refactor:** helper `agents/shared/db.py` con `async with tool_session() as db:` que aplique tenant-context y commit/rollback únicos. Migrar tool a tool. (No intentar inyectar sesión desde LangGraph: demasiado invasivo.)

### 6. `_gated_batch` / gate de autonomía duplicado por agente
- **Archivos:** `agents/inventory/tools.py:201` y variantes del mismo patrón AUTO/CONFIRM/MANUAL en billing, hr, crm, email, marketing, banking (cada uno con su copia y sus mensajes).
- **Qué está mal:** 6-7 implementaciones del flujo de aprobaciones. Cuando cambie la semántica de CONFIRM (lo hará), habrá drift entre dominios.
- **Refactor:** mover a `agents/shared/autonomy_gate.py` con un único `gated_write(domain, kind, params, summary, confirm, apply_fn)`. Los agents ya tienen `agents/shared/` — está vacío de esto.

### 7. 436 `except Exception`, decenas silenciosos
- **Archivos:** `agents/orchestrator/_plan_handlers.py` (4 catches anidados, líneas 301-389), `routes/marketing.py:205` (`except Exception:` sin log), `agents/orchestrator/dispatchers/documents.py:45`, `core/license.py:63,87`.
- **Qué está mal:** errores de programación (AttributeError, KeyError) se tragan igual que errores de red. El bug histórico de `await db.delete()` (28 sitios) sobrevivió meses precisamente por esto.
- **Refactor:** regla mínima: todo `except Exception` debe tener `logger.exception(...)`. Pasada con grep + lint rule (`ruff` BLE001/`try-except-pass`). No hace falta tocar la lógica.

### 8. Cobertura de tests invertida respecto al riesgo: billing/banking con 2 archivos, workflow con 15
- **Datos:** 198 archivos de test. Por nombre: workflow 15, hr 5, marketing 5 — pero **billing 2, banking 2, documents 2, treasury 2**. Los dominios que mueven dinero y cadena Verifactu son los menos testeados directamente.
- **Refactor:** antes del piloto, suite dirigida a `services/billing/commands.py` (683 líneas), `verifactu_chain.py` y `numbering.py` (concurrencia de numeración) y `services/banking/service.py` (auto_reconcile). Objetivo: 1 archivo de test por archivo de comandos.

### 9. Módulos dios (>700 líneas) concentrados en los dominios core
- **Archivos:** `services/hr/queries.py` (841), `services/sales/commands.py` (833), `routes/hr.py` (810 — ~40 endpoints, incluida generación de PDFs de finiquito en la route), `agents/orchestrator/classifier.py` (757), `services/analytics/dashboard.py` (718).
- **Qué está mal:** `routes/hr.py` mezcla CRUD de empleados, nóminas, documentos y 3 generadores de PDF. `classifier.py` con 757 líneas es el cuello de botella cognitivo del Coordinador.
- **Refactor:** dividir `routes/hr.py` en `hr_employees.py` / `hr_payrolls.py` / `hr_documents.py` (mismo prefix, 3 routers). `classifier.py`: extraer las tablas de keywords/few-shots a un módulo de datos.

### 10. Agregaciones en Python sobre cargas completas en memoria
- **Archivos:** `services/analytics/dashboard.py:276-288` (carga TODAS las nóminas y transacciones bancarias del periodo con `.scalars().all()` y suma en Python; el archivo tiene 168 `.all()`), `services/banking/service.py:306-356` (`get_reconciliation_suggestions` = producto cartesiano txs × invoices en memoria).
- **Qué está mal:** con 2 años de datos de una pyme real (10-50k movimientos) el dashboard y la conciliación degradan de forma no lineal.
- **Refactor:** dashboard → `func.sum()/group_by` en SQL (el propio archivo ya lo hace en otras queries, es inconsistencia interna). Conciliación → pre-filtrar invoices por rango de importe ±5% por tx en SQL.

## MEDIO

### 11. Datos DEMO aleatorios generados desde el servicio de producción
- **Archivo:** `services/banking/service.py:61-98` — `sync_transactions` inserta 5 movimientos `random.uniform(-500,1500)` con `[DEMO]` cuando PSD2 no está configurado.
- **Riesgo:** un usuario piloto pulsa "sincronizar banco" y ve movimientos inventados en su ERP contable. El prefijo `[DEMO]` filtra analíticas pero no la UI de conciliación.
- **Refactor:** devolver 409 "PSD2 no configurado" por defecto; mover la generación demo a `scripts/seed_user_data.py` o detrás de un flag explícito de settings.

### 12. SQL por f-string en RLS (mitigado pero patrón peligroso)
- **Archivo:** `app/db/rls.py:45` — `text(f"SET LOCAL app.current_tenant = '{parsed}'")`. Hoy es seguro (re-parseado por `UUID()`), pero es el único f-string SQL del repo y cualquier copy-paste futuro hereda el patrón sin la validación.
- **Refactor:** usar `SELECT set_config('app.current_tenant', :tid, true)` con bind param. 3 líneas.

### 13. `_infer_domain_from_text` — routing por keywords con default `"billing"`
- **Archivo:** `app/workers/tasks_scheduler.py` — workflows programados cuyo texto no matchea ninguna keyword van al agente de billing por defecto. Un workflow de "enviar resumen semanal" acabaría en billing.
- **Refactor:** default a `"chat"`/orchestrator (que ya clasifica con LLM) en lugar de billing, o persistir el dominio elegido al crear el workflow (parse-nl ya lo conoce).

### 14. Raíz de `services/` con ~25 archivos sueltos y solapes de nombre
- **Ejemplos:** `autonomy.py` + `autonomy_gate.py`; `backup.py` + `backup_local.py` + `backup/`; `email_sender.py` + `email_credentials.py` + `email/` + `email_ai/` + `email_marketing/`; `scheduler.py` (APScheduler) vs `workflow/scheduler.py` (queries).
- **Refactor:** consolidar por dominio en sus paquetes (el correo: 5 ubicaciones → `services/email/`). Hacerlo módulo a módulo con `gitnexus_rename`, no big-bang.

## BAJO

### 15. `routes/admin.py:67,137` ejecuta subprocesos desde un endpoint
- Verificar que está protegido por rol admin y que los args nunca derivan de input del usuario. Si es solo para la app desktop local, documentarlo en el módulo.

### 16. Deuda declarada honesta (poca y localizada)
- Solo 2 TODOs reales: `services/i18n/tenant_locale.py:37` (locale hardcoded por tenant) y `services/reports/modelos_aeat.py:228` (gap documentado del 303 — coincide con la auditoría pilot-readiness). El repo está limpio de FIXME/HACK — punto a favor.

---

## Si lo reescribiera de cero (traducido a refactors)
1. **Unit of Work**: una transacción por request/tool (hallazgos 4, 5).
2. **Gate de autonomía único** en `agents/shared/` (6).
3. **Scheduler durable**: idempotencia y catch-up en DB (2, 3).
4. **Tests proporcionales al riesgo**: billing/banking primero (8).
5. **Un paquete por dominio**, sin archivos sueltos ni duplicados en `services/` (1, 14).
