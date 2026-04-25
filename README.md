# AutomatizaPyme — ERP SaaS Multiagente para PYMEs

Plataforma de automatización administrativa para PYMEs españolas. El usuario gestiona facturación, RRHH, contabilidad, banca y CRM mediante **lenguaje natural**. Los agentes IA ejecutan las acciones y escriben directamente en la base de datos.

---

## CONTEXTO DEL PROYECTO — Leer antes de cualquier cambio

> Esta sección es de lectura obligatoria para cualquier modelo de IA o desarrollador que trabaje en este repositorio. Resume la visión central, los principios de diseño y el comportamiento esperado del sistema.

### Visión central

AutomatizaPyme es un **ERP inteligente local-first**. Cada cliente instala la aplicación en su propia máquina como app de escritorio (Electron). Los datos nunca salen de su entorno local. La app requiere conexión a internet únicamente para validar la licencia activa contra un servidor central (VPS) y para llamar a las APIs de LLM configuradas.

```
┌──────────────────────────────────────────┐        ┌─────────────────────────┐
│           CLIENTE (local)                │        │    VPS LICENCIAS        │
│                                          │        │                         │
│  Electron (PostgreSQL portable + Python) │◄──────►│  Servidor de licencias  │
│  Next.js Frontend                        │  HTTPS │  - Valida clave mensual │
│  FastAPI (uvicorn directo)               │        │  - Gestiona pagos       │
└──────────────────────────────────────────┘        └─────────────────────────┘

### Por qué este modelo

| Ventaja | Explicación |
|---|---|
| **Privacidad de datos** | La BD del cliente está en su máquina. Cero exposición de datos contables, nóminas o clientes a terceros. Argumento de venta muy fuerte frente a SaaS cloud. |
| **Sin riesgo de brecha masiva** | Un ataque al VPS no compromete datos de ningún cliente — el servidor solo sabe si la licencia es válida, pero no tiene acceso a los datos del ERP. |
| **Las claves API son del propio cliente** | Cada usuario configura sus propias API keys (Gemini, Anthropic, OpenAI) en su entorno local. AutomatizaPyme no centraliza ni tiene acceso a esas claves. Si una key se filtra, es problema del entorno de ese cliente. |

### Modelo de responsabilidad y Seguridad

La **única amenaza real** que compete al código de la aplicación en este modelo es que **software malicioso en la máquina del cliente** pueda interceptar la app. Por eso el enfoque de seguridad se centra en:
1. **Integridad del código distribuido**: El empaquetado final está ofuscado para proteger el mecanismo de validación de licencias del pago mensual.
2. **Comunicaciones cifradas**: Todas las llamadas al VPS de licencias viajan pre-cifradas por HTTPS.
3. **Punto único de fallo mitigable**: Si el servidor de licencias (VPS) cae, existe un periodo de gracia local para que las PYMEs no detengan su operativa diaria al intentar revalidar.
```

---

## Stack técnico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend API | FastAPI (Python) | 3.11 / 0.115 |
| Agentes IA | LangGraph | 0.2+ |
| Tareas async | TaskRunner (asyncio) + APScheduler | — |
| Base de datos | PostgreSQL + pgvector | 15 |
| Frontend | Next.js + React + TypeScript | 14 / 18 |
| Estado UI | Zustand | 4 |
| Estilos | Tailwind CSS | 3 |
| Escritorio | Electron | — |

---

## Proveedores LLM

### Proveedor por defecto (desarrollo): Claude Code CLI

```env
DEFAULT_LLM_PROVIDER=claude_code
# No requiere ANTHROPIC_API_KEY — usa la sesión activa de Claude Code CLI
```

Este es el proveedor activo por defecto en desarrollo. Enruta todas las llamadas LLM a través del proceso **Claude Code CLI** (`claude`) en lugar de la API REST de Anthropic. Consume el plan de suscripción de Claude (Pro/Max) en lugar de generar créditos de API.

**Requisitos:**
- Tener instalado Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- Haber iniciado sesión: `claude` (primera vez abre el navegador para autenticarse)
- El binario `claude` debe ser accesible desde el PATH o configurarse explícitamente:

```env
CLAUDE_CLI_PATH=C:\Users\Marcos\AppData\Roaming\npm\claude.cmd   # Windows
# CLAUDE_CLI_PATH=/usr/local/bin/claude                           # Linux/macOS
```

**Cómo funciona internamente:**

```
LLM request → llm_factory.get_llm() → ClaudeCodeChatModel
  → spawns: claude --print --output-format json "<prompt>"
  → parsea stdout JSON → devuelve respuesta al agente
```

El provider mantiene una **sesión warm** precalentada (cold-start ~2s, llamadas posteriores ~200ms). La sesión se reutiliza entre llamadas para minimizar la latencia.

**Limitaciones:**
- No soporta streaming (output completo de una vez)
- No soporta function calling nativo (los agentes utilizan JSON en el prompt)
- El contexto de conversación no se mantiene entre llamadas independientes
- Requiere que `claude` esté activo y autenticado — si caduca la sesión, el sistema cae al proveedor de fallback

**Diagnóstico si no funciona:**

```bash
# Comprobar que el CLI responde correctamente
claude --print "Di hola"

# Ver qué path se está usando
where claude          # Windows
which claude          # Linux/macOS

# Forzar re-autenticación
claude --logout && claude
```

> **Nota**: Este proveedor está pensado para **desarrollo local**. En producción (clientes) usar `anthropic` con su propia API key.

### Proveedor recomendado para producción: Anthropic (Claude)

```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6        # claude-sonnet-4-6 | claude-opus-4-6
```

**Recomendación**: Claude Sonnet 4.6 es el más equilibrado en precio/calidad para tareas de ERP. Claude Opus 4.6 para tareas que requieren máxima precisión. Usar este proveedor en despliegues a clientes.

### Proveedor alternativo recomendado: Gemini

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash
```

Gemini 2.5 Flash es la mejor alternativa — muy rápido, coste muy bajo, buen soporte de JSON structured output. Recomendado si se quiere optimizar costes.

### Otros proveedores soportados

```env
# Groq — velocidad máxima, bueno para pruebas
DEFAULT_LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
GROQ_MODEL=llama-3.3-70b-versatile

# OpenAI
DEFAULT_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# OpenRouter — acceso a múltiples modelos con una sola clave
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-opus-4-6
```

### Lógica de fallback automático

El sistema tiene fallback automático: si el proveedor principal falla (timeout, rate limit, 429), reintenta con backoff exponencial (30s → 60s → 120s) y puede caer a un proveedor secundario configurado. Ver `backend/app/core/llm_factory.py`.

> **Ollama ha sido eliminado.** Ya no se usa ni se soporta ningún modelo local mediante Ollama.

---

## Sistema de Embeddings y RAG

### Motor de búsqueda semántica

El sistema RAG usa **pgvector** (extensión de PostgreSQL) para almacenar y buscar vectores de embeddings. Los documentos subidos se fragmentan en chunks y se vectorizan automáticamente al subirse.

### Proveedor de embeddings: HuggingFace (local, por defecto)

```env
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3
```

El modelo `BAAI/bge-m3` de HuggingFace se descarga automáticamente la primera vez. Es multilingüe (español nativo), estado del arte para búsqueda semántica, y funciona completamente offline sin coste por llamada.

### Alternativa: Gemini Embeddings

```env
EMBEDDINGS_PROVIDER=gemini
GEMINI_API_KEY=AIza...
```

Usar si se quiere evitar la carga de memoria del modelo local (~500MB RAM).

### Flujo RAG completo

```
Documento subido → chunks (500 tokens) → BAAI/bge-m3 → vector float[] → pgvector
Consulta usuario → vector query → cosine_distance en BD → top-K chunks → Claude/Gemini
```

El agente RAG (`rag_agent.py`) combina el modelo de embeddings pequeño (BAAI/bge-m3) con el LLM principal (Anthropic/Gemini) para responder preguntas sobre documentos del tenant.

### Pipeline de ingesta: OpenDataLoader + clasificación + chunking inteligente

Cuando se sube un documento, el sistema ejecuta un pipeline completo antes de que sea consultable por RAG:

```
PDF subido
  ↓
PDF Parser (OpenDataLoader → fallback pypdf)
  ↓  ParsedDocument: markdown + elementos estructurados (tablas, párrafos, headings)
Clasificación mecánica (regex + keywords, 0 tokens LLM en ~90% de documentos)
  ↓  Tipo: factura_recibida | nómina | extracto_bancario | contrato | otro
  ↓  Entidades extraídas: NIF, importes, fechas, IBAN
Smart Chunker (respeta estructura del PDF)
  ↓  Chunks con metadatos: página, tipo de elemento, bounding box
Embedder (BAAI/bge-m3, 768 dimensiones)
  ↓
DocumentEmbedding (pgvector) → listo para consultas RAG
```

#### OpenDataLoader — Parser de PDFs estructurado

El parser principal usa **OpenDataLoader** (Java) para extraer markdown + JSON estructurado de PDFs. Captura tipo de elemento (párrafo, tabla, heading), número de página y bounding box. Si Java no está disponible (ej: sin JRE), cae automáticamente a `pypdf`.

- **Código**: `backend/app/services/pdf_parser.py`
- **JRE portable**: en Electron, se auto-detecta el JRE de AppData; si no existe, se descarga Adoptium JRE 21
- **Modelo de datos**: `ParsedDocument` (markdown completo + lista de `ParsedElement` con metadatos)

#### Clasificación sin coste de tokens

El clasificador (`backend/app/services/document_classifier.py`) usa reglas regex para detectar patrones españoles (NIF, IBAN, importes). Solo llama al LLM si la confianza es < 0.7 (~10% de documentos). Esto ahorra tokens masivamente en tenants con muchos documentos.

#### Smart Chunker — Chunking consciente de estructura

Cuando OpenDataLoader proporciona elementos estructurados, el chunker (`backend/app/services/smart_chunker.py`) respeta la estructura del PDF:
- **Tablas**: nunca se parten (chunk atómico)
- **Headings**: inician un chunk nuevo
- **Párrafos**: se agrupan hasta 2000 caracteres
- **Metadatos preservados**: página, tipo de elemento, bounding box por chunk

Esto permite que las respuestas del RAG citen la **página exacta** y el **tipo de contenido** (tabla vs párrafo) de donde viene la información.

#### Almacenamiento vectorial enriquecido

La tabla `document_embeddings` almacena cada chunk con sus metadatos:

```
document_embeddings:
  document_id, tenant_id, chunk_index, text_content,
  page_number, element_type (table|paragraph|heading),
  bounding_box (JSONB), embedding (pgvector 768-dim)
```

#### Consulta RAG (rag_agent.py)

El agente RAG ejecuta búsqueda híbrida:
1. **Keywords en nombre de archivo** (filtrado rápido)
2. **Búsqueda semántica** vía pgvector (cosine distance)
3. **Contexto enriquecido** con páginas y tipos de elemento
4. **LLM sintetiza respuesta** con citas a fuentes específicas

---

## Arquitectura de tres capas

```text
┌──────────────────────────────────────────────────────────────────────┐
│                      ORQUESTADOR (capa superior)                     │
│                                                                      │
│  El usuario configura reglas en lenguaje natural → el sistema las    │
│  convierte en Workflows persistentes. Una vez configurado, se ejecuta│
│  automáticamente. El usuario puede reconfigurar en cualquier momento.│
│                                                                      │
│  Funciones:                                                          │
│  • Configurar reglas en lenguaje natural ("hazme la nómina de este   │
│    cliente en Excel todos los días a las 14:00")                     │
│  • Reconfigurar workflows: añadir pasos, eliminar tareas, cambiar    │
│    horarios sin recrear el flujo desde cero                          │
│  • Trigger por TIEMPO: diario, semanal, mensual, cada X horas...     │
│  • Trigger por EVENTO: "cada vez que entre un archivo en la BD,      │
│    rellena automáticamente cliente, proyectos y facturas"            │
│  • Trigger CONTINUO/PERMANENTE: regla siempre activa sin evento ni   │
│    horario. Ej: "todos los Excels se rellenan siempre de esta forma" │
│    → el sistema aplica la norma de forma ininterrumpida              │
│  • Ejecutar múltiples workflows en paralelo por tenant               │
│  • Reintentar ejecuciones fallidas con parámetros ajustados          │
│  • Pausar y esperar aprobación humana en operaciones de riesgo       │
│                                                                      │
│  Modelo BD: Workflow + WorkflowExecution                             │
│  Motor: APScheduler + TaskRunner + LangGraph                         │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ puede generar
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    COORDINADOR GENERAL (capa media)                  │
│                                                                      │
│  El usuario lanza UNA instrucción compleja puntual → recibe UN       │
│  resultado final. Se ejecuta una sola vez. No crea reglas.           │
│                                                                      │
│  Funciones:                                                          │
│  • Descomponer la tarea compleja en subtareas secuenciales           │
│  • Asignar cada subtarea al agente especializado correcto            │
│  • Pasar el contexto y resultado de cada paso al siguiente           │
│  • Consolidar el output final (informe, PDF, email enviado...)       │
│                                                                      │
│  Ejemplo puntual: «Rellena las nóminas con estos modelos para        │
│  presentar el IRPF» → se ejecuta una vez y finaliza                  │
│                                                                      │
│  Modelo BD: Task (domain = 'coordinator')                            │
│  Motor: LangGraph (Classify → Plan → Validate → Dispatch)            │
└───────────────────────────┬──────────────────────────────────────────┘
                            │ delega en
                            ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  AGENTES ESPECIALIZADOS (capa base)                  │
│                                                                      │
│  Cada agente es experto en un único dominio.                         │
│  Reciben una instrucción concreta y devuelven un resultado tipado.   │
│                                                                      │
│  billing  │ documents │ compliance │ hr │ banking                    │
│  crm      │ excel     │ email      │ rag                             │
│                                                                      │
│  Motor: LangGraph por agente + LLM (Gemini / Anthropic / OpenAI)     │
└──────────────────────────────────────────────────────────────────────┘
```

### Agentes disponibles

| Agente | Dominio | Descripción |
|--------|---------|-------------|
| `billing_agent.py` | billing | Facturas, presupuestos, clientes, cobros |
| `hr_agent.py` | hr | Empleados, nóminas, contratos |
| `crm_agent.py` | crm | Oportunidades, actividades, clientes potenciales |
| `banking_agent.py` | banking | Movimientos bancarios, conciliación |
| `documents_agent.py` | documents | Subida, búsqueda y clasificación de documentos |
| `compliance_agent.py` | compliance | Normativa, modelos tributarios, LOPD |
| `excel_agent.py` | excel | Importación y exportación de hojas de cálculo |
| `email_agent.py` | email | Redacción y envío de emails (Gmail/Outlook) |
| `rag_agent.py` | rag | Preguntas sobre documentos propios del tenant |
| `workflow_agent.py` | workflow | Gestión de automatizaciones |

### Empleados IA personalizables (`/mi-equipo`)

El sistema permite crear **agentes IA personalizados** que actúan como empleados virtuales de la empresa. Cada empleado IA tiene nombre, rol, dominio, system prompt y un conjunto de skills asignados.

| Endpoint | Descripción |
|----------|-------------|
| `GET /ai-employees` | Listar todos los empleados IA del tenant |
| `POST /ai-employees` | Crear nuevo empleado IA (manual o vía LLM desde descripción) |
| `POST /ai-employees/{id}/instruct` | Dar instrucción en lenguaje natural → pasa por el coordinador |
| `PATCH /ai-employees/{id}/status` | Cambiar estado (idle, paused) |
| `POST /ai-employees/seed` | Generar equipo inicial predefinido |
| `GET /activity-feed` | Feed de actividad de todos los empleados IA |

**Dominios disponibles**: billing, hr, email, crm, banking, compliance, excel, documents, marketing, recruitment.

**Flujo de instrucciones**: El usuario envía un mensaje en lenguaje natural al empleado → el coordinador analiza la instrucción → la descompone en subtareas → las despacha al agente especializado correspondiente → el resultado se registra en el activity feed.

### Sandbox Generativo (`/sandbox`)

Permite generar **interfaces UI completas desde lenguaje natural**. El usuario describe qué necesita ("un dashboard de ventas con gráfico de barras") y el LLM genera HTML/CSS renderizable al instante.

| Endpoint | Descripción |
|----------|-------------|
| `POST /generative-ui/generate` | Generar interfaz desde prompt |
| `GET /generative-ui/history` | Historial de interfaces generadas |
| `PATCH /generative-ui/{id}` | Editar título/descripción |
| `DELETE /generative-ui/{id}` | Eliminar interfaz |

### Documentos RRHH generados por IA (`/rrhh/documentos`)

Genera documentos laborales (contratos, cartas, certificados) con IA a partir de los datos del empleado.

| Endpoint | Descripción |
|----------|-------------|
| `POST /hr-documents/generate` | Generar documento RRHH con IA |
| `GET /hr-documents` | Listar documentos generados |
| `POST /hr-documents/{id}/approve` | Aprobar documento para firma |
| `DELETE /hr-documents/{id}` | Eliminar documento |

### Reclutamiento con análisis IA de CVs (`/rrhh/reclutamiento`)

Módulo completo de reclutamiento: crear posiciones, subir CVs de candidatos, y análisis automático con IA que puntúa compatibilidad.

| Endpoint | Descripción |
|----------|-------------|
| `GET /recruitment/positions` | Listar posiciones abiertas |
| `POST /recruitment/positions` | Crear nueva posición |
| `POST /recruitment/positions/{id}/upload-cv` | Subir CV de candidato (PDF) |
| `PATCH /recruitment/candidates/{id}/status` | Cambiar estado del candidato |
| `POST /recruitment/analyze-cv` | Análisis IA del CV vs requisitos del puesto |

### Ejecución de automatizaciones (Orquestador)

Las automatizaciones tienen dos modos:
- **Determinista**: sigue un grafo de nodos fijo definido visualmente en el editor
- **Razonamiento**: el LLM crea el plan dinámicamente según la instrucción

Cada automatización puede dispararse por:
- **Tiempo** (cron): `*/2 * * * *` — evaluado por `check_scheduled_workflows` cada minuto via APScheduler
- **Evento**: `invoice_created`, `invoice_paid`, `client_added`, etc.

**Prevención de duplicados**: si ya hay una ejecución `running` o `pending` para un workflow, el sistema bloquea nuevas ejecuciones (HTTP 409 en API manual, skip silencioso en scheduler).

---

## ⚡ Los dos tipos de input — Distinción fundamental

El sistema tiene **dos mecanismos de entrada completamente distintos**. Cualquier cambio en el sistema debe respetar y preservar esta separación:

#### 🔵 TAREAS — Acción puntual y manual (`/tareas`)
Una tarea es una **instrucción única que el usuario lanza en el momento** para que un agente haga algo concreto ahora.
- Se ejecuta **una sola vez**.
- El usuario puede ver el resultado, aprobarlo o cancelarlo.
- Se persiste en la tabla `Task`. El resultado se guarda en `task.agent_results` y genera un log inmutable en `AuditLog`.

#### 🟢 AUTOMATIZACIONES — Acción repetitiva preestablecida (`/automatizaciones`)
Una automatización es una **regla persistente que el usuario define una sola vez** y que el sistema ejecuta automáticamente cada vez que se cumple una condición.
- Tipos de trigger:
  - **Basado en tiempo**: *"cada lunes"*, *"cada trimestre"*
  - **Basado en evento**: *"cuando se cree una factura > 5.000€"*
- Se persiste en `Workflow`. Cada ejecución crea un registro en `WorkflowExecution` y **puede generar `Task`s hijas** delegadas.

> **Regla de oro**: Una automatización puede generar tareas. Una tarea jamás crea automatizaciones.

---

## 🛡️ Principios fundamentales — NO negociables

1. **Los agentes pueden crear y modificar datos reales**: Tienen **acceso completo de escritura**. Pueden crear facturas, generar archivos físicos (PDFs) en disco y actualizar clientes. Nunca deben ser "solo de lectura" por defecto.
2. **Las automatizaciones se definen en lenguaje natural**: Las reglas de los workflows se almacenan como configuración JSON y se interpretan dinámicamente (modo reasoning) o pre-compiladas (modo deterministic). No son código Python hard-coded.
3. **Los workflows deben ser adaptativos**: Si un paso de razonamiento falla, el orquestador repite o replanifica pudiendo encadenar agentes inteligentemente (ej: *billing* genera factura → delega a *documents* guardar archivo → delega a *email* para enviarlo).
4. **ERP local independiente**: Los datos siempre se persisten localmente en la base de datos propia (`Invoices`, `Clients`, `Payroll`). Las integraciones de terceros (APIs de Bancos) son espejos opcionales u orígenes reactivos, nunca la fuente de verdad principal del ERP.
5. **Integridad Transaccional y Robustez (DDD)**: 
   - **Transacciones Atómicas**: Si una operación compleja falla a medias (ej. falla al generar el PDF de la factura), el motor hace *rollback* completo de los insert(s) en BD para evitar filas huérfanas.
   - **Máquinas de Estado Estrictas**: Entidades críticas bloquean transiciones ilegítimas.
   - **ExecutionContext Compartido**: Los agentes de un mismo workflow comparten una "memoria temporal" para que el paso 2 no le vuelva a preguntar al usuario por datos que el paso 1 ya resolvió en background.

---

## Base de datos

### Multi-tenancy

Todos los modelos tienen `tenant_id: UUID`. Los endpoints filtran siempre por `current_user.tenant_id`. No hay datos compartidos entre tenants.

### Modelos principales (28 tablas)

```
auth        → users, password_reset_tokens
tenant      → tenants, tenant_integrations, tenant_llm_config
billing     → invoices, invoice_lines, invoice_series, clients, products, quotes
hr          → employees, payrolls
crm         → opportunities, activities, events, reservations
accounting  → journal_entries, journal_lines, fixed_assets
inventory   → stock_items
orders      → purchase_orders, sales_orders
projects    → projects, tasks (proyectos), project_members
calendar    → calendar_events
tasks       → tasks (IA), audit_log, pending_approvals, domain_events
workflows   → workflows, workflow_executions
embeddings  → document_embeddings (pgvector)
```

### Migraciones

```bash
# Crear nueva migración
alembic revision --autogenerate -m "descripcion"

# Aplicar
alembic upgrade head

# Ver historial
alembic history
```

> **REGLA**: Siempre crear migración Alembic al añadir o modificar campos en modelos. Nunca modificar tablas directamente en producción.

---

## Integraciones OAuth

### Google (Gmail + Google Drive)

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
```

Un OAuth de Google habilita tanto Gmail como Drive. Scopes: `gmail.readonly`, `gmail.send`, `drive.file`, `drive.readonly`.

### Microsoft (Outlook + OneDrive)

```env
MICROSOFT_CLIENT_ID=...
MICROSOFT_CLIENT_SECRET=...
```

Un OAuth de Microsoft habilita Outlook y OneDrive. Scopes: `Mail.Read`, `Mail.Send`, `Files.ReadWrite`.

### Flujo OAuth

```
Frontend → abre popup → backend /oauth/{provider}/start → redirect a Google/Microsoft
→ callback /oauth/{provider}/callback → intercambia code por tokens
→ tokens cifrados con PBKDF2+Fernet en TenantIntegration
```

El estado OAuth usa un dict en memoria con TTL de 10 minutos (limpieza automática de estados expirados).

---

## Seguridad

### Variables de entorno críticas

```env
# Generar con: openssl rand -hex 32
SECRET_KEY=...

# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
TENANT_ENCRYPTION_KEY=...
```

> La aplicación **no arranca** si estas variables tienen los valores por defecto. Es intencional.

### Medidas implementadas

- **JWT**: HS256, expiración 60 min (access) + 30 días (refresh)
- **CORS**: restringido a métodos y headers específicos
- **Rate limiting**: aplicado en endpoints de auth
- **Upload validation**: extensiones permitidas + límite 50MB
- **Prompt injection**: `prompt_sanitizer.py` aplicado en agentes LLM
- **Security headers**: X-Content-Type-Options, X-Frame-Options, HSTS, CSP
- **DB indexes**: índices compuestos en `tenant_id + created_at` para queries frecuentes
- **Electron**: ejecución nativa sin contenedores
- **Cifrado de credenciales**: PBKDF2 (100k iteraciones) para tokens OAuth de tenants

---

## Estructura de directorios

```
atomatizacion-de-empresas/
├── backend/
│   ├── app/
│   │   ├── agents/               # Agentes especializados + orquestador LangGraph
│   │   │   ├── orchestrator/     # _core.py — núcleo del orquestador
│   │   │   ├── billing_agent.py
│   │   │   ├── hr_agent.py
│   │   │   └── ...
│   │   ├── api/v1/
│   │   │   ├── routes/           # Endpoints FastAPI (uno por dominio)
│   │   │   └── schemas/          # Pydantic schemas de request/response
│   │   ├── core/
│   │   │   ├── config.py         # Settings (pydantic-settings, lee .env)
│   │   │   └── llm_factory.py    # get_llm() y get_embedder() — único punto de entrada a LLMs
│   │   ├── db/
│   │   │   ├── models/           # SQLAlchemy models (un archivo por dominio)
│   │   │   └── migrations/       # Alembic migrations
│   │   ├── services/             # Lógica de negocio reutilizable
│   │   │   ├── task_runner.py    # TaskRunner (asyncio, reemplaza Celery)
│   │   │   ├── task_dispatch.py  # dispatch_task() (reemplaza .delay())
│   │   │   ├── scheduler.py     # APScheduler (reemplaza Celery Beat)
│   │   │   ├── idempotency.py   # Idempotencia en memoria con TTL
│   │   │   ├── llm_cache.py     # Cache LLM en memoria (max 1000)
│   │   │   └── exec_log_store.py # Logs de ejecución en memoria
│   │   └── workers/
│   │       ├── tasks_orchestrator.py  # Tareas async del orquestador
│   │       ├── tasks_node_engine.py   # Tareas async del node engine
│   │       └── tasks_scheduler.py     # Tareas async del scheduler
│   ├── tests/                    # pytest — 7 archivos de test
│   └── pyproject.toml
├── frontend/
│   └── src/
│       ├── app/(dashboard)/      # Páginas Next.js (una carpeta por módulo)
│       ├── components/           # Componentes React reutilizables
│       │   └── Workflows/        # Editor visual de automatizaciones
│       ├── lib/
│       │   ├── api.ts            # Cliente HTTP centralizado — SIEMPRE usar esto
│       │   └── logger.ts         # logError() — nunca console.error directo
│       └── stores/               # Zustand stores
├── desktop/                      # App Electron (PostgreSQL portable + Python embebido)
├── levantar.bat                  # Script de arranque para desarrollo
└── .env                          # Variables de entorno
```

---

## Arranque rápido

### Requisitos

- Python 3.11+
- Node.js 18+
- PostgreSQL 15 (o usar el portable incluido en `desktop/`)
- Git

### Variables de entorno mínimas

Copia `.env.example` a `.env` y configura al menos:

```env
SECRET_KEY=<openssl rand -hex 32>
TENANT_ENCRYPTION_KEY=<fernet key>
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Arrancar (desarrollo)

```bat
levantar.bat
```

### Arrancar (producción — Electron)

Ejecutar la app Electron desde `desktop/`. Arranca automáticamente PostgreSQL portable, el backend (uvicorn) y el frontend.

Accesos:
- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8080/docs
- **Usuario demo**: `demo@automatizapyme.com` / `Demo1234!`

### Datos de demo

```bash
python smoke_demo.py              # Crea datos de demostración
python smoke_tasks_workflows.py   # Lanza tareas IA de ejemplo

para aplicar cambios sin reinstalar el exe 



cd desktop && npm run sync

```

---

## Convenciones de desarrollo

### Backend

- **Endpoints**: `backend/app/api/v1/routes/<dominio>.py` — un archivo por módulo
- **Modelos BD**: `backend/app/db/models/<dominio>.py` — siempre crear migración al cambiar
- **LLM**: llamar siempre via `get_
llm()` en `llm_factory.py`. Nunca instanciar `ChatOpenAI` etc. directamente
- **Embeddings**: llamar siempre via `get_embedder()`. Nunca instanciar `HuggingFaceEmbeddings` directamente
- **Agentes**: devuelven siempre un dict con `{"success": bool, "output": ..., "summary": str, "error": str|None}`
- **Tareas async**: despachar via `task_dispatch.dispatch_task()`, nunca llamar directamente

### Frontend

- **API calls**: siempre via `frontend/src/lib/api.ts`. Nunca `fetch()` directo ni `<a href>` a URLs del backend
- **Errores**: usar `logError(contexto, error)` de `logger.ts`, nunca `console.error`
- **Descargas de archivos**: siempre `fetch()` con JWT en header `Authorization` (el backend requiere auth)
- **Nuevas páginas**: añadir a `(dashboard)/` con `"use client"` si tiene estado

### Reglas generales

- Multi-tenancy: todos los queries de BD filtran por `tenant_id`
- Nunca hardcodear IDs, URLs de backend, ni claves API en código fuente
- El orquestador (`orchestrator/_core.py`) es el único punto de entrada para agentes desde el task runner
- Las automatizaciones no pueden tener dos ejecuciones simultáneas (HTTP 409)

---

## Tests

```bash
# Ejecutar suite completa
pytest tests/ -v

# Test específico
pytest tests/test_api_auth.py -v

# Con cobertura
pytest tests/ --cov=app --cov-report=term-missing
```

Archivos de test: `test_api_auth`, `test_api_health`, `test_api_tasks_agents`, `test_api_tenant`, `test_encryption`, `test_prompt_sanitizer`, `test_security`.

---

## Módulos del frontend

| Ruta | Descripción |
|------|-------------|
| `/` | Dashboard principal con KPIs |
| `/ventas/facturas` | Facturación — CRUD + cambio de estado + PDF |
| `/ventas/presupuestos` | Presupuestos y conversión a factura |
| `/ventas/pedidos` | Pedidos de venta |
| `/ventas/recurrentes` | Facturas recurrentes |
| `/clientes` | CRM básico de clientes |
| `/crm/*` | Pipeline de ventas, calendario, reservas, reuniones |
| `/rrhh/empleados` | Gestión de empleados |
| `/rrhh/nominas` | Nóminas con desglose SS e IRPF |
| `/rrhh/documentos` | Documentos laborales generados por IA (contratos, cartas) |
| `/rrhh/reclutamiento` | Posiciones abiertas, subida de CVs, análisis IA |
| `/rrhh/analisis-cv` | Análisis detallado de CVs con scoring |
| `/contabilidad/*` | Libro diario, P&G, activos fijos, balance |
| `/banca` | Movimientos bancarios y conciliación |
| `/documentos` | Repositorio de documentos con búsqueda semántica |
| `/albaranes` | Albaranes de entrega — CRUD + PDF |
| `/compras/*` | Facturas de compra, pedidos, proveedores |
| `/tesoreria/*` | Cashflow, pagos y cobros, remesas |
| `/mi-equipo` | Empleados IA personalizables — crear, instruir, monitorizar |
| `/sandbox` | Generador de interfaces UI desde lenguaje natural |
| `/automatizaciones` | Editor visual de workflows + historial |
| `/informes` | Informes generados por IA |
| `/integraciones` | OAuth Google/Microsoft, PSD2 |
| `/configuracion/api-keys` | Gestión de API keys y proveedor LLM por tenant |

---

## Problemas conocidos y limitaciones

- El modelo BAAI/bge-m3 tarda ~30s en cargar la primera vez que se sube un documento (descarga ~600MB)
- Las automatizaciones con trigger `*/2 * * * *` o más frecuentes pueden saturar el proceso si la tarea es larga — usar con precaución
- El proveedor Groq tiene límite de rate agresivo en el tier gratuito — en producción usar Anthropic o Gemini
- Las integraciones OAuth (Gmail, Outlook) requieren configurar redirect URIs en Google Cloud Console / Azure AD respectivamente
- Los servicios en memoria (cache LLM, idempotencia, exec logs) se pierden al reiniciar la aplicación — esto es aceptable para un ERP local single-user
- `croniter` debe estar instalado para que funcionen los triggers de tiempo — incluido en `pyproject.toml`
