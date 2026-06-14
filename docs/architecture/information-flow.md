# Flujo de información en AutomatizaCore

> Documento de arquitectura — cómo la información interna de cada módulo del ERP se almacena, se propaga y se distribuye al resto del sistema.
> Síntesis verificada sobre código real (no asunciones). Las rutas son relativas a la raíz del repositorio.
> Cada afirmación lleva estado: **CONFIRMED** (verificado al pie de la letra), **PARTIAL** (cierto con matices/correcciones), **REFUTED** (falso).

---

## 1. Resumen ejecutivo

AutomatizaCore es un ERP multi-tenant donde la información fluye por **cinco mecanismos superpuestos**: (1) **acoplamiento por datos** — casi todas las tablas cuelgan de `tenant_id → tenants.id` formando una estrella de aislamiento, y un puñado de entidades-puente (`clients`, `products`, `users`, `invoices`, `journal_entries`) cosen los dominios mediante foreign keys; (2) **eventos de dominio** — `event_bus.emit_event` persiste un `DomainEvent` y dispara workflows `event_based` de otros módulos sin que los agentes se importen entre sí; (3) **llamadas cross-módulo en la capa de servicios** — casi siempre por _imports lazy_ dentro de función (billing→accounting, banking→billing, sales→inventory); (4) **la capa de agentes LangGraph** — un orquestador (Coordinador) descompone una instrucción en lenguaje natural en un plan multi-agente y propaga contexto entre pasos **como texto enriquecido**, no como objetos estructurados; y (5) **el pipeline documental RAG** — ingesta, embeddings locales (BAAI/bge-m3), y recuperación por coseno en Python. Todo termina distribuyéndose a la UI por un único cliente HTTP (`client.ts`) más un canal SSE en tiempo real. El aislamiento real lo garantiza **RLS de Postgres solo en la ruta HTTP**; workers, tools y portal de cliente dependen de filtros `WHERE tenant_id` manuales, lo que constituye el principal riesgo de fuga.

---

## 2. Diagrama de flujo (Mermaid)

```mermaid
flowchart TB
    subgraph FE["Frontend (Next.js)"]
        UI["Páginas / componentes"]
        APICLI["lib/api/client.ts<br/>(única puerta HTTP)"]
        SSE["taskStream.ts<br/>(SSE, fetch+JWT)"]
    end

    subgraph API["API v1 (FastAPI)"]
        ROUTES["routes/*<br/>(validan + delegan)"]
        DEPS["get_current_user<br/>→ set_current_tenant"]
    end

    subgraph AGENTS["Capa de agentes (LangGraph)"]
        ORCH["Orquestador / Coordinador<br/>classify→plan→dispatch→summarize"]
        DOM["Agentes de dominio<br/>billing · hr · documents · rag ·<br/>compliance · banking · email"]
        EXECCTX["ExecutionContext<br/>(propaga TEXTO entre pasos)"]
    end

    subgraph SVC["Servicios (business logic)"]
        BILL["billing<br/>auto_accounting + verifactu"]
        BANK["banking<br/>(conciliación)"]
        SALES["sales / pos / purchase"]
        INV["inventory<br/>(StockMovement FEFO)"]
        ACC["accounting<br/>(JournalEntry PGC)"]
        TREAS["treasury / collections<br/>(consumidores puros)"]
    end

    subgraph BUS["Event bus + automatización"]
        EVT["event_bus.emit_event<br/>→ DomainEvent (JSONB)"]
        WF["Workflows event_based<br/>+ WorkflowExecution"]
        SCHED["scheduler (APScheduler)<br/>cron / month_end / overdue"]
        AUDIT["audit_log (WORM)<br/>append-only"]
    end

    subgraph RAG["Pipeline documental"]
        DOC["TenantDocument<br/>(upload, status=uploaded)"]
        EMB["DocumentEmbedding<br/>(JSONB, sin pgvector)"]
        COS["cosine_topk<br/>(coseno en Python)"]
    end

    DB[("PostgreSQL<br/>multi-tenant + RLS<br/>tenant_id estrella")]

    UI --> APICLI --> ROUTES
    UI -.->|tiempo real| SSE
    ROUTES --> DEPS --> DB
    ROUTES -->|crea Task| ORCH
    ORCH --> DOM
    DOM <-->|key_data / response_preview| EXECCTX
    EXECCTX --> DOM
    DOM -->|@tool| SVC
    SVC --> DB
    BILL -->|FK invoice_id| ACC
    BANK -->|marca paid + asiento| BILL
    SALES -->|StockMovement| INV
    ACC -.->|FK| TREAS
    SVC -->|emit_event| EVT --> WF --> ORCH
    SCHED -->|cron tick| WF
    SCHED -->|emit_event| EVT
    DOM -->|log_action| AUDIT
    DOC --> DOM
    DOM -->|classify+embed| EMB
    EMB --> COS --> DOM
    EVT -->|broadcast_to_tenant| SSE
    ORCH -->|step / agent_result| SSE
```

---

## 3. Dimensiones del flujo de información

### 3.1 Acoplamiento a nivel de datos (Foreign Keys cross-dominio)

**Cómo fluye:** el modelo es una estrella multi-tenant: casi todas las tablas llevan `tenant_id → tenants.id`. Sobre esa base, tres entidades-puente concentran el acoplamiento cross-dominio (`clients`, `products`, `users`), y el ciclo financiero se cose por FKs directas (`invoices`, `payrolls`, `journal_entries`, `bank_transactions`).

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| Invoice (billing) | Client (crm) | FK | factura ↔ cliente/proveedor (NIF, razón social) | `backend/app/db/models/billing.py:62` |
| Invoice | TenantDocument | FK | PDF/escaneo origen (`document_id`) | `backend/app/db/models/billing.py:76` |
| Invoice | Invoice (self) | FK self | `rectifies_invoice_id` (rectificativas RD 1619/2012) | `backend/app/db/models/billing.py:80` |
| InvoiceLine | Product (inventory) | FK (nullable) | línea ↔ artículo | `backend/app/db/models/billing.py:167` |
| JournalEntry (accounting) | Invoice (billing) | FK (nullable) | asiento generado desde factura | `backend/app/db/models/accounting.py:31` |
| JournalEntry | Payroll (hr) | FK (nullable) | asiento generado desde nómina | `backend/app/db/models/accounting.py:32` |
| BankTransaction | Invoice / JournalEntry | FK (nullable) | conciliación banco ↔ factura ↔ asiento | `backend/app/db/models/accounting.py:72-73` |
| SepaRemittanceOrder (treasury) | Invoice / Payroll | FK | trazabilidad cobro/pago SEPA | `backend/app/db/models/treasury.py:79-80` |
| Product (inventory) | Client (rol proveedor) | FK | `supplier_id` → tabla `clients` (no hay tabla suppliers) | `backend/app/db/models/inventory.py:42` |
| PurchaseOrder (orders) | Client (rol proveedor) | FK | `supplier_id` → `clients` | `backend/app/db/models/orders.py:64` |
| Reservation (calendar) | Product (inventory) | FK (nullable) | `resource_id`: recurso reservable = producto | `backend/app/db/models/calendar.py:45` |
| DocumentEmbedding (ai) | TenantDocument | **String suelto (NO FK)** | `document_id` sin integridad referencial | `backend/app/db/models/embeddings.py:14` |
| `<casi todas las tablas>` | Tenant (tenancy) | FK `tenant_id` | aislamiento multi-tenant | `backend/app/db/models/*.py` |

**Entidades compartidas:** `tenants` (raíz universal), `clients` (doble rol cliente/proveedor), `products` (líneas comerciales + recursos de agenda), `users` (autoría/auditoría transversal), `invoices`, `payrolls`, `journal_entries`, `tenant_documents`, `tasks`, `ai_employees`.

**Matices verificados:** la enumeración de FKs a `products.id` es real, pero **todas son `nullable=True`** → el acoplamiento inventory↔comercial es **opcional, no estructural** (una línea puede existir con descripción libre). `tenant_id` es **columna omnipresente** (28/30 modelos) pero **no siempre FK**: hay UUID suelto sin FK en `embeddings.py:15`, `notifications.py` y columnas en `billing.py`/`tenant.py`. `verifactu_chain.tenant_id` también es columna suelta sin FK.

---

### 3.2 Eventos de dominio y triggers (event bus)

**Cómo fluye:** hay **tres subsistemas de "eventos" distintos**: (1) el **event bus de negocio** (`event_bus.emit_event`) persiste un `DomainEvent` (JSONB, por-tenant) y busca Workflows `event_based` del mismo tenant cuyo `trigger_config["events"]` contenga el nombre (o `"any"`), crea Task + WorkflowExecution y despacha al orquestador; (2) un camino casi-duplicado `workflow/_nlp.fire_event` (no persiste DomainEvent, solo desde `POST /workflows/fire-event`); (3) **audit_log WORM** append-only, independiente del bus. Los eventos cruzan módulos siempre por **nombre-string** (`events_catalog.py` es la única fuente de verdad).

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| billing (crear factura) | event_bus + workflows | `emit_event('invoice_created')` | invoice_id, amount, client_name/nif | `backend/app/agents/billing/_invoice_create_async.py:163` |
| billing (cobro) | workflows | `emit_event('invoice_paid')` | invoice_id, amount_total | `backend/app/services/billing/commands.py:288` |
| hr (nómina) | event_bus | `emit_event('payroll_created')` | payroll_id, net_salary, document_id | `backend/app/agents/hr/_payroll_calc.py:168` |
| documents (clasificación) | event_bus → billing/hr | `emit_event('document_processed')` | document_id, document_type, key_entities | `backend/app/agents/documents/tools.py:347` |
| banking (auto-conciliación) | event_bus | `emit_event('banking_auto_reconciled')` | count | `backend/app/services/banking/service.py:448` |
| scheduler (cron 8:30) | event_bus | `emit_event('invoice_overdue')` (vía alerts) | invoice_id | `backend/app/services/alerts/service.py:94` |
| scheduler (día 1, 7:00) | event_bus (todos tenants) | `emit_event(MONTH_END)` | month, year, period | `backend/app/workers/tasks_scheduler.py:580` |
| event_bus.emit_event | orquestador | crea Task+WorkflowExecution + `dispatch_orchestrator` | enriched intent + metadata | `backend/app/services/event_bus.py:108-144` |
| event_bus.emit_event | frontend | `broadcast_to_tenant` (best-effort WS) | `{type:'event', workflow_count}` | `backend/app/services/event_bus.py:158-170` |
| todos los agentes | audit_log (WORM) | `audit.log_action` (immutable por trigger) | agent_name, action, in/out, status | `backend/app/services/audit.py:15` |

**Entidades compartidas:** `domain_events` (DomainEvent), `audit_log` (WORM), `Workflow.trigger_config['events']`, `Task`+`WorkflowExecution`, `events_catalog.py ALL_EVENTS`, `agent_execution_trace`.

**Matices verificados:** **audit_log es WORM PARCIAL** — los triggers `BEFORE UPDATE/DELETE` existen en `0012_sec_worm_audit.py` solo en **Postgres** (no SQLite/tests), y el literal real de la excepción es `'Append-only table: <tabla> is immutable (SEC.WORM)'` (con `TG_TABLE_NAME` interpolado), no el texto genérico. El desacople best-effort es **PARTIAL**: la mayoría de emisores envuelven `emit_event` en try/except, pero **al menos 3 call-sites NO** (`invoices.py:343`, `banking/service.py:448`, `import_bulk.py:193`), por lo que un fallo del bus en esos puntos sí propaga la excepción. `invoice_overdue` lo emite **el módulo alerts**, no el worker month_end.

---

### 3.3 Llamadas cross-módulo entre servicios

**Cómo fluye:** la capa de servicios distribuye información casi siempre por **imports lazy dentro de función** (no a nivel de módulo) para evitar ciclos. El eje financiero es el más acoplado.

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| billing (crear factura) | accounting | call lazy (`auto_accounting.create_invoice_journal_entry`) | asiento PGC determinista (430/700/477...) idempotente por invoice_id | `backend/app/services/billing/auto_accounting.py:56` |
| billing | billing/verifactu_chain | call lazy (intra-dominio, pre-commit) | eslabón append-only hash encadenado | `backend/app/services/billing/commands.py:130-131` |
| banking (conciliar) | billing | call lazy (`create_invoice_payment_entry`) | marca Invoice='paid' + asiento de cobro + `tx.journal_entry_id` | `backend/app/services/banking/service.py:176-180` |
| sales (albarán/TPV/recepción) | inventory | call lazy + StockMovement | descuento/reversa stock FEFO, idempotencia por `reference` | `backend/app/services/sales/commands.py:471-604` |
| hr | ai (cv_parser) | call lazy | extracción IA de datos de CV | `backend/app/services/hr/commands.py:374` |
| email_marketing | email | import + call | envío real de cada email de campaña | `backend/app/services/email_marketing/sender.py:16` |
| workflow/approval_actions | banking + inventory + email | call lazy (`@register_action`) | efectos cross-dominio de acciones aprobadas | `backend/app/services/workflow/approval_actions.py:277` |

**Entidades compartidas:** `Invoice`/`InvoiceLine`, `JournalEntry`, `StockMovement` (clave de idempotencia: `reference`), `Product.stock_quantity`, `BankTransaction`, `verifactu_chain`, `DEMO_TX_PREFIX`, `send_email`.

**Matices verificados:** `billing/accounting.py` **NO define** `create_journal_entry`; es un **shim de compatibilidad** que re-exporta desde `billing/commands.py:419` (allí vive la guarda `is_date_locked`/`PeriodClosedError`). Solo **`reconcile_transaction`** genera el asiento de cobro; **`auto_reconcile` marca `paid` pero NO crea asiento** ni escribe `journal_entry_id`. `treasury` y `collections` son **consumidores puros** (ningún servicio los importa) y se nutren **solo por modelos compartidos**, **no por event_bus** (no usan `emit_event`).

---

### 3.4 Flujo de datos en runtime de la capa de agentes

**Cómo fluye:** una instrucción entra como fila `Task`, el worker construye el `OrchestratorState` (TypedDict, único vehículo entre nodos del grafo) y lo hace fluir: `init_tenant → classify → load_knowledge → plan → validate → dispatch* → summarize`. El `dispatch_node` invoca el dispatcher de dominio, que ejecuta `graph.ainvoke` del agente con un **estado LangGraph propio y vacío** (`messages:[]`, `agent_results:[]`).

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| route POST /tasks | Task (DB) + worker | HTTP → insert + BackgroundTask | user_intent, domain, metadata | `backend/app/api/v1/routes/tasks.py` |
| plan_node / `_plan_from_llm` | OrchestratorState.plan | LLM `MultiAgentPlan` o blueprint | SubTask{agent, action, intent, depends_on} | `backend/app/agents/orchestrator/_plan_handlers.py:423` |
| dispatch_node | ExecutionContext (cada iteración) | `ExecutionContext.from_state(state)` | step_summaries + entities + tenant_knowledge | `backend/app/agents/orchestrator/_dispatch_handlers.py:504` |
| ExecutionContext.build_enriched_intent | current_intent del siguiente agente | inyección de **texto** | instrucción + entidades + preview (~1k tokens) | `backend/app/agents/orchestrator/_dispatch_handlers.py:283` |
| `_dispatch_billing` | agente billing (sub-grafo aislado) | `graph.ainvoke({messages:[],...})` | enriched_intent; NO ve OrchestratorState | `backend/app/agents/orchestrator/dispatchers/billing.py:20` |
| billing_agent_node | ToolNode → services → DB | loop ReAct; tools leen tenant del ContextVar | Invoice/InvoiceLine; PendingApproval si supera umbral | `backend/app/agents/billing/agent.py:36` |
| dispatcher (traducción) | AgentResult | heurística keywords sobre último message | {action, response, approval_id} | `backend/app/agents/orchestrator/dispatchers/billing.py:204` |
| summarize_node | AgentResult agent='summary' | LLM aparte (skip si domain=='chat' o status≠DONE) | resumen ejecutivo → activity_new | `backend/app/agents/orchestrator/_summarize_handlers.py:14` |

**Entidades compartidas:** `OrchestratorState`, `SubTask`, `AgentResult` (`agent_results[]` es lo único que propaga datos entre steps), `ExecutionContext`, `_EXTRACTABLE_KEYS` (22 claves canónicas), `response_preview`, `Task` (fuente de verdad para resume), `tenant_context` ContextVar, `DISPATCHER_MAP`, `PendingApproval`.

**Matices verificados:** la propagación inter-step es **LOSSY y unidireccional vía prompt** — solo viajan las entidades de `_EXTRACTABLE_KEYS` (output dict o regex markdown) y un `response_preview` cap. a 1000 tokens / 4000 chars; **el preview ni se renderiza si hay alguna key_data estructurada** (`execution_context.py:335`). El `AgentResult` lo construye el **dispatcher por heurística de keywords**, no el agente (clasificación frágil). Los steps `ready` sin dependencia mutua corren en **paralelo** (`asyncio.gather` en `dispatch_node`) compartiendo el **mismo snapshot de ExecutionContext** previo al batch → **hermanos no se ven entre sí**.

---

### 3.5 Pipeline de información documental (RAG / embeddings)

**Cómo fluye:** un fichero subido persiste **solo binario + metadata** en `TenantDocument` con `status="uploaded"` (la subida **NO embebe ni clasifica**, pero **sí dispara inmediatamente** una Task documents). La indexación la ejecuta el agente: `classify_document → parse_pdf (OpenDataLoader Java, fallback pypdf) → smart_chunk → get_embedder (BAAI/bge-m3 local) → DocumentEmbedding (JSONB)`. El retrieval se distribuye a tres consumidores que comparten `cosine_topk`.

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| Frontend (upload) | TenantDocument | POST multipart → `upload_single` (status=uploaded) | binario + file_name + category + tenant_id | `backend/app/services/documents/service.py` |
| Orchestrator | documents agent | anexa `document_id` como **texto** al intent | document_id (vínculo por `task_id`) | `backend/app/agents/orchestrator/dispatchers/documents.py:40` |
| classify_document | parse_pdf | subprocess Java (fallback pypdf) | markdown + page_number/element_type/bounding_box | `backend/app/services/pdf/parser.py` |
| raw_text | classify_by_rules | keywords+regex (LLM solo si confidence<0.70) | document_type, key_entities, confidence | `backend/app/services/documents/classifier.py` |
| Chunk[] | DocumentEmbedding | `aembed_documents` → INSERT JSONB | vector + text + page_number + jurisdiction; `employee_id=NULL`=público | `backend/app/agents/documents/tools.py` |
| consulta NL | DocumentEmbedding | `cosine_topk` (coseno en **Python**, NO pgvector) | top_k chunks con cita `[Página N]` | `backend/app/agents/agent_tools/semantic_search.py` |
| compliance (fiscal) | DocumentEmbedding | `_search_tenant_docs` + normativa hardcoded | chunks del tenant filtrados por jurisdiction | `backend/app/agents/compliance/tools.py` |
| AIEmployee custom | tools RAG documents.* | AgentSkill (`tool_module`) + employee_id si knowledge_enabled | corpus privado + público | `backend/app/agents/agent_tools/ai_team.py` |

**Entidades compartidas:** `TenantDocument`, `DocumentEmbedding` (tabla vectorial única), `Tenant.jurisdiction` (filtro cross-border), `Client` (creado desde NIF extraído), `AgentSkill`, evento `document_processed`.

**Matices verificados:** el coseno es **Python PURO** (`math.sqrt` + bucle), **NO NumPy** pese al docstring. El `~90% sin LLM` es **estimación no respaldada** por métrica; solo el mecanismo (umbral `confidence<0.70`) es verificable. `upload_single` **NO es pasivo**: tras guardar dispara `_dispatch_task('documents')`. El `document_id` se **anexa como texto** al intent (no como parámetro estructurado); el vínculo se resuelve por `TenantDocument.task_id`. **El BOE NO está vectorizado** — compliance lo consulta en vivo con `BOEScraper`.

---

### 3.6 Propagación de contexto de tenant y aislamiento

**Cómo fluye:** el tenant activo vive en un único ContextVar (`_current_tenant_ctx`), heredado por copia en cada Task asyncio. En HTTP lo fija la dependencia `get_current_user` (tras decodificar el JWT), **no un middleware**. La barrera fuerte es **RLS Postgres**: `apply_tenant_rls` ejecuta `SET LOCAL app.current_tenant` y las policies de `0016_sec_rls` filtran por esa variable.

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| Request HTTP (JWT) | ContextVar tenant | `get_current_user` → `set_current_tenant` | tenant_id del User | `backend/app/core/dependencies.py:73` |
| get_db (AsyncSession) | Postgres | `apply_tenant_rls` → `SET LOCAL app.current_tenant` | tenant_id validado | `backend/app/db/base.py:41` → `backend/app/db/rls.py` |
| variable de sesión | filas con tenant_id | policy `rls_tenant_isolation` USING/WITH CHECK | filtrado por tenant | `backend/app/db/migrations/versions/0016_sec_rls.py` |
| orquestador/dispatcher | worker | tenant_id explícito + `set_current_tenant(hint)` | tenant del Task/Execution | `backend/app/workers/tasks_orchestrator.py` |
| LLM/coordinador | @tool de agente | `enforce_tenant` sobreescribe `kwargs['tenant_id']` con el del ContextVar | anti prompt-injection | `backend/app/agents/tenant_context.py:54` |
| @tool | AsyncSession (tool_session) | `tenant_context` fija ContextVar; query `WHERE tenant_id == X` manual | **NO hay SET LOCAL aquí** | `backend/app/agents/shared/db.py` |
| scheduler global | operaciones por tenant | `set_current_tenant(None)` para lectura cross-tenant, luego `set_current_tenant(tid)` por iteración | lista de tenants activos | `backend/app/workers/tasks_scheduler.py` |
| portal de cliente | validación tenant | JWT `client_portal` valida `client.tenant_id` (**NO setea ContextVar**) | tenant del cliente externo | `backend/app/core/dependencies.py` |

**Entidades compartidas:** `_current_tenant_ctx`, variable de sesión `app.current_tenant`, policy `rls_tenant_isolation`, columna `tenant_id` (~30 modelos), `get_db`/`tool_session`, `enforce_tenant`.

**Matices verificados (críticos):** **NO existe ningún event listener SQLAlchemy** en `backend/app` (el único está en `tests/conftest.py:80`). Por tanto el `SET LOCAL` ocurre **exclusivamente** en `get_db` (HTTP); **los docstrings que mencionan "el listener RLS" son falsos/obsoletos**. La policy es **permisiva en lectura cuando `app.current_tenant` es NULL/''** (`USING ... OR IS NULL OR = ''`) → cualquier sesión sin SET LOCAL (todos los workers/tools/portal) **ve TODAS las filas de TODOS los tenants a nivel DB en SELECT**. Matiz que reduce el daño: el **`WITH CHECK` NO tiene escape NULL/''** → un INSERT/UPDATE sin contexto sería **rechazado** por Postgres, así que la fuga total cross-tenant a nivel DB es de **LECTURA**, no de escritura.

---

### 3.7 Distribución de información backend → frontend

**Cómo fluye:** toda la información llega a la UI por un único cliente HTTP `client.ts` (JWT Bearer, refresh en 401, evento en 402, descargas blob). Cada dominio tiene su módulo en `lib/api`, reagrupado por un barrel (`index.ts`). El tiempo real va por **SSE con `fetch`** (no `EventSource`, para poder enviar el JWT en cabecera), puenteado desde el WS in-process al `task_event_hub`.

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| endpoint REST | módulo lib/api | `request()` (JWT Bearer, refresh 401) | JSON tipado o Blob | `frontend/src/lib/api/client.ts` |
| orquestador | task_event_hub | `broadcast_to_tenant` (fan-out por task_id) | eventos `step`/`summary` | `backend/app/api/ws/notifications.py:33` |
| task_event_hub.stream | endpoint SSE `/tasks/{id}/stream` | StreamingResponse text/event-stream | frames SSE de progreso | `backend/app/api/v1/routes/tasks.py:156` |
| endpoint SSE | useAgentStream (página mi-equipo) | `fetch` + ReadableStream (no EventSource) | TaskProgressEvent + status | `frontend/src/lib/api/taskStream.ts:37` |

**Entidades compartidas:** `client.ts` (puerta HTTP), barrel `index.ts` (`api` object), `TaskProgressEvent`, `task_event_hub` (puente WS→SSE in-process), `Task.task_id` (pivote), `secureStore`/cookie auth_flag.

**Matices verificados:** "`client.ts` única base de fetch" es **PARTIAL** — **ningún componente `.tsx` llama `fetch` directamente** (regla de capas respetada), pero **4 módulos de `lib/` SÍ usan `fetch` crudo** fuera de `request()`: `client_portal.ts`, `scanner.ts`, `taskStream.ts` y `lib/error-reporter.ts`. La respuesta del agente en streaming SSE solo la cablea **mi-equipo**; **banca** y el **AiChatBar global** lanzan agentes pero recogen el resultado (`Task.agent_results`) por **REST polling** (`api.tasks.get` cada 2s).

**Riesgos del canal:** `task_event_hub` es **in-process only** (sin Redis, no escala a varios workers uvicorn), **sin persistencia ni replay**, descarta si la cola se llena (256).

---

### 3.8 Distribución de trabajo por automatizaciones/workflows

**Cómo fluye:** un `Workflow` multi-tenant se dispara por **tres caminos** — cron (APScheduler tick por minuto), evento de dominio (`event_bus`), o manual. Cualquier disparo crea una `WorkflowExecution` (estado durable) + una `Task` con domain inferido. El despacho bifurca: **DETERMINISTA** (`execute_deterministic_steps`, encadena con `prev_output`/`$prev`), **REASONING** (`dispatch_orchestrator` → plan multi-agente → `DISPATCHER_MAP`), o **NODOS** (`NodeEngine`).

| From | To | Mecanismo | Dato | Fichero |
|------|----|-----------|------|---------|
| APScheduler (cron `*`) | `_check_scheduled_workflows` | cron `add_job` | tick cross-tenant sweep | `backend/app/services/scheduler.py:35` |
| `_check_scheduled_workflows` | IdempotencyGuard + has_active_execution | idempotencia + condiciones DB | clave por instante programado; salta si run activo | `backend/app/workers/tasks_scheduler.py:197` |
| plan_node / `_plan_from_llm` | dispatch_node → DISPATCHER_MAP | LLM `MultiAgentPlan`, routing por dominio | SubTasks (agent, action, needs_output_from) | `backend/app/agents/orchestrator/_dispatch_handlers.py:201` |
| `_dispatch_billing` | `_dispatch_email` | `ainvoke` encadenado por `needs_output_from` | resumen billing → email → archiva TenantDocument | `backend/app/agents/orchestrator/dispatchers/billing.py:20` |
| Task finalizada | WorkflowExecution.status/result_log | sync vía `additional_metadata.execution_id` | done→success, failed→failed, awaiting→paused | `backend/app/workers/_orchestrator_state.py:82` |
| approval_gate | PendingApproval + execution paused | suspend/resume por nodo | `current_node_id`; resume exacto (no reinicia) | `backend/app/services/ai/node_engine_nodes.py:165` |
| check_failed_workflow_executions | create_notification | cron sweep con flag `notified` | executions failed desatendidas | `backend/app/workers/tasks_scheduler.py:491` |

**Entidades compartidas:** `Workflow` (trigger_type/config, execution_mode, ui_nodes), `WorkflowExecution` (durable: result_log, current_node_id, node_states, notified), `Task`, `PendingApproval`, `DISPATCHER_MAP`, `IdempotencyGuard`, `TenantDocument` (salida archivada), `tenant_context`.

**Matices verificados:** `DISPATCHER_MAP` enruta a **funciones dispatcher** (`_dispatch_billing`...), no a "graphs autónomos" uniformemente; **solo los AIEmployees custom** se ejecutan como graph compilado. `prev_output` literal (`$prev`) es de la ruta **DETERMINISTA**; en reasoning el encadenamiento lo hace `ExecutionContext.build_enriched_intent`. **El ejemplo "lunes → billing → email" es PARTIAL**: el scheduler crea **una** Task con **un** domain inferido por keywords (`_infer_domain_from_text`); si el domain es `billing` (no `coordinator`), `plan_node` hace **plan de 1 solo paso**. La descomposición billing→email vía `needs_output_from` **solo ocurre si la automatización entra como `coordinator`**, no automáticamente por contener "factura".

---

## 4. Narrativa extremo a extremo: el viaje de una factura

Sigamos **una factura creada por lenguaje natural** y veamos cómo su información se propaga por todo el ERP:

1. **Entrada (lenguaje natural → Task).** El usuario escribe "crea una factura de 2.000€ a ACME por consultoría". El frontend la envía por `client.ts` a `POST /tasks` (`backend/app/api/v1/routes/tasks.py`), que inserta una fila `Task` y la encola. La dependencia `get_current_user` ya fijó el `tenant_id` en el ContextVar (`backend/app/core/dependencies.py:73`).

2. **Orquestación (Coordinador).** El worker construye el `OrchestratorState` y lo hace fluir por el grafo (`classify → plan → dispatch`). El planner produce un `SubTask{agent:'billing', action, intent}` y `dispatch_node` invoca `_dispatch_billing`, que ejecuta el sub-grafo billing **aislado** (`backend/app/agents/orchestrator/dispatchers/billing.py:20`).

3. **Persistencia + contabilización (FK).** La tool del agente billing crea `Invoice`/`InvoiceLine` en Postgres (FK `client_id → clients.id`, `backend/app/db/models/billing.py:62`). En la creación se dispara `auto_accounting.create_invoice_journal_entry` (`backend/app/services/billing/auto_accounting.py:56`), que genera el **asiento PGC determinista** (430 Clientes / 700 Ventas / 477 IVA) enlazado por `JournalEntry.invoice_id` (`backend/app/db/models/accounting.py:31`).

4. **VeriFactu (intra-billing, atómico).** Antes del commit, `maybe_append_verifactu_record` (`backend/app/services/billing/commands.py:130-131`) añade un **eslabón append-only** con huella hash encadenada a la factura anterior, en la misma transacción. A partir de aquí, `delete_invoice` quedará **bloqueado** (cadena inmutable).

5. **Evento de dominio.** El agente emite `emit_event('invoice_created')` (`backend/app/agents/billing/_invoice_create_async.py:163`). `event_bus.emit_event` (`backend/app/services/event_bus.py:108-144`) persiste un `DomainEvent` (JSONB) y busca Workflows `event_based` **del mismo tenant** que escuchen ese nombre. Si existe (p.ej. "cuando se cree factura → notificar por email"), crea Task + WorkflowExecution y despacha al orquestador → posible **workflow cross-módulo** sin que billing importe al agente email.

6. **Auditoría WORM.** Cada acción del agente escribió en `audit_log` vía `audit.log_action` (`backend/app/services/audit.py:15`), tabla **append-only protegida por triggers** en Postgres. Esto alimenta el dashboard de "tiempo ahorrado" (`backend/app/services/metrics/time_saved.py:54`).

7. **Distribución a la UI (SSE).** Durante la ejecución, `_stream_and_log` emite eventos `orchestrator_step`/`agent_result` que `broadcast_to_tenant` puentea al `task_event_hub` (`backend/app/api/ws/notifications.py:33`) y de ahí al endpoint SSE. Si el usuario está en **mi-equipo**, `taskStream.ts` los muestra en tiempo real; en banca/AiChatBar el resultado llega por **REST polling** de `agent_results`. Además `emit_event` hace `broadcast_to_tenant` con `{type:'event', workflow_count}`.

8. **Cierre del ciclo financiero (cobro).** Más tarde, al importar un extracto N43, `banking.reconcile_transaction` (`backend/app/services/banking/service.py:176-180`) concilia el `BankTransaction` contra la `Invoice`: marca `Invoice.status='paid'`, crea el asiento de cobro y escribe `tx.journal_entry_id` — todo en un commit. Emite `invoice_paid`, que puede encadenar otro workflow. Treasury puede generar luego la remesa SEPA (`SepaRemittanceOrder.invoice_id`, `backend/app/db/models/treasury.py:79`).

9. **RAG (si llega el PDF).** Si el usuario sube el PDF de la factura, `upload_single` lo guarda como `TenantDocument` (status=uploaded) y dispara una Task documents. El agente lo clasifica, lo trocea (`smart_chunk`) y genera filas `DocumentEmbedding` (JSONB) con `bge-m3` local. A partir de ahí el RAG (`cosine_topk` en Python) puede responder preguntas citando `[Página N]`. El NIF extraído puede **crear/vincular un Client** (`backend/app/agents/documents/tools.py`).

**En síntesis:** una sola factura toca FK (clients/accounting/treasury), VeriFactu, event_bus, audit WORM, SSE/REST a la UI y, opcionalmente, el índice RAG — siempre dentro del aislamiento `tenant_id`.

---

## 5. Tabla consolidada de afirmaciones verificadas

| Dimensión | Claim | Estado | Evidencia |
|-----------|-------|--------|-----------|
| Datos (FK) | `clients` es bridge único cliente+proveedor; no existe tabla `suppliers` | **CONFIRMED** | `crm.py:23`; `inventory.py:42` y `orders.py:64` (`supplier_id→clients`) |
| Datos (FK) | Ciclo Invoice/Payroll→JournalEntry→BankTransaction→SepaRemittance | **CONFIRMED** | `accounting.py:31-32,72-73`; `treasury.py:79-80` (FKs nullable) |
| Datos (FK) | Líneas comerciales referencian `products.id` (acoplamiento obligatorio) | **PARTIAL** | FKs reales pero **todas `nullable=True`** → opcional, no estructural |
| Datos (FK) | `tenant_id→tenants.id` es la FK omnipresente | **PARTIAL** | columna en 28/30 modelos; UUID sin FK en `embeddings.py:15`, `notifications.py` |
| Datos (FK) | `DocumentEmbedding.document_id` es String sin FK | **CONFIRMED** | `embeddings.py:14` (vs `billing.py:76` que sí es FK) |
| Eventos | Dos publicadores: `emit_event` (persiste) vs `fire_event` (no persiste) | **CONFIRMED** | `event_bus.py:40-172`; `workflow/_nlp.py:79-145` |
| Eventos | Aislamiento multi-tenant en el bus (SELECT por tenant + RLS) | **CONFIRMED** | `event_bus.py:60-66,144` |
| Eventos | `audit_log` es WORM real con triggers | **PARTIAL** | solo Postgres; literal real `'Append-only table: <tabla>...'` |
| Eventos | Todos los `emit_event` son best-effort (try/except) | **PARTIAL** | 3 call-sites SIN try/except (`invoices.py:343`, `banking:448`, `import_bulk:193`) |
| Servicios | billing→accounting vía `auto_accounting` | **PARTIAL** | `billing/accounting.py` es shim; impl real en `commands.py:419` |
| Servicios | banking→billing crea asiento de cobro al conciliar | **PARTIAL** | solo `reconcile_transaction`; `auto_reconcile` NO crea asiento |
| Servicios | treasury/collections son consumidores puros | **PARTIAL** | cierto, pero vía modelos compartidos **NO event_bus** |
| Servicios | VeriFactu es intra-billing y bloquea borrado | **CONFIRMED** | `commands.py:130-131,243-244,329-335` |
| Agentes | Sub-grafo de dominio arranca vacío; solo recibe texto | **CONFIRMED** | `dispatchers/billing.py:33-44` |
| Agentes | Propagación inter-step lossy (`_EXTRACTABLE_KEYS` + preview) | **CONFIRMED** | `execution_context.py:163-191,335` (preview solo si no hay key_data) |
| Agentes | `AgentResult` lo construye el dispatcher por heurística | **CONFIRMED** | `dispatchers/billing.py:51-134` |
| Agentes | Steps paralelos comparten snapshot previo (no se ven) | **CONFIRMED** | `_dispatch_handlers.py:504-519` |
| RAG | Embeddings `bge-m3` local; fallback OpenAI | **CONFIRMED** | `llm_factory.py:262-302`; `config.py:70-71` |
| RAG | Sin pgvector; coseno en Python trayendo todo a memoria | **CONFIRMED** | `embeddings.py:37-42`; `semantic_search.py` (Python puro, **no NumPy**) |
| RAG | Clasificación ~90% sin LLM | **PARTIAL** | estimación no respaldada; solo umbral `confidence<0.70` verificable |
| RAG | La subida NO indexa | **PARTIAL** | cierto, pero `upload_single` SÍ dispara Task documents |
| Tenancy | RLS ACTIVA + FORCE en Postgres | **CONFIRMED** | `0016_sec_rls.py:31-77` |
| Tenancy | `SET LOCAL` solo en `get_db`; **no hay listener SQLAlchemy** | **CONFIRMED** | `base.py:41`; grep listener = 0 (solo en tests) |
| Tenancy | Policy permisiva con tenant NULL/'' → ve todo | **CONFIRMED** | `0016_sec_rls.py:38-42` (USING); WITH CHECK SÍ estricto → fuga solo LECTURA |
| Tenancy | No existe `TenantContextMiddleware` (comentarios obsoletos) | **CONFIRMED** | `main.py:123-137`; tenant en `dependencies.py:73` |
| Frontend | Ningún `.tsx` llama `fetch` directo | **CONFIRMED** | grep `.tsx` = 0 |
| Frontend | `client.ts` única base de fetch | **PARTIAL** | 4 módulos lib/ usan `fetch` crudo (taskStream, client_portal, scanner, error-reporter) |
| Frontend | SSE usa `fetch` no `EventSource` (para JWT) | **CONFIRMED** | `taskStream.ts:4-5,37-44` |
| Frontend | Stream SSE solo cableado en mi-equipo; resto REST polling | **CONFIRMED** | `useTaskPanel.ts`; banca/AiChatBar usan `api.tasks.get` |
| Automatización | Idempotencia triple barrera + recovery | **CONFIRMED** | `tasks_scheduler.py:216,222`; `tasks_orchestrator.py:80-82` |
| Automatización | Resume por aprobación exacto desde `current_node_id` | **CONFIRMED** | `node_engine_nodes.py:165-197`; `node_engine.py:104-133` |
| Automatización | Ejemplo cron "billing→email" automático | **PARTIAL** | requiere domain `coordinator`; si infiere `billing` → plan 1 paso |

---

## 6. Riesgos y gaps de flujo de información (priorizados)

### CRÍTICOS (aislamiento / integridad)

1. **Brecha de aislamiento en workers/tools/portal (fail-open de LECTURA).** No existe listener SQLAlchemy; el `SET LOCAL` solo corre en `get_db`. La policy RLS es **permisiva con tenant NULL** → cualquier query de `@tool`, worker o portal de cliente que **olvide `WHERE tenant_id`** devuelve filas de **todos los tenants** en SELECT. El aislamiento ahí es "best-effort por convención", no garantizado por la DB (~600 call-sites manuales). *Mitigante:* el `WITH CHECK` estricto impide la escritura cross-tenant, así que la fuga es de lectura. *Acción:* eliminar la cláusula `OR IS NULL OR = ''` (fail-closed) o introducir un listener que propague el ContextVar a `SET LOCAL` en toda sesión.

2. **Docstrings que mienten sobre el listener RLS.** `agents/shared/db.py`, `db/rls.py`, `core/tenant_context.py` describen un listener que **no existe**, induciendo a confiar en una barrera ausente. *Acción:* corregir los comentarios para reflejar que el aislamiento fuera de HTTP es 100% por filtro manual.

3. **`document_embeddings.document_id` sin FK ni ON DELETE.** Borrar un `TenantDocument` deja embeddings huérfanos → el RAG puede servir chunks de documentos eliminados. La coherencia IA↔documento es responsabilidad del código, no de la BD.

### ALTOS (propagación incompleta entre pasos)

4. **Propagación inter-step frágil y lossy (capa de agentes).** Toda la info que pasa de un agente al siguiente es **prosa dentro de `current_intent`** + `_EXTRACTABLE_KEYS` (22 claves cerradas) con preview cap. a ~1k tokens. Un cambio en el formato de salida de un agente rompe la extracción de entidades (p.ej. pierde `invoice_id`) **sin error visible**. Pasos paralelos del mismo batch no se ven entre sí.

5. **Clasificación heurística en el dispatcher.** `success`/`action` se infieren por keywords sobre el texto del LLM, no por un campo estructurado. Falsos positivos/negativos cambian qué se marca done/failed, qué se propaga y el `result_log`/`notified` del workflow → **ocultan fallos reales**. Además acopla lógica de negocio dentro del dispatcher (viola la regla de capas).

6. **Entrega no garantizada en workflows reasoning.** El resultado solo se entrega si el planner LLM coloca un paso `email` y `needs_output_from` encadena la salida; si el plan omite el paso, el resumen se calcula **pero no se entrega**, sin error. Agravado por la inferencia de domain (`billing` → plan de 1 paso, sin descomposición).

### MEDIOS (acoplamiento / robustez)

7. **Acoplamiento transaccional banking→billing→accounting.** `reconcile_transaction` muta tres dominios (`BankTransaction`, `Invoice`, `JournalEntry`) en un commit; un cambio en `auto_accounting` o en la state machine de Invoice puede romper la conciliación silenciosamente.

8. **`emit_event` hace `db.commit()` interno.** Si el caller tenía una transacción abierta con otros cambios, el commit del bus los confirma prematuramente (acoplamiento de transacción). Visible en billing/sales/hr.

9. **Idempotencia de stock por strings mágicos.** Toda la detección de duplicados/reversas depende del formato de `StockMovement.reference` (`DELIVERY_NOTE:`/`POS_SESSION:`/`PO:`); cualquier cambio de formato rompe la idempotencia sin error.

10. **`task_event_hub` in-process y `fire_event` divergente.** El hub SSE no persiste, no replica y descarta si la cola se llena (256); no escala a varios workers uvicorn. El camino `fire_event` no deja rastro en `domain_events` ni emite WS → auditoría incompleta del endpoint manual.

11. **Mezcla heterogénea de políticas ON DELETE en FKs cross-dominio.** Muchas FKs no declaran `ondelete` (default RESTRICT) — `JournalEntry→Invoice`, `SepaRemittanceOrder→Invoice/Payroll` — pudiendo bloquear borrados; otras usan SET NULL/CASCADE. El ciclo de vida de una factura (anulación, rectificativa) debe propagarse **manualmente** a asientos y remesas.

### BAJOS (escalabilidad / claridad)

12. **Retrieval RAG O(n) sin ANN.** `cosine_topk` trae **todos** los chunks del tenant a memoria por consulta y rankea en Python (sin NumPy); apto hasta ~5000 chunks/tenant, luego degrada en las 3 rutas (rag/compliance/empleados).

13. **Confusión de capas "evento".** El event bus de dominio, `analytics/events.py` (PostHog) y los eventos SSE comparten la palabra pero son sistemas independientes — riesgo de comprensión, no de runtime.

---

*Documento generado por síntesis verificada de 8 dimensiones de flujo de información. Las afirmaciones PARTIAL reflejan las correcciones de la fase de verificación sobre código real.*
