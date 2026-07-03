# AutomatizaCore

> **ERP español con IA agentica e instalación local.** Una plataforma completa de gestión empresarial (facturación, contabilidad, banca, CRM, RRHH, compliance fiscal) donde el usuario opera en **lenguaje natural** y agentes especializados ejecutan las acciones contra una base de datos que vive en su propia máquina.

**Estado**: pre-producción · 67.350 LOC backend · 14 agentes · 69 rutas API · 109 páginas frontend · cumplimiento Verifactu

---

## Índice

1. [Qué es y para quién](#qué-es-y-para-quién)
2. [Capacidades](#capacidades)
3. [Modelo local-first (con matices honestos)](#modelo-local-first-con-matices-honestos)
4. [Arquitectura](#arquitectura)
5. [Stack técnico](#stack-técnico)
6. [Proveedores LLM](#proveedores-llm)
7. [Sistema RAG y embeddings](#sistema-rag-y-embeddings)
8. [Empleados IA personalizables](#empleados-ia-personalizables)
9. [Tareas vs Automatizaciones](#tareas-vs-automatizaciones)
10. [Multi-tenancy y BD](#multi-tenancy-y-bd)
11. [Integraciones OAuth](#integraciones-oauth)
12. [Seguridad](#seguridad)
13. [Servidor de licencias y proxy OAuth (Render + Neon)](#servidor-de-licencias-y-proxy-oauth-render--neon)
14. [Arranque rápido](#arranque-rápido)
15. [Limitaciones conocidas](#limitaciones-conocidas)
16. [Documentación adicional](#documentación-adicional)

---

## Qué es y para quién

AutomatizaCore combina dos cosas que normalmente no van juntas:

1. **Un ERP completo** con facturación electrónica Verifactu, contabilidad española (libro diario, P&G, balance), banca, CRM, RRHH con nóminas, compras, ventas, POS, inventario y compliance AEAT.
2. **Una capa de IA agentica** donde el usuario escribe en lenguaje natural (*"hazme la nómina de Juan para este mes"*) y agentes especializados ejecutan la acción.

**Target principal**:
- Asesorías fiscales y laborales pequeñas–medianas (5–20 empleados)
- Pymes con datos sensibles que no pueden o no quieren ERP cloud puro (legal, sanitario, ciberseguridad)
- Empresas que quieren un "equipo de IA" propio combinando 45 capacidades de negocio

**Lo que NO es**:
- Un SaaS horizontal genérico tipo Holded — eso ya existe
- Un producto certificado para empresas grandes — usa SAP/Oracle si necesitas eso
- Un wrapper de ChatGPT — la IA aquí escribe en la BD, no sólo responde

---

## Capacidades

### ERP funcional

| Área | Estado | Notas |
|---|---|---|
| Facturación electrónica | ✅ Producción | Invoices, series, recurrentes, presupuestos, conversión cotización→factura, exportación PDF |
| **Verifactu** | 🟡 Beta (envío SIMULADO) | Cadena de hash, configuración por tenant, audit WORM, backfill LISTOS. El **envío a la AEAT es simulación** (`mark_verifactu_sent` marca la factura sin generar XML/firma/POST real): la presentación telemática real está **bloqueada por certificado FNMT** (ver SCOPE.md). No asumir que una factura "enviada" está presentada ante Hacienda |
| Contabilidad española | ✅ Producción | Libro diario, P&G, balance, cuadro de cuentas, activos fijos |
| Compras | ✅ Producción | Purchase orders, facturas de compra, proveedores |
| Ventas | ✅ Producción | Sales orders, albaranes con reversa de stock, cotizaciones |
| Inventario | ✅ Producción | Stock items, ajustes, valoración |
| POS | ✅ Producción | Punto de venta integrado |
| CRM | ✅ Producción | Oportunidades, actividades, pipeline, portal de clientes |
| Banca | ✅ Producción | Movimientos, saldos, conciliación, resumen financiero |
| Tesorería | 🟡 Beta | Cashflow, pagos/cobros, remesas |
| RRHH | ✅ Producción | Empleados, nóminas (cálculo IRPF + SS + aprobación), contratos |
| Reclutamiento | ✅ Producción | Posiciones, subida de CVs, análisis IA con scoring |
| Calendar | ✅ Producción | Eventos, citas, reservas |
| Proyectos | ✅ Producción | Projects, members, tasks |
| Compliance AEAT | ✅ Producción | Modelos AEAT, presentación asistida, REGAP, BOE queries |

### Capa IA — Lo que nos diferencia

| Capacidad | Notas |
|---|---|
| **Empleados IA personalizables** | Crea agentes con nombre/rol/dominio/system_prompt + selección de 45 skills del catálogo. Tabla `ai_employees` + `agent_skills`, budget guard por empleado, activity feed. |
| **Sandbox generativo de UI** | Genera interfaces HTML/CSS desde lenguaje natural (`/sandbox`) |
| **Workflows con NLP** | Parser de lenguaje natural a workflow persistente + scheduler + recovery + condiciones |
| **Pipeline RAG propio** | OpenDataLoader (Java) → clasificación regex (90% sin LLM) → smart chunker → BAAI/bge-m3 → pgvector con citas a página exacta |
| **Documentos RRHH IA** | Genera contratos, cartas y certificados con plantillas |
| **Análisis IA de CVs** | Scoring de compatibilidad candidato↔posición |
| **Coordinador (Classify→Plan→Validate→Dispatch)** | LangGraph orquestando 14 dispatchers por dominio |
| **Orquestador de workflows** | APScheduler + cron + event triggers + idempotencia + recovery |
| **Autonomía configurable** | Por tenant, qué operaciones puede ejecutar la IA sin aprobación humana |
| **Approvals fiscales** | Workflow de aprobación humana para operaciones AEAT |

### Plataforma

Multi-tenancy estricto desde día 1 · Multi-idioma (i18n) · Backup local · Audit log inmutable + domain events · Cifrado PBKDF2+Fernet de credenciales OAuth · Rate limiting · Prompt injection guard · Security headers + CSP · JWT + refresh tokens · LLM usage metering · Firma digital · Importación masiva · Onboarding wizard con simulación-303

### Desktop (Electron)

Instalable como `.exe` sin requerir Docker, ni Postgres preinstalado, ni Python, ni Java en el sistema del cliente. Auto-gestiona:

- **PostgreSQL portable** (`postgres-manager.js`)
- **Python embebido** (`python-manager.js`)
- **JRE 21 portable** (Adoptium, descargado bajo demanda para OpenDataLoader) (`jre-manager.js`)
- **Sincronización hot-reload** al instalado (`sync.js`)
- Tray, splash, service manager

---

## Modelo local-first (con matices honestos)

```
┌──────────────────────────────────────────┐      ┌─────────────────────────┐
│           CLIENTE (local)                │      │  SERVIDOR LICENCIAS     │
│                                          │      │  Render (FastAPI)       │
│  Electron (PostgreSQL portable + Python) │◄────►│  + Neon (Postgres)      │
│  Next.js Frontend                        │ HTTPS│  Valida licencia + proxy│
│  FastAPI                                 │      │  OAuth · No ve datos ERP│
└────────────┬─────────────────────────────┘      └─────────────────────────┘
             │
             │ HTTPS (sólo en llamadas LLM y embeddings cloud opcional)
             ▼
┌──────────────────────────────────────────┐
│  APIs LLM configuradas por el cliente    │
│  (Anthropic / Gemini / OpenAI / etc.)    │
└──────────────────────────────────────────┘
```

### Lo que sí es local

- **Toda la base de datos operativa** (facturas, clientes, nóminas, contabilidad, documentos): PostgreSQL en disco del cliente.
- **Embeddings**: BAAI/bge-m3 corre offline en CPU del cliente (~500MB RAM).
- **Clasificación de documentos**: regex+keywords mecánicos, sin LLM en el 90% de los casos.
- **El backend, el frontend y la BD** corren en proceso local (sin contenedores, sin servidor remoto).

### Lo que NO es local

- **Las llamadas a LLM con contenido del cliente** salen por HTTPS al proveedor configurado (Anthropic/Gemini/OpenAI).
- El proveedor por defecto es Anthropic con DPA estándar (Zero Data Retention disponible bajo plan Enterprise).
- **Ollama y modelos locales fueron eliminados** del soporte oficial; se podría reintegrar si un cliente lo requiere.

### Cuándo importa el matiz

Para la mayoría de pymes (asesorías, comercio, servicios), el modelo "datos en reposo locales + inferencia cloud con DPA" es suficiente y diferenciador frente a SaaS puro tipo Holded/Sage.

Para clientes con requisitos estrictos (ciberseguridad, legal sensible, sanitario con datos clínicos), pueden necesitar inferencia 100% local. **Esto requiere desarrollo adicional** (reintegrar Ollama o LLM autohospedado).

### Modelo de responsabilidad

| Aspecto | Cobertura |
|---|---|
| Privacidad de datos en reposo | ✅ Garantizada (BD local) |
| Brecha masiva (servidor central) | ✅ Imposible (no hay servidor con datos) |
| Llamadas LLM | 🟡 Bajo DPA del proveedor configurado por el cliente |
| Falsificación de licencias | ✅ Respuesta firmada Ed25519 + caché HMAC; sin bypass por entorno |
| Comunicación con el servidor de licencias (Render) | ✅ HTTPS + firma del servidor verificada en cliente |
| Caída del servidor de licencias | ✅ Gracia offline local (7 días) |
| Software malicioso en máquina del cliente | ❌ Fuera de alcance (responsabilidad del entorno) |

---

## Arquitectura

```text
┌──────────────────────────────────────────────────────────────────────┐
│                      ORQUESTADOR (capa superior)                     │
│                                                                      │
│  El usuario configura reglas en lenguaje natural → se convierten en  │
│  Workflows persistentes que se ejecutan automáticamente.             │
│                                                                      │
│  • Trigger por TIEMPO: cron, intervalos                              │
│  • Trigger por EVENTO: invoice_created, invoice_paid, client_added…  │
│  • Trigger CONTINUO: regla siempre activa (ej. "todos los Excels se  │
│    rellenan así")                                                    │
│  • Reintentos con backoff, recovery de ejecuciones fallidas          │
│  • Pausa para aprobación humana en operaciones de riesgo             │
│                                                                      │
│  Implementación: services/workflow/ + APScheduler + TaskRunner       │
│  Modelo BD: Workflow + WorkflowExecution                             │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ puede generar
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    COORDINADOR GENERAL (capa media)                  │
│                                                                      │
│  El usuario lanza UNA instrucción compleja puntual → recibe UN       │
│  resultado final. Se ejecuta una sola vez.                           │
│                                                                      │
│  Flujo: Classify → Plan → Validate → Dispatch                        │
│                                                                      │
│  Implementación: agents/orchestrator/ + 14 dispatchers de dominio    │
│  Motor: LangGraph                                                    │
│  Modelo BD: Task (domain = 'coordinator')                            │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ delega en
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  AGENTES ESPECIALIZADOS (capa base)                  │
│                                                                      │
│  14 agentes de dominio, cada uno con su LangGraph propio:            │
│                                                                      │
│  accounting · banking · billing · compliance · crm                   │
│  documents · email · excel · hr · inventory                          │
│  marketing · rag · recruitment · workflow                            │
│                                                                      │
│  Superficie pública por dominio: el grafo compilado + sus @tools     │
└──────────────────────────────────────────────────────────────────────┘
```

> **Nota terminológica**: el código tiene una carpeta `agents/orchestrator/` que en la jerga del README corresponde al **Coordinador** (capa media), mientras que el **Orquestador** (capa superior) vive en `services/workflow/`. Es deuda histórica de naming. Ver [CLAUDE.md](CLAUDE.md) y [ARCHITECTURE.md](ARCHITECTURE.md).

### Reglas no negociables

1. **Los agentes pueden crear y modificar datos reales**. Acceso de escritura completo, no son "solo lectura" por defecto.
2. **Las reglas de workflow se almacenan como configuración JSON** y se interpretan dinámicamente (modo *reasoning*) o pre-compiladas (modo *deterministic*). Nada hard-coded.
3. **Los workflows son adaptativos**: si falla un paso, el orquestador replanifica y puede encadenar agentes (billing → documents → email).
4. **La BD local es la fuente de verdad**. Integraciones externas (bancos PSD2, OAuth Gmail/Outlook) son espejos o orígenes reactivos, nunca la verdad.
5. **Integridad transaccional estricta**: rollback completo si una operación compuesta falla a medias. Máquinas de estado bloquean transiciones ilegítimas. `ExecutionContext` compartido entre agentes del mismo workflow.

---

## Stack técnico

| Capa | Tecnología |
|---|---|
| Backend API | FastAPI 0.115 / Python 3.11 |
| ORM | SQLAlchemy 2.0 async + asyncpg |
| Base de datos | PostgreSQL 15 + pgvector |
| Agentes IA | LangGraph 0.2 + LangChain 0.3 |
| Tareas async | TaskRunner (asyncio) + APScheduler + Celery/Redis |
| Embeddings local | sentence-transformers + BAAI/bge-m3 |
| Frontend | Next.js 14 + React 18 + TypeScript |
| Estado UI | Zustand 4 |
| Estilos | Tailwind 3 + Radix UI |
| Visualización | ReactFlow (workflows) + Recharts |
| Generación docs | xhtml2pdf, docxtpl, mammoth, python-docx |
| Tests backend | pytest + pytest-asyncio + ruff + mypy |
| Tests frontend | Vitest + Playwright + axe-core (a11y) |
| Escritorio | Electron + Postgres portable + Python embebido + JRE 21 portable |
| Observabilidad opcional | Langfuse |

---

## Proveedores LLM

### Default desarrollo: Claude Code CLI

```env
DEFAULT_LLM_PROVIDER=claude_code
CLAUDE_CLI_PATH=C:\Users\Marcos\AppData\Roaming\npm\claude.cmd   # Windows
```

Enruta llamadas LLM por el proceso Claude Code CLI (consume la suscripción Pro/Max en lugar de créditos de API). Pensado **solo para desarrollo local**. Limitaciones: sin streaming, sin function calling nativo (los agentes usan JSON en prompt), sin contexto entre llamadas independientes.

```
LLM request → llm_factory.get_llm() → ClaudeCodeChatModel
  → spawns: claude --print --output-format json "<prompt>"
  → parsea stdout JSON → devuelve al agente
```

Mantiene una **sesión warm** precalentada (cold-start ~2s, llamadas posteriores ~200ms).

### Default producción: Anthropic

```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6
```

Sonnet 4.6 es lo más equilibrado precio/calidad para ERP. Opus 4.6 cuando se requiere precisión máxima.

### Alternativas

| Provider | Cuándo |
|---|---|
| **Gemini 2.5 Flash** | Optimizar coste — muy rápido, JSON structured output sólido |
| **OpenAI GPT-4o-mini** | Compatibilidad con stacks que ya usan OpenAI |
| **Groq Llama 3.3 70B** | Velocidad máxima para pruebas |
| **OpenRouter** | Acceso multi-modelo con una sola clave |

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

### Fallback automático

Si el proveedor principal falla (timeout, rate limit, 429), el sistema reintenta con backoff exponencial (30s → 60s → 120s) y puede caer a un proveedor secundario configurado. Ver `backend/app/core/llm_factory.py`.

> **Ollama no está soportado** en la versión actual. Si un cliente requiere inferencia 100% local, reintegrarlo es un desarrollo de 1–2 días.

---

## Sistema RAG y embeddings

### Motor de búsqueda semántica

pgvector almacena vectores de chunks de documentos. Búsqueda híbrida: keywords en nombre + semántica (cosine distance).

### Embeddings local (por defecto)

```env
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3
```

`BAAI/bge-m3` se descarga la primera vez (~600MB). Multilingüe (español nativo), estado del arte para búsqueda semántica, **completamente offline** sin coste por llamada.

### Alternativa cloud

```env
EMBEDDINGS_PROVIDER=gemini
GEMINI_API_KEY=AIza...
```

### Pipeline de ingesta

```
PDF subido
  ↓
PDF Parser (OpenDataLoader/Java → fallback pypdf)
  ↓  ParsedDocument: markdown + elementos (tablas, párrafos, headings)
Clasificación mecánica (regex + keywords, 0 tokens LLM en ~90% docs)
  ↓  Tipo: factura_recibida | nómina | extracto_bancario | contrato | otro
  ↓  Entidades extraídas: NIF, importes, fechas, IBAN
Smart Chunker (respeta estructura del PDF)
  ↓  Chunks con metadatos: página, tipo de elemento, bounding box
Embedder (BAAI/bge-m3, 1024 dim)
  ↓
DocumentEmbedding (JSONB) — listo para RAG
```

**OpenDataLoader** (Java) extrae markdown + JSON estructurado de PDFs con metadatos: tipo de elemento, página, bounding box. Si no hay JRE, cae a `pypdf`. En Electron se auto-descarga Adoptium JRE 21.

**Clasificador sin tokens** (`backend/app/services/documents/classifier.py`): regex para patrones españoles (NIF, IBAN, importes). Solo llama al LLM si confianza < 0.7 (~10% de docs). Ahorra tokens masivamente.

**Smart Chunker** (`backend/app/services/documents/smart_chunker.py`):
- Tablas nunca se parten (chunk atómico)
- Headings inician chunk nuevo
- Párrafos se agrupan hasta 2000 caracteres
- Preserva página, tipo, bounding box por chunk

### Almacenamiento

```
document_embeddings:
  document_id, tenant_id, chunk_index, text_content,
  page_number, element_type (table|paragraph|heading),
  bounding_box (JSONB), embedding (JSONB, lista de floats)
```

> Los embeddings se guardan en una columna **JSONB**, no en `pgvector`: la app
> desktop distribuye un Postgres portable sin la extensión `pgvector`. La
> búsqueda por similitud se hace en Python (coseno) sobre los vectores cargados.
> La dimensión depende del proveedor: **1024** con `BAAI/bge-m3` (local, por
> defecto), 1536 con `text-embedding-3-small` (OpenAI).

### Consulta RAG (`agents/rag/`)

1. Keywords en nombre de archivo (filtrado rápido)
2. Búsqueda semántica por similitud coseno en Python (`cosine_topk`)
3. Contexto enriquecido con páginas y tipos
4. LLM sintetiza respuesta con citas a fuentes específicas

---

## Empleados IA personalizables

El módulo `/mi-equipo` permite crear **agentes IA personalizados** que actúan como empleados virtuales con nombre, rol, dominio, system prompt y un conjunto de skills.

### API

| Endpoint | Descripción |
|---|---|
| `GET /ai-employees` | Listar empleados IA del tenant |
| `POST /ai-employees` | Crear empleado (manual o vía LLM desde descripción NL) |
| `POST /ai-employees/{id}/instruct` | Instrucción en lenguaje natural → pasa por el coordinador |
| `PATCH /ai-employees/{id}/status` | Cambiar estado (idle, paused) |
| `POST /ai-employees/seed` | Generar equipo inicial predefinido |
| `GET /activity-feed` | Feed de actividad de todos los empleados |

### Dominios disponibles

`billing` · `documents` · `compliance` · `hr` · `banking` · `crm` · `excel` · `email` · `marketing` · `recruitment`

### Catálogo de skills (~45)

Cada empleado se compone de skills del catálogo (`AVAILABLE_SKILLS` en `backend/app/agents/agent_tools/ai_team.py`). Ejemplos:

- `billing.create_invoice`, `billing.send_invoice_by_email`, `billing.search_client`
- `hr.calculate_and_create_payroll`, `hr.approve_payroll`
- `crm.qualify_leads`, `crm.update_opportunity_stage`
- `banking.reconcile_transactions`, `banking.financial_summary`
- `documents.classify_document`, `documents.search_documents_semantic`
- `compliance.check_boe_news`, `compliance.fiscal_query`
- `recruitment.process_cv`, `recruitment.update_candidate_status`

### Flujo de instrucciones

```
Usuario escribe mensaje NL al empleado
  ↓
Coordinador analiza la instrucción
  ↓
Descompone en subtareas
  ↓
Despacha a agentes especializados
  ↓
Activity feed + log inmutable
```

### Budget guard

Cada empleado tiene `budget_limit_usd`. El worker `budget_guard.py` vigila el consumo de tokens por empleado y pausa si excede.

---

## Tareas vs Automatizaciones

El sistema tiene **dos mecanismos de entrada completamente distintos**:

### 🔵 TAREAS — Acción puntual (`/tareas`)

Instrucción única que el usuario lanza en el momento.
- Se ejecuta **una sola vez**
- El usuario ve el resultado, lo aprueba o cancela
- Persistida en `Task` + `agent_results` + `AuditLog`

### 🟢 AUTOMATIZACIONES — Regla persistente (`/automatizaciones`)

Regla que el usuario define una vez y el sistema ejecuta cada vez que se cumple una condición.

**Triggers**:
- **Tiempo**: *"cada lunes"*, *"cada trimestre"*, cron
- **Evento**: *"cuando se cree una factura > 5.000€"*

Persistida en `Workflow`. Cada ejecución crea `WorkflowExecution` y puede generar `Task`s hijas.

**Modos**:
- **Determinista**: grafo de nodos fijo definido visualmente
- **Razonamiento**: LLM crea el plan dinámicamente

**Prevención de duplicados**: si hay una ejecución `running` o `pending` para un workflow, las nuevas se bloquean (HTTP 409 en API, skip silencioso en scheduler).

> **Regla de oro**: Una automatización puede generar tareas. Una tarea jamás crea automatizaciones.

---

## Multi-tenancy y BD

Todos los modelos tienen `tenant_id: UUID`. Los endpoints filtran siempre por `current_user.tenant_id`. **No hay datos compartidos entre tenants**.

### Modelos principales (~23 archivos en `db/models/`)

```
auth           → users, password_reset_tokens
tenant         → tenants, tenant_integrations, tenant_llm_config
billing        → invoices, invoice_lines, invoice_series, clients, products, quotes
hr             → employees, payrolls
hr_documents   → documentos laborales generados con IA
crm            → opportunities, activities, events, reservations
accounting     → journal_entries, journal_lines, fixed_assets
inventory      → stock_items
orders         → purchase_orders, sales_orders
projects       → projects, project_members, tasks
pos            → pos sessions, tickets
calendar       → calendar_events
tasks          → tasks (IA), audit_log, pending_approvals, domain_events
workflows      → workflows, workflow_executions
embeddings     → document_embeddings (pgvector)
ai_employees   → ai_employees, agent_skills
generative_ui  → ui_generations
metering       → llm_usage (tokens consumidos por tenant/agente)
notifications  → notifications
alerts         → alerts + alert rules
backup         → backup_records
```

### Migraciones

```bash
# Crear migración
alembic revision --autogenerate -m "descripcion"

# Aplicar
alembic upgrade head

# Ver historial
alembic history
```

> **Regla**: siempre crear migración Alembic al añadir/modificar campos. Nunca modificar tablas directamente en producción.

---

## Integraciones OAuth

### Google (Gmail + Drive)

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Un OAuth habilita Gmail y Drive. Scopes: `gmail.readonly`, `gmail.send`, `drive.file`, `drive.readonly`.

### Microsoft (Outlook + OneDrive)

```env
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

Un OAuth habilita Outlook y OneDrive. Scopes: `Mail.Read`, `Mail.Send`, `Files.ReadWrite`.

### Flujo

```
Frontend abre popup
  → backend /oauth/{provider}/start
  → redirect a Google/Microsoft
  → callback /oauth/{provider}/callback
  → intercambia code por tokens
  → tokens cifrados con PBKDF2+Fernet en TenantIntegration
```

El estado OAuth usa un dict en memoria con TTL 10 min (limpieza automática).

---

## Seguridad

### Variables críticas

```env
# Generar con: openssl rand -hex 32
SECRET_KEY=...

# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TENANT_ENCRYPTION_KEY=...
```

La aplicación **no arranca** si estas variables tienen valores por defecto. Es intencional.

### Medidas implementadas

- **JWT**: HS256, access 60min + refresh 30 días
- **CORS**: restringido a métodos y headers específicos
- **Rate limiting**: slowapi en endpoints de auth
- **Upload validation**: extensiones permitidas + límite 50MB
- **Prompt injection**: `prompt_sanitizer.py` aplicado en agentes
- **Security headers**: X-Content-Type-Options, X-Frame-Options, HSTS, CSP
- **Cifrado de credenciales**: PBKDF2 (100k iteraciones) + Fernet para tokens OAuth
- **Audit log inmutable**: WORM, requerido por compliance fiscal
- **DB indexes**: compuestos en `tenant_id + created_at`

---

## Servidor de licencias y proxy OAuth (Render + Neon)

El cliente valida su licencia y enruta el OAuth de redes sociales contra un
servidor propio. **No es un VPS**: son servicios gestionados (cold start incluido).

### Topología

```
  App escritorio  ──HTTPS──►  Render (FastAPI)      ──►  Neon (PostgreSQL)
  (valida/activa)             license-server             tabla `licenses`
                              + proxy OAuth              (persistente)
```

- **Render** corre el `license-server` (FastAPI): valida/activa licencias, **firma
  las respuestas con Ed25519**, y hace de **proxy OAuth** de redes sociales (el
  `client_secret` de Meta/X vive aquí, nunca en el binario distribuido).
- **Neon** es la base de datos PostgreSQL **persistente** (plan gratis). Render se
  conecta vía `DATABASE_URL`. Sustituye al SQLite efímero anterior, que se borraba
  en cada redeploy. La app **nunca** habla con Neon — solo con Render; Neon es
  almacenamiento pasivo (el "disco" de licencias que no se borra).

### Variables de entorno en Render

| Variable | Para qué |
|----------|----------|
| `DATABASE_URL` | Connection string de Neon (Postgres persistente). |
| `ADMIN_TOKEN` | Protege el panel y la API de administración (`/admin`). |
| `LICENSE_SIGNING_KEY` | Privada Ed25519 (base64) que firma `/validate`. Su pública va incrustada en el cliente (`core/license.py`). |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*` | Alta automática de licencias al completarse el pago. |
| `SMTP_*` | Envío opcional de la clave por email. |
| `FACEBOOK_*`, `INSTAGRAM_*`, `TWITTER_*`, `LINKEDIN_*` `_CLIENT_SECRET` | Secrets del proxy OAuth (no viajan al cliente). |

> El cliente activa el proxy con `OAUTH_PROXY_URL`; si está vacío, usa el secret
> local (fallback). Google se queda local con PKCE (su token de Gmail no transita
> el servidor).

### Gestión de licencias (sin tocar código)

Panel web protegido por `ADMIN_TOKEN`:

```
https://automatizapyme-license-server.onrender.com/admin
```

Crear, listar, revocar, reactivar, **liberar equipo** (`reset-machine`) y borrar
licencias, con **caducidad opcional en días**. Mismas acciones por API
(`POST/GET/DELETE /admin/licenses…` con cabecera `X-Admin-Token`).

### Validación, firma y gracia offline

`POST /licenses/validate` responde firmada con Ed25519 (`nonce:plan`). El cliente
verifica la firma contra la pública incrustada → rechaza servidores falsos. Caché
local 24 h y **gracia offline de 7 días** si el servidor no responde. Sin bypass
por entorno (no existe `AP_DEVMODE`).

### Setup nuevo (resumen)

1. Crear proyecto en [Neon](https://neon.tech) → copiar el connection string.
2. En Render → Environment: `DATABASE_URL`, `ADMIN_TOKEN`, `LICENSE_SIGNING_KEY`
   (+ las de Stripe/SMTP/OAuth). Guardar → redeploy.
3. Abrir `/admin`, introducir el `ADMIN_TOKEN` y emitir la primera licencia.

---

## Arranque rápido

### Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (o usar el portable de `desktop/`)
- Git

### Variables mínimas

Copia `.env.example` a `.env` y configura al menos:

```env
SECRET_KEY=<openssl rand -hex 32>
TENANT_ENCRYPTION_KEY=<fernet key>
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Desarrollo

```bat
levantar.bat
```

Accesos:
- Frontend: http://localhost:3000
- API docs: http://localhost:8080/docs
- Usuario demo: `demo@automatizacore.com` / `Demo1234!`

### Producción (Electron)

Ejecuta la app Electron desde `desktop/`. Arranca automáticamente PostgreSQL portable, el backend y el frontend.

### Datos de demo

```bash
python smoke_demo.py              # Datos de demostración
python smoke_tasks_workflows.py   # Tareas IA de ejemplo
```

### Hot-reload al exe instalado

```bash
 cd desktop && npm run sync          # Sincroniza cambios al exe instalado
cd desktop && npm run sync:rebuild   # Igual + rebuild del frontend antes de copiar
```

### Auto-update y releases

El desktop usa `electron-updater` con provider GitHub (`desktop/package.json` →
`build.publish`). El wiring de código está completo: `main.js` →
`lib/update-channel.js` (canales `stable`/`beta`) → `electron-updater` →
`checkForUpdates()` al arranque y `quitAndInstall()` vía IPC.

**Build de release:**

```bash
cd frontend && npm run build   # build de producción (.next)
cd desktop && npm run dist     # electron-builder → dist/*.exe + latest.yml + app-update.yml
```

**⚠️ Antes de publicar una release distribuible (3 requisitos):**

1. **El `app-update.yml` se hornea en build-time** desde `build.publish`. Un
   instalador buscará updates en el `owner/repo` que tenía esa config al
   construirse — cambiar el destino exige **reconstruir**, no basta editar el repo.
2. **Repo de releases público.** `electron-updater` no puede actualizar clientes
   desde un repo **privado** sin un token embebido en la app (inseguro). Para
   distribución real, publica en un repo público (p.ej. `automatizacore-releases`)
   o usa otro canal (S3/genérico). El repo de código puede seguir privado.
3. **Sanear `.env`.** `build.extraResources` copia `../.env` dentro del
   instalador. En producción el `.env` empaquetado debe llevar **placeholders**;
   los secretos reales (API keys, `SECRET_KEY`, encryption key) se resuelven en
   runtime vía Electron `safeStorage`, nunca horneados en el artefacto.

**Publicar** (tras cubrir lo anterior y subir la versión en `package.json`):

```bash
# electron-builder publica si GH_TOKEN está seteado y se pasa --publish always,
# o manualmente con gh:
gh release create v1.0.1 "dist/AutomatizaCore Setup 1.0.1.exe" \
  "dist/latest.yml" -R <owner>/<repo-releases>
```

El updater solo dispara la actualización si la versión publicada es **mayor**
que la instalada.

### Tests

```bash
pytest tests/ -v                       # Suite completa (215 ficheros de test)
pytest tests/test_routing_seam.py -v   # Costuras críticas de routing
pytest --cov=app --cov-report=term     # Con cobertura

cd frontend && npm test                # Frontend (Vitest)
cd frontend && npm run test:e2e        # E2E (Playwright)
cd frontend && npm run test:a11y       # Accesibilidad (axe-core)
```

#### Tests del seam de routing

`test_routing_seam.py` cubre 7 costuras críticas en la cadena de invocación de agentes (modal → parse-nl → blueprint → NodeEngine → dispatcher → AIEmployee):

1. `generate_preview_nodes` asigna `data.employee_id` para AIEmployees custom
2. `generate_preview_nodes` usa el built-in con su nombre real
3. `_plan_from_blueprint` propaga `data.employee_id` → `params.employee_id`
4. `build_skill_dispatch` (NodeEngine) propaga `data.employee_id` al subtask
5. `plan_node` hace swap a custom cuando hay 1 match en el dominio
6. `classifier._resolve_custom_employee` filtra por `is_builtin=False`
7. `_invoke_dispatcher_impl` enruta `agent="custom"` al dispatcher dinámico

---

## Limitaciones conocidas

| Limitación | Notas |
|---|---|
| **Inferencia LLM cloud** | El contenido del usuario se envía al proveedor LLM configurado. Para clientes con requisitos estrictos de no-cloud, hay que reintegrar Ollama o LLM autohospedado (1–2 días de trabajo). |
| **Sin clientes en producción** | A fecha de este README, el sistema está validado en testing pero no ha cerrado un ciclo fiscal real con AEAT. |
| **Cobertura de tests baja** | 215 ficheros de test (~2.100 funciones) para 67K LOC backend. El seam crítico de routing está cubierto, el resto no. |
| **Carga inicial de BAAI/bge-m3** | ~30s la primera vez (descarga ~600MB) |
| **Cron muy frecuentes** | `*/2 * * * *` o más frecuente puede saturar si la tarea es larga |
| **Groq tier gratuito** | Rate limit agresivo; usar Anthropic o Gemini en producción |
| **Servicios en memoria** | Cache LLM, idempotencia, exec logs se pierden al reiniciar. Aceptable para ERP local single-user. |
| **TicketBAI / regionales** | País Vasco y Navarra requerirían adaptación de Verifactu actual |
| **Facturae export** | No confirmado como compatible al 100% con AEAT — verificar |
| **OAuth redirect URIs** | Requieren configuración en Google Cloud Console / Azure AD |
| **Sin app móvil** | Solo desktop + web |

---

## Documentación adicional

| Documento | Para qué |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Reglas de arquitectura, contrato `run_agent()`, capas, convenciones de código |
| [CLAUDE.md](CLAUDE.md) | Reglas para asistentes IA (Claude Code) que trabajan en este repo |
| [AGENTS.md](AGENTS.md) | Detalle de los 14 agentes especializados |
| [SCOPE.md](SCOPE.md) | Alcance funcional histórico |
| [MARKETING.md](MARKETING.md) | Mensajes y positioning |
| [tasks/roadmap.md](tasks/roadmap.md) | Roadmap detallado por sprints |
| [tasks/analisis-proyecto-2026-05-17.md](tasks/analisis-proyecto-2026-05-17.md) | Análisis profundo del estado actual (mayo 2026) |
| [tasks/lessons.md](tasks/lessons.md) | Lecciones aprendidas |
| [GITNEXUS.md](GITNEXUS.md) | Cómo usar GitNexus para navegar el código |

---

## Convenciones rápidas

### Backend

- **Endpoints**: `backend/app/api/v1/routes/<dominio>.py` — un archivo por módulo
- **Modelos BD**: `backend/app/db/models/<dominio>.py` — siempre crear migración al cambiar
- **LLM**: llamar siempre vía `get_llm()` en `llm_factory.py`. Nunca instanciar `ChatOpenAI` etc. directamente.
- **Embeddings**: llamar siempre vía `get_embedder()`. Nunca instanciar `HuggingFaceEmbeddings` directamente.
- **Agentes**: exportan solo `run_agent()`. Devuelven `AgentResult(success, message, data, error)`.
- **Tareas async**: despachar vía `task_dispatch.dispatch_task()`, nunca llamar directamente.

### Frontend

- **API calls**: siempre vía `frontend/src/lib/api/*.ts`. **Nunca `fetch()` directo**.
- **Tipos compartidos**: cuando se añade un tipo a `lib/api/erp.ts`, actualizar también `lib/api.ts` (TS resuelve al `.ts` antes que al directorio).
- **Errores**: `logError(contexto, error)` de `logger.ts`. Nunca `console.error`.
- **Descargas autenticadas**: `fetch()` con JWT en `Authorization` header.

### Reglas generales

- Multi-tenancy: todos los queries filtran por `tenant_id`
- Nunca hardcodear IDs, URLs de backend, ni claves API en código fuente
- El coordinador (`agents/orchestrator/_core.py`) es el único punto de entrada para agentes desde el task runner
- Las automatizaciones no pueden tener dos ejecuciones simultáneas (HTTP 409)

---

*Última actualización: 2026-06-15 · 14 agentes · 69 rutas · 96 clases ORM · 60 migraciones · 215 ficheros de test + E2E Playwright*
