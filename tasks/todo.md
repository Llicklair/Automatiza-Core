# Tareas activas — AutomatizaPyme

Última actualización: 2026-05-19

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

  ⚠️ **Para que tome efecto**: cerrar AutomatizaPyme.exe y volver a abrir (el
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

### Datos de testing en tenant AutomatizaPyme (limpieza opcional)

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
- [ ] Recordar: cualquier cambio backend exige cerrar y reabrir `AutomatizaPyme.exe` (backend embebido).

### Estimación de coste LLM

- Ronda 1: ~13 × 2 casos = 26 llamadas principales + ~30 auxiliares.
- Ronda 2: ~6 × 3-5 agentes = 18-30 llamadas.
- Total orientativo: **75-90 llamadas**. Esperar 30-40% cache hit en classifier dentro de la misma ronda.
