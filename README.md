# AutomatizaPyme — ERP SaaS Multiagente para PYMEs

Plataforma de automatización administrativa para PYMEs españolas. El usuario gestiona facturación, RRHH, contabilidad, banca y CRM mediante **lenguaje natural**. Los agentes IA ejecutan las acciones y escriben directamente en la base de datos.

---

## CONTEXTO DEL PROYECTO — Leer antes de cualquier cambio

> Esta sección es de lectura obligatoria para cualquier modelo de IA o desarrollador que trabaje en este repositorio. Resume la visión central, los principios de diseño y el comportamiento esperado del sistema.

### Visión central

AutomatizaPyme es un **ERP inteligente local-first**. Cada cliente instala la aplicación en su propia máquina con Docker. Los datos nunca salen de su entorno local. La app requiere conexión a internet únicamente para validar la licencia activa contra un servidor central (VPS) y para llamar a las APIs de LLM configuradas.

```
┌─────────────────────────────────────┐        ┌─────────────────────────┐
│         CLIENTE (local)             │        │    VPS LICENCIAS        │
│                                     │        │                         │
│  Docker (API + DB + Redis + Worker) │◄──────►│  Servidor de licencias  │
│  Next.js Frontend                   │  HTTPS │  - Valida clave mensual │
│  PostgreSQL (datos del cliente)     │        │  - Gestiona pagos       │
└─────────────────────────────────────┘        └─────────────────────────┘
```

---

## Stack técnico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend API | FastAPI (Python) | 3.11 / 0.115 |
| Agentes IA | LangGraph | 0.2+ |
| Cola de tareas | Celery + Redis | 5.4 / 7 |
| Base de datos | PostgreSQL + pgvector | 15 |
| Frontend | Next.js + React + TypeScript | 14 / 18 |
| Estado UI | Zustand | 4 |
| Estilos | Tailwind CSS | 3 |
| Contenedores | Docker Compose | Windows |

---

## Proveedores LLM

### Proveedor por defecto: Anthropic (Claude)

```env
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-6        # claude-sonnet-4-6 | claude-opus-4-6
```

**Recomendación**: Anthropic Claude Sonnet 4.6 es el modelo principal. Es el más equilibrado en precio/calidad para tareas de ERP. Claude Opus 4.6 para tareas que requieren máxima precisión.

### Proveedor alternativo recomendado: Gemini

```env
DEFAULT_LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash-preview-04-17
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

> **Ollama ha sido eliminado.** Ya no se usa ni se soporta ningún modelo local mediante Ollama. El perfil `--profile llm` del docker-compose está obsoleto.

---

## Sistema de Embeddings y RAG

### Motor de búsqueda semántica

El sistema RAG usa **pgvector** (extensión de PostgreSQL) para almacenar y buscar vectores de embeddings. Los documentos subidos se fragmentan en chunks y se vectorizan automáticamente al subirse.

### Proveedor de embeddings: HuggingFace (local, por defecto)

```env
EMBEDDINGS_PROVIDER=local
EMBEDDINGS_LOCAL_MODEL=BAAI/bge-m3
```

El modelo `BAAI/bge-m3` de HuggingFace se descarga automáticamente la primera vez. Es multilingüe (español nativo), estado del arte para búsqueda semántica, y funciona completamente offline sin coste por llamada. Se ejecuta dentro del contenedor Docker del worker.

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

---

## Arquitectura de agentes (3 capas)

```
Usuario (lenguaje natural)
        │
        ▼
┌───────────────────┐
│   ORQUESTADOR     │  LangGraph — clasifica dominio, crea plan, coordina agentes
│   _core.py        │  Entrada: user_intent + tenant_context
└────────┬──────────┘
         │
    ┌────▼─────┐
    │  PLAN    │  Lista de subtareas → agentes especializados
    └────┬─────┘
         │
┌────────▼──────────────────────────────────┐
│  AGENTES ESPECIALIZADOS                   │
│  billing · hr · crm · banking             │
│  documents · compliance · excel           │
│  email · rag · workflow                   │
└───────────────────────────────────────────┘
         │
    Escritura directa en PostgreSQL
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

### Ejecución de automatizaciones

Las automatizaciones tienen dos modos:
- **Determinista**: sigue un grafo de nodos fijo definido visualmente en el editor
- **Razonamiento**: el LLM crea el plan dinámicamente según la instrucción

Cada automatización puede dispararse por:
- **Tiempo** (cron): `*/2 * * * *` — evaluado por `check_scheduled_workflows` cada minuto via Celery Beat
- **Evento**: `invoice_created`, `invoice_paid`, `client_added`, etc.

**Prevención de duplicados**: si ya hay una ejecución `running` o `pending` para un workflow, el sistema bloquea nuevas ejecuciones (HTTP 409 en API manual, skip silencioso en Beat).

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
docker-compose exec api alembic revision --autogenerate -m "descripcion"

# Aplicar
docker-compose exec api alembic upgrade head

# Ver historial
docker-compose exec api alembic history
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

El estado OAuth usa Redis con TTL de 10 minutos (no dict en memoria).

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
- **Docker**: usuario non-root en contenedores; healthchecks en api y worker
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
│   │   └── workers/
│   │       └── celery_app.py     # Tareas Celery + Beat scheduler
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
├── docker-compose.yml
├── levantar.bat                  # Script único: arrancar, parar, reconstruir, logs
└── .env                          # Variables de entorno (raíz, para Docker)
```

---

## Arranque rápido

### Requisitos

- Docker Desktop (Windows) con WSL2 activado
- Node.js 18+ (para el frontend fuera de Docker)
- Git

### Variables de entorno mínimas

Copia `.env.example` a `.env` y configura al menos:

```env
SECRET_KEY=<openssl rand -hex 32>
TENANT_ENCRYPTION_KEY=<fernet key>
DEFAULT_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Arrancar

```bat
levantar.bat
```

El script muestra un menú con opciones:
- **[1] Arrancar** — `docker-compose up -d` + inicia Next.js
- **[2] Parar** — para todos los servicios
- **[3] Reconstruir** — rebuild completo de imágenes Docker
- **[4] Ver logs** — logs en tiempo real del backend
- **[5] Restaurar BD** — aplica migraciones Alembic

Accesos:
- **Frontend**: http://localhost:3000
- **API docs**: http://localhost:8080/docs
- **Usuario demo**: `demo@automatizapyme.com` / `Demo1234!`

### Datos de demo

```bash
docker-compose exec api python smoke_demo.py              # Crea datos de demostración
docker-compose exec api python smoke_tasks_workflows.py   # Lanza tareas IA de ejemplo
```

---

## Convenciones de desarrollo

### Backend

- **Endpoints**: `backend/app/api/v1/routes/<dominio>.py` — un archivo por módulo
- **Modelos BD**: `backend/app/db/models/<dominio>.py` — siempre crear migración al cambiar
- **LLM**: llamar siempre via `get_llm()` en `llm_factory.py`. Nunca instanciar `ChatOpenAI` etc. directamente
- **Embeddings**: llamar siempre via `get_embedder()`. Nunca instanciar `HuggingFaceEmbeddings` directamente
- **Agentes**: devuelven siempre un dict con `{"success": bool, "output": ..., "summary": str, "error": str|None}`
- **Tareas Celery**: siempre con `time_limit=600, soft_time_limit=540`

### Frontend

- **API calls**: siempre via `frontend/src/lib/api.ts`. Nunca `fetch()` directo ni `<a href>` a URLs del backend
- **Errores**: usar `logError(contexto, error)` de `logger.ts`, nunca `console.error`
- **Descargas de archivos**: siempre `fetch()` con JWT en header `Authorization` (el backend requiere auth)
- **Nuevas páginas**: añadir a `(dashboard)/` con `"use client"` si tiene estado

### Reglas generales

- Multi-tenancy: todos los queries de BD filtran por `tenant_id`
- Nunca hardcodear IDs, URLs de backend, ni claves API en código fuente
- El orquestador (`orchestrator/_core.py`) es el único punto de entrada para agentes desde Celery
- Las automatizaciones no pueden tener dos ejecuciones simultáneas (HTTP 409)

---

## Tests

```bash
# Ejecutar suite completa
docker-compose exec api pytest tests/ -v

# Test específico
docker-compose exec api pytest tests/test_api_auth.py -v

# Con cobertura
docker-compose exec api pytest tests/ --cov=app --cov-report=term-missing
```

Archivos de test: `test_api_auth`, `test_api_health`, `test_api_tasks_agents`, `test_api_tenant`, `test_encryption`, `test_prompt_sanitizer`, `test_security`.

---

## Módulos del frontend

| Ruta | Descripción |
|------|-------------|
| `/` | Dashboard principal con KPIs |
| `/ventas/facturas` | Facturación — CRUD + cambio de estado + PDF |
| `/ventas/presupuestos` | Presupuestos y conversión a factura |
| `/clientes` | CRM básico de clientes |
| `/crm/*` | Pipeline de ventas, calendario, reservas, reuniones |
| `/rrhh/empleados` | Gestión de empleados |
| `/rrhh/nominas` | Nóminas con desglose SS e IRPF |
| `/contabilidad/*` | Libro diario, P&G, activos fijos |
| `/banca` | Movimientos bancarios y conciliación |
| `/documentos` | Repositorio de documentos con búsqueda semántica |
| `/automatizaciones` | Editor visual de workflows + historial |
| `/informes` | Informes generados por IA |
| `/integraciones` | OAuth Google/Microsoft, PSD2, Holded |
| `/configuracion/api-keys` | Gestión de API keys y proveedor LLM por tenant |

---

## Problemas conocidos y limitaciones

- El modelo BAAI/bge-m3 tarda ~30s en cargar la primera vez que se sube un documento (descarga ~600MB)
- Las automatizaciones con trigger `*/2 * * * *` o más frecuentes pueden saturar el worker si la tarea es larga — usar con precaución
- El proveedor Groq tiene límite de rate agresivo en el tier gratuito — en producción usar Anthropic o Gemini
- Las integraciones OAuth (Gmail, Outlook) requieren configurar redirect URIs en Google Cloud Console / Azure AD respectivamente
- `croniter` debe estar instalado en el contenedor worker para que funcionen los triggers de tiempo — incluido en `pyproject.toml`
