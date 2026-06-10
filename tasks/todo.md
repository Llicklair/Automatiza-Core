# Tareas activas — AutomatizaCore

Última actualización: 2026-06-11

---

## Auditoría brutal del backend — ✅ COMPLETADA 2026-06-11

`tasks/auditoria_brutal_backend.md`: 16/16 hallazgos resueltos en commits
atómicos (1 por hallazgo), tests dirigidos verdes en cada uno.

- [x] **CRÍTICOS 1-3**: backup duplicado, idempotencia en DB (`idempotency_keys`,
  migración 0056), catch-up del scheduler (`_next_due_run`).
- [x] **ALTOS 5-10**: `tool_session()` para RLS en tools (piloto inventory),
  gate de autonomía unificado (`evaluate_autonomy`), excepts silenciosos con
  log (ruff S110/S112), tests billing/banking, hr.py → 4 sub-routers +
  classifier_data.py, agregaciones a SQL.
- [x] **MEDIOS 11-14**: sync banco sin demo (409 + flag `BANKING_DEMO_SYNC`),
  RLS con `set_config` bind param, default de dominio → "chat", email
  consolidado en `services/email/`.
- [x] **BAJOS 15-16**: admin.py verificado y documentado; H16 informativo.
- [x] **Bonus** (b9f1611): vocabulario de estados de Invoice unificado con la
  máquina de estados — `auto_reconcile` ya marca facturas como pagadas y el
  dashboard deja de mostrar "Pendientes" a 0.

Pendiente relacionado (no aprobado): migración incremental del resto de
agentes a `tool_session()`; extraer lógica de negocio de routes con muchos
commits (hallazgo 4 se resolvió solo para el alcance crítico); observación
menor: `run_recurring` numera `REC-<timestamp>` fuera de la serie correlativa.

---

## Auditoría frontend/UIX — ✅ quick-wins COMPLETADOS 2026-06-11

`tasks/auditoria_brutal_frontend_uix.md`: rondas 4664abd/b126a3a (#5, #8-EmptyState,
#2 parcial) + esta ronda, 1 commit por hallazgo:

- [x] **#1 i18n fachada** (2744a34): solo "es" en el selector hasta tener
  traducciones reales; cookies heredadas hacen fallback a es.
- [x] **#2 marketing** (d6f36f7): crear/publicar/eliminar post con toast.error.
- [x] **#12 sonner** (2714dcb): **bonus — el toast store no tenía renderer**,
  todos los toast.* del repo eran invisibles. Nuevo `ToastContainer` en el
  layout; sonner eliminado (dep + wrapper).
- [x] **#4 alert/confirm nativos** (406affc): 16 callsites → showConfirm/toast.
- [x] **#8 PageHeader** (5dacc49): ui/PageHeader borrado, shared/ es el canónico.
- [x] **#3 loading.tsx** (7a28add): 10 rutas frecuentes con spinner estándar.

- [x] **#9 páginas monstruo** (2026-06-11, 7 commits): troceadas al patrón
  `_components/`/`_hooks/`, pure-move, 5.209 → ~906 líneas de page.tsx —
  marketing 743→63 (e84eb61), analitica 969→163 (0fd3a2f), portal 763→145
  (f868429), correos 660→145 (3ec520b), usuarios 609→179 (b62e1a2),
  clientes 537→153 (e0c743a), email-marketing 528→58 (9eb154a).
  tsc por página + next build final verde. Pendiente anotado: doble carga
  de `accounts()` entre TabCuentas/TabCrear (marketing).

- [x] **#10 polling** (2026-06-11): hook `lib/hooks/usePolling` con pausa en
  pestaña oculta + 7 tests (b8d3886); ApprovalsTab → push WS approval_created
  + respaldo 60s, ActivityTab/usePendingApprovalsCount migrados (dc8eb92);
  6 polls continuos migrados, layout ahora reactivo a hydrated/token
  (7619fdc). Polls acotados OAuth/tasks y UI ticks intactos a propósito.

Pendiente (proyectos, no aprobados): #7 a11y, #11 tokens de
diseño/PageContainer, #6 tabs unificados, migración i18n real por
módulos, alert de `portal-cliente/page.tsx` (necesita ToastContainer
en su layout propio).

---

## Plan activo (2026-06-09) — Ciclo de vida de tokens OAuth en Marketing

Objetivo: que los posts programados dejen de fallar para siempre cuando el token
caduca, y que los tokens dejen de guardarse en texto plano. Es el mismo trozo de
código (guardar/leer `access_token`), así que se arreglan juntos.

> Pre-producción (sin clientes). `refresh_token` y `token_expires_at` YA existen
> en el modelo → **sin migración Alembic** (evitamos el gotcha de version_num).

### Mecánica de refresh por plataforma

| Plataforma | Vida token | Renovación |
|-----------|-----------|------------|
| Twitter/X | ~2 h | `grant_type=refresh_token` (scope `offline.access` ya pedido). **Rota** el refresh_token → guardar el nuevo |
| LinkedIn | ~60 d | `grant_type=refresh_token` si hay; si no → marcar "reconecta" |
| Facebook | →60 d | sin refresh_token: re-intercambio `fb_exchange_token` del access_token |
| Instagram | 60 d | sin refresh_token: `GET /refresh_access_token?grant_type=ig_refresh_token` (token >24 h) |

### Cambios — ✅ COMPLETADO 2026-06-09 (18 tests verdes; agent+encryption sin regresión)

- [x] **1. `services/encryption.py`** — `encrypt_str(s)` / `decrypt_str(s)` sobre
  `get_fernet()`. `decrypt_str`: si `InvalidToken` → devuelve el valor tal cual +
  warning (compat filas legacy en plano, sin script de migración).
- [x] **2. `services/marketing/oauth_tokens.py`** (NUEVO) — choke point único:
  `ensure_valid_token(account, db) -> str | None` (descifra; si expira <5 min →
  refresh por plataforma → persiste cifrado → devuelve nuevo; si falla → None) +
  `_refresh_twitter/_linkedin/_facebook/_instagram`.
- [x] **3. `services/marketing/publisher.py`** — usa `ensure_valid_token`; si
  None → `failed` con "Token caducado: reconecta la cuenta".
- [x] **4. `api/v1/routes/marketing.py`** — cifra access_token + refresh_token
  con `encrypt_str` en el upsert del callback OAuth.
- [x] **5. Tests** `tests/test_marketing_tokens.py` — roundtrip cifrado +
  `ensure_valid_token` con httpx mockeado (válido/caducado+ok/caducado+sin-refresh).

### Facebook Page tokens — ✅ COMPLETADO 2026-06-09 (28 tests verdes)
Publicar en FB exigía Page token (Meta retiró los perfiles personales en 2018).
`_resolve_facebook_page` en routes cambia el user token por el Page token (larga
duración, sin expiración) de la primera página gestionada; scope `pages_show_list`
añadido. El publisher NO cambia: con Page token `/me/feed` = feed de la Página.

### Reintentos + backoff — ✅ COMPLETADO 2026-06-09 (44 tests verdes)
`publish_post` ahora devuelve `PublishResult(ok, transient)`; transitorios =
429/5xx/red. Scheduler: `_handle_publish_result` reprograma transitorios con
backoff exponencial (5→10→20→40→80 min, máx 5 intentos) vía nueva columna
`scheduled_posts.retry_count` (migración **0050_post_retry_count**); permanentes
quedan `failed`. ⚠️ Aplicar migración: `alembic upgrade head` en la BD real.

### Instagram → Instagram Graph API — ✅ COMPLETADO 2026-06-09
Antes usaba `graph.instagram.com` + Basic Display (solo lectura) → no publicaba.
Ahora: OAuth vía Facebook (scopes `instagram_basic,instagram_content_publish,
pages_show_list`), `_resolve_instagram_account` localiza la cuenta IG Business
vinculada a una Página (reusa `_facebook_pages`), y `_publish_instagram` publica
por `graph.facebook.com/{ig-user-id}/media[_publish]` con el Page token.
⚠️ Verificación real exige app Meta + cuenta IG Business + (para producción)
App Review del permiso `instagram_content_publish`.

### Fuera de alcance (siguientes pasos)
- Selector de página/cuenta cuando el usuario gestiona varias (ahora se toma la
  primera con IG vinculada / la primera página).
- Verificación end-to-end contra Meta (app + páginas/cuentas de prueba).
- Subida de imagen propia (hoy IG/FB esperan una URL pública de imagen).

### Verificación
`pytest backend/tests/test_marketing_tokens.py -v` · import backend OK · smoke:
forzar `token_expires_at` en pasado y confirmar path refresh/`failed`.

---

## Consejo Report 2026-06-01 — Implementación (en curso)

Alcance aprobado: **todo el plan (1,4,5,6,9,10) + extraer hooks primero**.
Constraints: #3 hub files congelados · #7 descartado · #11 diferido.

Orden de ejecución (menor → mayor riesgo):

- [x] **#9** Allocation muerta en `llm_factory.get_llm` → singleton perezoso `_mock_fallback()` (lru_cache). SAFE. ✅
- [x] **Refactor seam** en `DashboardLayout`: extraído `useAuthGuard` (NEW en `src/hooks/`) + WS migrado a `useNotificationSocket` (con flag `enabled` para hidratación). ✅
- [x] **#6** Degradación LLM visible: `errors.ts` (`isConnectivityError`+`AI_DEGRADATION_MESSAGE`) + `GlobalErrorListener` muestra toast (throttle 30s). NO se sobrecargó `AIDisclosureBanner` (banner legal AI Act ≠ estado de disponibilidad). ✅
- [x] **#4** Spending cap + alerta 80%: `get_budget_status` en `agent_budget.py` (estados ok/warning/exhausted), endpoint PATCH `/ai-employees/{id}/budget` + `aiEmployees.updateBudget`. Dashboard de coste = diferido (next-quarter). ✅
- [x] **#10** WS push `budget_warning` (80%) y `budget_exhausted` (100%) desde heartbeat; handlers en layout.tsx. ✅
- [x] **#1** `smoke_orchestrator.py` reforzado con veredicto PASS/FAIL + `--strict` (exit 1). ✅ código y **ejecutado end-to-end** contra LLM real + DB portable (PG 15.10 en 5433): `ambiguous`/`reports_month`/`impossible` → 3 PASS, exit codes OK. 2 bugs propios arreglados (commit `46a3b40`). Batería completa disponible: `python backend/scripts/smoke_orchestrator.py --strict` (DATABASE_URL=postgresql+asyncpg://pyme_user:pyme_pass@localhost:5433/pyme_db).
- [~] **#5** Auto-update: wiring de código OK + `desktop/package.json` `publish` corregido a `Llicklair/Automatiza-core` (commit `5e56935`). **Release NO publicada** (decisión usuario 2026-06-01: "no publicar aún"). Bloqueantes para el runtime:
  1. **Rebuild obligatorio**: el `app-update.yml` se hornea en el instalador en build-time; el `.exe` del 26-abr (`desktop/dist/`) tiene el owner placeholder → inservible. Hace falta `cd frontend && npm run build` luego `cd desktop && npm run dist`.
  2. **Repo privado**: electron-updater (provider github) no puede actualizar clientes desde un repo privado sin token embebido (inseguro). Para distribución real → repo de releases **público** (p.ej. `automatizacore-releases`) o canal alternativo (S3/genérico).
  3. **`.env` horneado**: `build.extraResources` copia `../.env` dentro del instalador. Sanear secretos (API keys, SECRET_KEY) antes de cualquier release distribuible; producción debe usar placeholders + Electron safeStorage.

Notas de verificación: `orchestrator/tools.py` NO existe (no tocado); DashboardLayout perf-claim refutada (zustand ya aísla) → refactor por SRP/seams. tsc frontend ✅; `test_planner_custom_agents` 11/11 ✅.

---

## Roadmap 11 mejoras — alineado 2026-05-21

**Decisión usuario**: orden Fase 1 → 2 → 3, **sin servicios externos de pago** (eIDAS con AutoFirma del Estado, no QTSP).

### Fase 1 — Quick wins en código (objetivo: 1-2 sem)

- [~] **F1.1 Audit Coordinador exhaustivo** — script `scripts/audit_domain_completeness.py` ✅ creado 2026-05-20. `team` eliminado ✅. Falta: ejecutar audit completo y cerrar cualquier asimetría residual (`VALID_DOMAINS` × `DISPATCHER_MAP` × `_KEYWORD_MAP` × tools).
- [~] **F1.2 Contrato AIEmployee con 4 capacidades reales** — migración 0029 ✅ aplicada. Faltan: (a) tabla `employee_memory` + RAG filter por employee, (b) UI split Empleado/Perfil, (c) data-migration de customs existentes (líneas 75-83).
- [⚠️ ACCIÓN USUARIO] **F1.3 OAuth Google → Production mode** — bloqueante para piloto.
  Pasos exactos (30 s):
  1. https://console.cloud.google.com/apis/credentials/consent
  2. Seleccionar el proyecto OAuth de AutomatizaCore
  3. En "Publishing status" pulsar **"PUBLISH APP"** → "Confirm"
  4. Estado pasa de *Testing* a *In production* (sin verificar).
  Resultado: refresh tokens dejan de caducar a 7 días, los usuarios fuera del listado Test users pueden hacer login (ven warning "Google hasn't verified" — aceptable hasta tener 5+ clientes y meterse en OAuth verification, que es F1.3-bis cuando toque).
- [ ] **F1.4 Asistente fiscal preventivo** — cruce facturas recibidas vs 303 simulado antes de cerrar trimestre, alerta de IVA deducible olvidado, IRPF retenido descuadrado, etc. Reusa `services/aeat/` + agente compliance. Output: nuevo widget en `/impuestos` + push notif.

### Fase 2 — Subir nivel a motores ya construidos (objetivo: 3-4 sem)

- [ ] **F2.5 OCR con aprendizaje por proveedor** — template store en BD por NIF emisor. Primera vez: extracción LLM + guarda layout (bounding boxes de campos clave). Siguientes facturas del mismo NIF: extracción regex sobre el layout aprendido, sin LLM. Meta: >95% precisión, ~0 tokens en proveedores repetidos.
- [ ] **F2.6 Conciliación bancaria explicable** — `services/banking/reconciliation.py` ya tiene scoring (commit 581068a). Falta: sugerencia "Este movimiento = factura #1234 porque {monto exacto, fecha ±3d, concepto contiene NIF}" + un-click aceptar/rechazar + aprendizaje del rechazo.
- [ ] **F2.7 Tesorería Beta → Producción** — cashflow proyectado real (cobros pendientes + pagos previstos), remesas SEPA XML (Pain.001.001.03 cobros, Pain.008.001.02 adeudos), simulador de tesorería.
- [ ] **F2.8 Modelo 100 sociedades** — mismo patrón que 303 (builder + presentación AEAT + WORM). Cubre S.L. enteras, no solo autónomos.

### Fase 3 — Capacidades nuevas con dependencias externas (objetivo: 1-3 meses)

- [ ] **F3.9 Inteligencia de cobros** — predictor de morosidad sobre histórico (días-medios-cobro por cliente, % facturas vencidas, ticket medio). Recordatorios escalonados: aviso amistoso D-3, recordatorio D+0, requerimiento D+15, intereses D+30. ML simple (logistic regression sobre features de cliente) si no hay datos suficientes → ranking por reglas.
- [ ] **F3.10 Marketplace de workflows** — catálogo curado + import/export YAML + moderación. Empaqueta workflows existentes (`gestoria_mensual`, `cierre_trimestral`) como plantillas reutilizables. Network effect sin centralizar datos.
- [ ] **F3.11 Firma electrónica eIDAS (AutoFirma)** — integración con AutoFirma del Estado (gratis). RRHH ya genera contratos, falta: invocar AutoFirma → certificado FNMT del usuario → PAdES (PDF firmado) + sello de tiempo TSA gratuito @firma. Sustituye Signaturit en escenarios B2B simples.

---

---

## Decisión arquitectónica 2026-05-20 — Principio ERP + Contrato del AIEmployee custom

**Contexto**: revisión de tres dudas de diseño (sección AEAT, garantías del
principio ERP "IA accede a todo", razón de ser de los AIEmployees custom).

**Decisiones**:

1. **Sección "Cumplimiento fiscal ES (AEAT)" unificada** — agrupa Verifactu,
   SII, Factura electrónica (Facturae B2B Crea y Crece + B2G FACe) y modelos
   periódicos (303, 390, 111, 130, 347, 349). Piezas compartidas (NIF/CIF,
   firma, XAdES, WORM chain) no se duplican.

2. **El "agente general" del principio ERP es el Coordinador existente**
   (`agents/orchestrator/`, inversión de nombre con `services/workflow/` ya
   documentada en CLAUDE.md). No hace falta crear un agente nuevo — hace
   falta **auditar exhaustividad**. Tres puntos de sincronización obligatorios
   ([lessons.md:81](lessons.md#L81)):
   - `VALID_DOMAINS` (state.py)
   - `DISPATCHER_MAP` (dispatchers/__init__.py)
   - `_KEYWORD_MAP` / `_STRONG_KEYWORDS` (classifier.py)

   **Hallazgo inmediato** (descubierto preparando el audit): `team` está en
   `DISPATCHER_MAP` pero NO en `VALID_DOMAINS` → dominio inalcanzable
   silenciosamente. Mismo patrón antipatrón que SC-4 (reports).

3. **Contrato mínimo del AIEmployee custom**: para justificar existir frente
   a `default + system_prompt_addendum`, debe aportar al menos **2 de 4**
   capacidades. Si solo aporta tono/expertise textual → se degrada a
   "Perfil" (UI más simple, sin la promesa de autonomía).

   | Capacidad | Campo BD | Tipo |
   |---|---|---|
   | Scope filter persistente | `scope` | JSONB nullable |
   | Memoria persistente | `memory_enabled` + tabla `employee_memory` | bool + tabla |
   | Knowledge base privada | `knowledge_enabled` + filtro RAG por employee | bool |
   | Workflows predefinidos | `workflows` | JSONB nullable |

   El bug Yolanda Sánchez ([lessons.md:114](lessons.md#L114)) — custom
   roto que intercepta routing del builtin con cero valor añadido — es
   exactamente lo que este contrato previene.

### Tareas concretas derivadas

- [ ] **Audit script `scripts/audit_domain_completeness.py`** ✅ CREADO 2026-05-20.
  Cruza VALID_DOMAINS × DISPATCHER_MAP × _KEYWORD_MAP × tools registradas en
  `tool_registry.py`. Salida tabla + exit code 1 si hay asimetría. Ejecutar
  en pre-commit y antes de cualquier PR que añada un dominio nuevo.

- [ ] **Migración `0029_aiemployee_contract`** ✅ CREADA 2026-05-20.
  Añade columnas `scope` (JSONB), `memory_enabled` (Bool default False),
  `knowledge_enabled` (Bool default False), `workflows` (JSONB) a
  `ai_employees`. Modelo SQLAlchemy actualizado. Tablas `employee_memory` y
  filtro RAG por employee se introducen en migraciones posteriores cuando
  toque implementar las capacidades.

- [x] **Eliminado `team` de DISPATCHER_MAP** ✅ 2026-05-20.
  `_dispatch_team` era dead code (zero callers externos). Removidas las 4
  referencias en `dispatchers/__init__.py` + función borrada en `misc.py`.
  Audit script vuelve a 0 críticos.

- [x] **Migración 0028 + 0029 aplicada en BD del usuario** ✅ 2026-05-20.
  alembic_version: `0029_aiemployee_contract`. Dedup previo necesario:
  smoke testing había creado 6 clientes duplicados en tenant
  "AutomatizaCore" (9cd49fbb) que bloqueaban 0028. Mergeados 4 grupos
  coherentes + resuelto el caso B11223344 (NIF reasignado: Tech Innovations
  pasó a NIF=NULL, Clínica Dental Montserrat quedó como único owner del NIF).
  Total: 41 FKs repuntadas, 5 clientes borrados, 1 cliente con NIF a NULL.

- [ ] **UI: split "Empleado IA" vs "Perfil"** — al crear un empleado custom,
  formulario obliga a marcar ≥2 de las 4 capacidades del contrato; si solo
  tono/expertise, el flujo redirige al alta de "Perfil". Pendiente de
  diseño UX (no bloqueante para backend).

- [ ] **Aplicar el contrato a customs existentes**: auditoría DB de los
  AIEmployees actuales (`is_builtin=False`) — los que no cumplan el contrato
  se marcan como "Perfil" en una migración data-only o se rellenan con
  scope/workflows si el usuario los reconoce como verdaderos empleados.

---

## Pendiente accionable

### Bugs abiertos

- [x] **Bug cleanup tasks vs audit_log WORM** ✅ RESUELTO 2026-05-19 (iteración tarde).
  Fix: soft-delete en `Task` (nueva columna `is_deleted` + migración
  `0027_tasks_is_deleted`). El servicio `cleanup_tasks` ya no DELETE; marca
  `is_deleted=True` y deja audit_log intacto (cumplimiento WORM preservado).
  Consultas (`list_tasks`, `get_task`, `_build_conversation_history`,
  `_load_recent_tasks_context`) ahora filtran `is_deleted=False`. Cubierto por
  7 tests nuevos en `tests/test_service_workflow_task.py`. Docstring del
  endpoint actualizado para reflejar el nuevo contrato.

- [x] **Bug PDF timeout** ✅ RESUELTO 2026-05-19. Causa raíz: prompts
  "genera PDF" hacen al coordinator planificar 2+ steps. Step 1 (RAG) crea el
  PDF OK. Step 2 invoca un AIEmployee custom (yolanda, CFO) que recibe el
  contexto enriquecido del step previo (response_preview de 800 chars con todo
  el markdown del PDF). El LLM custom tarda **76s** procesando ese prompt grande
  — el timeout previo de 90s del custom dispatch (SC-9) lo cortaba al borde →
  task marcada failed pese al PDF ya generado.

  **Fixes aplicados** (3):
  1. `_dispatch_handlers.py` — timeout custom dispatch 90s → 180s + mensaje de
     error actualizado.
  2. `execution_context.py` — `response_preview` 800 → 400 chars (acorta el
     prompt al siguiente step → reduce latencia LLM ~30%).
  3. `services/pdf/__init__.py` — circular import (SC-12) arreglado con
     `__getattr__` lazy. Necesario para diagnosticar el bug desde scripts
     standalone; mejora también la robustez de imports en general.

  Verificación: test aislado `c:\tmp\test_yolanda_isolated.py` reproduce el flow
  step 1 → step 2 con contexto enriquecido. Antes fail al timeout 90s, ahora
  completa en ~76s sin problemas.

  ⚠️ **Para que tome efecto**: cerrar AutomatizaCore.exe y volver a abrir (el
  backend Python embebido por Electron tiene que reiniciarse para recoger los
  cambios).

- [x] **SC-12** ✅ RESUELTO 2026-05-19. Circular import en `app.services.pdf` ↔
  `app.services.pdf_reports` arreglado con `__getattr__` (PEP 562) en
  `pdf/__init__.py`. Los re-exports `generate_cashflow_report_pdf` etc. ahora
  se cargan lazy cuando se accede al atributo, rompiendo el ciclo durante
  module init. Scripts standalone que importan `tool_registry` ahora funcionan.

### Refactor arquitectónico (origen: `audit-llm-e2e.md`)

- [x] **#2 Limpieza `__init__.py` de 11 dominios** ✅ CERRADO 2026-05-19 (iteración tarde).
  El barrido anterior dejó pendiente `orchestrator/__init__.py` (re-exportaba
  todos los nodos del grafo + dispatchers internos + tipos auxiliares). Ahora
  expone solo `orchestrator`, `OrchestratorState`, `TaskStatus` — verificado
  con `grep` que esos son los únicos símbolos consumidos desde fuera del
  paquete. Submódulos (`_dispatch_handlers`, `state`, `dispatchers`, etc.)
  siguen accesibles vía path completo. Resto de paquetes (banking, billing,
  compliance, crm, documents, hr, marketing, rag, recruitment, workflow,
  email, accounting) ya estaban en estado mínimo desde el commit 16b6e2d.
- [ ] **#3 `AgentResult` end-to-end en 12/14 `agent.py`** — Opción B (~5-7h, sesión dedicada):
  - Añadir `async def run_agent(state, ...) -> AgentResult` a cada `agent.py` envolviendo `graph.ainvoke()`.
  - Migrar 11 dispatchers a `run_agent()`.
  - Migrar `tool_registry.py` a `from app.agents.<dom>.tools import ...`.
  - Limpiar `__init__.py` a `from .agent import run_agent`.

### Acciones para fase pre-piloto (cuando haya clientes externos)

- [ ] Publicar OAuth Google en **Production mode** (sin verificar) — 1 click en Google Cloud Console, gratis. Necesario para que refresh tokens no expiren cada 7 días.
- [ ] Iniciar OAuth verification (2-6 sem, gratis) + CASA assessment Tier 1 para `gmail.send` (gratis para <5k MAU). Cuando haya 5+ clientes confirmados.
- [ ] Roadmap M1-M2 mencionado en memorias: numeración correlativa, JWT safeStorage, AEAT FNMT.

---

## Notas para futuras sesiones (gotchas confirmadas)

- **Smoke standalone no usa email real**: el backend desktop recibe `TENANT_ENCRYPTION_KEY` desde Electron `safeStorage`, no del `.env`. Scripts que cargan `.env` ven `decrypt FAIL: InvalidToken` y email cae a DEMO. No es bug, es esperado. Si en futuro hace falta probar OAuth real → reescribir smoke como cliente HTTP contra `:8080` con JWT login.
- **OAuth Google está en Testing mode**: refresh tokens expiran cada 7 días. Solo 100 Test users de por vida. Producto funciona con la cuenta del owner; abrir a clientes externos exige publicar en Production primero.
- **El orchestrator requiere `Task` real en DB para ainvoke directo** (FK desde `tenant_documents` y `audit_log`). `smoke_orchestrator.py` ya tiene el helper `_create_task_row()`.
- **Classifier cachea 24h por defecto** (`_CACHE_TTL_CLASSIFY = 86400`). Al iterar sobre keywords/strong, invalidar cache antes de testear o esperar 24h. Script en `c:\tmp\clear_classify_cache.py`.
- **`VALID_DOMAINS` y `DISPATCHER_MAP` deben mantenerse en sync**. Cuando se añade un dominio, ambos archivos + keywords del classifier deben actualizarse o el routing falla silenciosamente.
- **Rutas absolutas `/foo` en Next no funcionan en Electron** (`file://` las resuelve a la raíz del filesystem → 404). Para assets críticos (logo, etc.) usar componente inline tipo `<LogoSvg />`.

---

## Histórico — sesiones cerradas

### 2026-05-18 / 2026-05-19 — Smoke Coordinador SC-1..SC-13

13 hallazgos detectados con `backend/scripts/smoke_orchestrator.py`. **12 cerrados**, 1 abierto (SC-12, arriba).

| ID | Tema | Resolución |
|---|---|---|
| SC-1 | CRM create_client clasificaba mal | Keywords + strong "crea/registra cliente" en `classifier.py` |
| SC-2 | Recruitment no creaba candidatos | Tool nueva `create_candidate` + prompt agresivo |
| SC-3 | Planner no descomponía cadenas multi-acción | Delegar a LLM si hay conector multi-step + 1 dominio |
| SC-4 | Reports caían en `chat` | `report` añadido a `VALID_DOMAINS` + keywords |
| SC-5 | Email en modo DEMO | Reconexión OAuth + fix marcar `is_active=false` ante `InvalidToken` |
| SC-6 | Dispatcher `custom` absorbía 75% del tráfico | Resuelto colateralmente tras SC-1..4 (cayó a 12.5%) |
| SC-7 | UnicodeDecodeError leyendo PDFs | Detectar extensión binaria en `agent_tools/documents.py` |
| SC-8 | Skills obsoletas de yolanda sanchez | Cleanup DB: 5 skills obsoletas borradas |
| SC-9 | Custom timeout 900s × 4 = 60 min | Timeout bajado a 90s en `_dispatch_handlers.py` |
| SC-10 | Orchestrator no pasaba output entre steps | `response_preview` en `build_enriched_intent` |
| SC-11 | hr_simple lento (44 min en un caso) | Variabilidad transitoria Anthropic, no es bug |
| SC-13 | Smoke standalone no comparte encryption key con backend | Documentado en gotchas (no es bug) |

**Smoke v2 final: 8/8 done, 0 fails, 0 timeouts.**

Reporte detallado en `tasks/smoke_orchestrator_2026-05-18.md`. Causa raíz + fix de cada SC en el commit history.

### Archivos modificados en sesiones smoke

- `backend/app/agents/orchestrator/classifier.py` — SC-1, SC-3, SC-4
- `backend/app/agents/orchestrator/state.py` — SC-4
- `backend/app/agents/orchestrator/_dispatch_handlers.py` — SC-9
- `backend/app/agents/recruitment/tools.py` — SC-2
- `backend/app/agents/recruitment/__init__.py` — SC-2
- `backend/app/agents/tool_registry.py` — SC-2
- `backend/app/prompts/recruitment_agent.txt` — SC-2
- `backend/app/services/execution_context.py` — SC-10
- `backend/app/agents/agent_tools/documents.py` — SC-7
- `backend/app/agents/email/tools.py` — SC-5

### Datos de testing en tenant AutomatizaCore (limpieza opcional)

```sql
DELETE FROM tasks WHERE additional_metadata->>'source' = 'smoke_orchestrator';
DELETE FROM crm_contacts WHERE name LIKE 'Acme Smoke%';
DELETE FROM invoices WHERE customer_name LIKE 'Acme Smoke%';
DELETE FROM candidates WHERE name = 'Juan Smoke Perez';
```
(Verificar nombres reales de tablas antes de ejecutar.)

---

## Plan de iteraciones — Simulación PYME real (2026-05-19)

**Objetivo**: ejercitar todas las herramientas y agentes custom contra el LLM real, simulando uso de PYME, validando Coordinador (one-shot) **y** Orquestador (scheduled) en paralelo.

**Estructura**: Híbrida — Ronda 1 aísla por agente; Ronda 2 cruza dominios en flujos end-to-end.
**Perfiles rotados**: A=Consultora/servicios · B=Retail/e-commerce · C=Asesoría contable.

**Dominios detectados en `backend/app/agents/`** (13 funcionales): billing · hr · crm · banking · compliance · documents · email · marketing · recruitment · accounting · excel · rag · uploads (+ orchestrator coordinador, + workflow orquestador).

**Telemetría obligatoria por iteración**:
- ¿Clasificador acertó dominio? (logs `classifier.py`, ojo cache 24h — `c:\tmp\clear_classify_cache.py`)
- ¿Tool ejecutada coincide con la esperada? (registry hit en `tool_registry.py`)
- Tokens consumidos + latencia LLM
- ¿Activity log + task_event_hub registraron el evento?
- Fallo → entrada en `tasks/lessons.md` con regla de prevención

---

### Ronda 1 — Aislamiento por agente (13 iteraciones)

Cada iteración: **1 caso one-shot Coordinador** + **1 workflow agendado Orquestador**. Perfil rota A→B→C→A…

| # | Agente | Perfil | One-shot (Coordinador) | Scheduled (Orquestador) | Tools clave |
|---|--------|--------|------------------------|-------------------------|-------------|
| 1 | **email** | A | "Responde al hilo de Juan sobre la propuesta y adjunta el PDF" | Cada lunes 08:00 resumir bandeja no leída | gmail send, draft, summarize |
| 2 | **documents** | C | "Sube y analiza este contrato PDF, extrae cláusulas de penalización" | Cada noche indexar nuevos PDFs en `/inbox` | upload, extract, classify, agent_tools/documents |
| 3 | **billing** | B | "Crea factura 1.250€ + IVA al cliente NIF B12345678 y envíala" | Día 1 de cada mes generar facturas recurrentes | create_invoice, search_client, send_invoice_by_email |
| 4 | **hr** | A | "Calcula la nómina de mayo de Ana García y déjala pendiente de aprobación" | Día 25 generar todas las nóminas del mes | calculate_and_create_payroll, generate_all_payrolls, approve_payroll |
| 5 | **recruitment** | A | "Recibe CV de Lucía, evalúa fit con vacante Backend SR y agenda entrevista" | Diario 09:00 cribar nuevos CVs del buzón | parse_cv, score_candidate, create_candidate, schedule_interview |
| 6 | **crm** | B | "Crea oportunidad 8.500€ con Acme S.L. en etapa Negociación" | Semanal calificar leads inactivos >30 días | create_opportunity, qualify_leads, update_opportunity_stage |
| 7 | **banking** | C | "Concilia los movimientos de abril del banco con las facturas emitidas" | Diario 07:00 resumen financiero + alertas saldo bajo | reconcile_transactions, check_balances, financial_summary |
| 8 | **compliance** | C | "Recuérdame los modelos de IVA del trimestre y consulta el BOE de hoy" | Cron trimestral aviso modelos 303/130/111 con 7 días de antelación | check_fiscal_deadlines, check_boe_news, fiscal_query (+ fiscal_approval workflow) |
| 9 | **accounting** | B | "Cuadra los asientos del libro diario de abril" | Cierre mensual día 5 del mes siguiente | (mapear tools de `agents/accounting` al iniciar la iter) |
| 10 | **marketing** | A | "Genera 3 propuestas de copy para landing del servicio Auditoría IT" | Quincenal newsletter desde plantilla | generate_copy, schedule_campaign |
| 11 | **excel** | B | "Convierte este Excel de pedidos en resumen por categoría" | Mensual exportar KPIs a Excel | parse_excel, transform, export |
| 12 | **rag** | C | "Busca en nuestra base de conocimiento la política de devoluciones" | (no aplica scheduled — uso síncrono) | semantic_search, agent_tools/knowledge |
| 13 | **uploads** | A | "Procesa el batch de 5 facturas subidas hoy" | Cada hora vaciar cola `pending_uploads` | ingest, dispatch_to_documents |

**Checkpoint Ronda 1**: matriz dominio×tool con verde/rojo. Si <90% verde, no pasar a Ronda 2.

---

### Ronda 2 — End-to-end multi-agente (6 flujos)

Cada flujo arranca con **una sola instrucción NL** al Coordinador y debe encadenar ≥3 agentes vía `_dispatch_handlers`. Mide: clasificación correcta, paso de contexto entre agentes (`response_preview` en `execution_context.py`), `AgentResult` propagado, activity log coherente.

| # | Flujo realista | Perfil | Agentes en cadena | Disparador |
|---|----------------|--------|-------------------|------------|
| 1 | **CV → entrevista → email confirmación → evento Calendar** | A | recruitment → calendar → email | One-shot |
| 2 | **PDF factura proveedor → OCR → asiento contable → conciliación banco** | B | documents → accounting → banking | Workflow al subir archivo |
| 3 | **Cliente nuevo CRM → contrato generado → enviado por email → recordatorio firma +5d** | A | crm → documents → email → scheduler | One-shot que crea cron |
| 4 | **Cierre trimestral**: movimientos → cálculo IVA → modelo 303 → notificación aprobación | C | banking → compliance (fiscal_approval) → email | Scheduled trimestral |
| 5 | **Lead web → calificación → oportunidad CRM → campaña marketing nurture** | B | crm.qualify_leads → marketing → email | One-shot |
| 6 | **Nóminas + recibos + envío portal cliente** | A | hr.generate_all_payrolls → documents → portal-clientes | Workflow día 28 |

---

### Salidas esperadas por iteración

1. `tasks/iter_NN_<agent>_<profile>.md` con: prompt enviado, dominio clasificado, tool(s) ejecutadas, resultado, tokens, fallos.
2. Actualizar `tasks/lessons.md` SOLO si surge regla nueva (no duplicar lecciones SC-1..SC-13).
3. Al cerrar cada ronda: tabla resumen + decisión Go/No-Go.

### Infra previa (una vez antes de empezar)

- [ ] Verificar `backend/scripts/smoke_orchestrator.py` arranca limpio.
- [ ] Confirmar OAuth Google vigente (refresh <7d); regenerar antes de iter 1, 5 y flujos E2E 1/3.
- [ ] Seed mínimo por perfil: 1 tenant + 3 clientes + 2 empleados + 5 facturas históricas + 3 CVs + 5 PDFs.
- [ ] Activar DEBUG en `classifier`, `task_dispatch`, `tool_registry` durante todo el ejercicio.
- [ ] Limpiar cache classifier antes de cada ronda (`c:\tmp\clear_classify_cache.py`).
- [ ] Recordar: cualquier cambio backend exige cerrar y reabrir `AutomatizaCore.exe` (backend embebido).

### Estimación de coste LLM

- Ronda 1: ~13 × 2 casos = 26 llamadas principales + ~30 auxiliares.
- Ronda 2: ~6 × 3-5 agentes = 18-30 llamadas.
- Total orientativo: **75-90 llamadas**. Esperar 30-40% cache hit en classifier dentro de la misma ronda.
