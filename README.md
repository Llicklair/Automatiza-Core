# AutomatizaPyme — Plataforma SaaS Multiagente

Plataforma de automatización administrativa para PYMEs basada en arquitectura multiagente con IA.

---

## 🧠 CONTEXTO DEL PROYECTO — Leer antes de cualquier cambio

> **Esta sección es de lectura obligatoria para cualquier modelo de IA o desarrollador que trabaje en este repositorio.**
> Resume la visión central, los principios de diseño y el comportamiento esperado del sistema.

### Visión central

AutomatizaPyme es un **ERP inteligente** que permite a una PYME española gestionar su administración completa (facturación, documentos, RRHH, contabilidad, banca) a través de **instrucciones en lenguaje natural**. El usuario no rellena formularios: le habla al sistema y los agentes ejecutan, crean y modifican la información por él.

---

## 📦 Modelo de distribución — Cómo funciona el negocio

### Arquitectura "Local-first con licencia online"

AutomatizaPyme **no es un SaaS en la nube tradicional**. Cada cliente descarga e instala la aplicación en su propia máquina. Los datos nunca salen de su entorno local. Sin embargo, la aplicación requiere conexión a internet para funcionar, ya que valida su suscripción activa contra un servidor de licencias centralizado (VPS).

```
┌─────────────────────────────────────┐        ┌─────────────────────────┐
│         CLIENTE (local)             │        │    VPS LICENCIAS        │
│                                     │        │                         │
│  Docker (API + DB + Redis + Worker) │◄──────►│  Servidor de licencias  │
│  Next.js Frontend                   │  HTTPS │  - Valida clave mensual │
│  PostgreSQL (datos del cliente)     │        │  - Gestiona pagos       │
│                                     │        │  - Revoca accesos       │
│  API keys LLM: gestionadas aquí     │        │  - Dashboard de admin   │
└─────────────────────────────────────┘        └─────────────────────────┘
         ↑ datos nunca salen                            ↑ sin datos de clientes
```

### Por qué este modelo

| Ventaja | Explicación |
|---|---|
| **Privacidad de datos** | La BD del cliente está en su máquina. Cero exposición de datos contables, nóminas o clientes a terceros. Argumento de venta muy fuerte frente a SaaS cloud |
| **Sin riesgo de brecha masiva** | Un ataque al VPS no compromete datos de ningún cliente — el servidor solo sabe si la licencia es válida, no tiene acceso a los datos |
| **Costes de infraestructura bajos** | El VPS solo sirve validaciones y gestión de suscripciones, no carga de trabajo ERP |
| **Las claves API son del propio cliente** | Cada usuario configura sus propias API keys (Gemini, Groq, etc.) en su `.env` local. AutomatizaPyme no gestiona ni tiene acceso a ninguna de ellas. Si una key se filtra, es un problema exclusivo de esa instalación, no afecta a otros clientes ni al proveedor |
| **GDPR simplificado** | El cliente es el único responsable de sus datos. No hay transferencia internacional ni procesador en la nube |

### Flujo de suscripción

```
1. Cliente compra suscripción → recibe clave mensual única (ej: PYME-XXXX-XXXX-XXXX)
2. Introduce la clave en la primera ejecución de levantar.bat
3. Al arrancar, la app contacta el VPS → valida la clave → permite uso
4. Cada N horas (configurable, ej: 24h) la app revalida en background
5. Si la suscripción caduca o se revoca → la app muestra aviso y bloquea
```

### Modelo de responsabilidad sobre las claves API

Cada cliente configura sus propias claves de proveedor LLM (Gemini, Groq, OpenAI, etc.) en el archivo `.env` de su instalación local. AutomatizaPyme no centraliza, no gestiona ni tiene visibilidad sobre esas claves en ningún momento.

Esto tiene implicaciones claras:

| Situación | Responsable |
|---|---|
| Un usuario configura mal su `.env` | El usuario |
| Una key del usuario se filtra por malware en su máquina | El usuario |
| Un usuario comparte su `.env` con alguien | El usuario |
| Una key del usuario caduca o se agota su cuota | El usuario |
| Problemas de seguridad en el código de AutomatizaPyme | AutomatizaPyme |

> **Analogía**: es el mismo modelo que cualquier aplicación de escritorio que usa cuentas de terceros (un cliente de email no es responsable si te roban la contraseña de Gmail desde tu ordenador). AutomatizaPyme provee la herramienta; la seguridad del entorno donde se ejecuta es responsabilidad del cliente.

La **única amenaza real** que compete al código de la aplicación en este modelo es que **software malicioso en la máquina del cliente** pueda leer el `.env` o interceptar las llamadas de la app. Por eso el enfoque de seguridad de este proyecto se centra en:

1. **Integridad del código distribuido**: el paquete que descarga el cliente no ha sido manipulado (firma digital del bundle)
2. **Comunicaciones cifradas**: todas las llamadas al VPS de licencias y a los proveedores LLM viajan por HTTPS/TLS
3. **Sin superficie de ataque remota**: la app no expone puertos al exterior salvo los estrictamente necesarios para uso local
4. **Protección de la licencia**: el mecanismo de validación de clave está ofuscado para dificultar bypasses

### Consideraciones técnicas importantes

#### Protección del código ("wrapeo")
El código se empaqueta con herramientas de ofuscación para dificultar la ingeniería inversa del mecanismo de licencias:
- **Backend Python**: compilado con [Nuitka](https://nuitka.net/) o empaquetado con PyInstaller + ofuscación
- **Frontend Next.js**: build de producción con minificación y ofuscación de bundles
- **Lógica de validación de licencia**: no en texto plano, cifrada en el bundle

> **Límite real de la ofuscación**: protege contra el usuario casual que quiere saltarse el pago. No protege contra un atacante dedicado con tiempo y herramientas de ingeniería inversa. Es una barrera de coste/esfuerzo, no un muro infranqueable. El objetivo no es proteger las keys del LLM (son del propio usuario) sino proteger el mecanismo de licencias.

#### Punto único de fallo

Si el VPS de licencias cae, **ningún cliente puede iniciar sesión** (los ya iniciados pueden seguir hasta el próximo ciclo de revalidación). Mitigaciones:
- Alta disponibilidad del VPS (mínimo 2 instancias con balanceador)
- Periodo de gracia configurable (ej: 48h sin validar antes de bloquear)
- Cache local del último token de licencia válido

#### Revocación de licencias

El servidor debe ser capaz de revocar una clave en tiempo real (impago, fraude, fin de suscripción). La app local consulta el estado cada 24h y bloquea si la clave ya no es válida.

#### Huella de hardware (opcional)

Para evitar que una clave se comparta entre múltiples instalaciones, se puede incluir fingerprinting de hardware (MAC address, UUID de disco) en la validación. La clave solo es válida para la máquina donde se activó.

---

### ⚡ Los dos tipos de input — Distinción fundamental

El sistema tiene **dos mecanismos de entrada completamente distintos**. Cualquier cambio en el sistema debe respetar y preservar esta separación:

#### 🔵 TAREAS — Acción puntual y manual (`/tareas`)
Una tarea es una **instrucción única que el usuario lanza en el momento** para que un agente haga algo concreto ahora.

- El usuario la crea manualmente desde la UI o vía API.
- Se ejecuta **una sola vez**.
- El usuario puede ver el resultado, aprobarlo o cancelarlo.
- Ejemplos:
  - *"Crea una factura a ACME S.L. por 1.500€ de consultoría"*
  - *"Analiza el contrato que acabo de subir"*
  - *"¿Cuáles son mis obligaciones fiscales este trimestre?"*
- Se persiste en la tabla `Task` con estados: `pending → executing → done / failed`.
- El resultado queda en `task.agent_results` y genera un log en `AuditLog`.

#### 🟢 AUTOMATIZACIONES — Acción repetitiva preestablecida (`/automatizaciones`)
Una automatización es una **regla persistente que el usuario define una sola vez** y que el sistema ejecuta automáticamente cada vez que se cumple una condición.

- El usuario la configura en **lenguaje natural** (ej: *"el día 1 de cada mes, genera el informe bancario"*).
- Se ejecuta **de forma recurrente o reactiva** sin intervención del usuario.
- El sistema interpreta el lenguaje natural y lo convierte en `trigger_config` + `action_config` (JSONB en tabla `Workflow`).
- Tipos de trigger:
  - **Basado en tiempo** (`schedule_based`): *"cada lunes"*, *"el día 5 del mes"*, *"cada trimestre"*
  - **Basado en evento** (`event_based`): *"cuando se cree una factura > 5.000€"*, *"cuando un cliente lleve 30 días sin pagar"*
  - **Manual** (`manual`): botón en la UI que lanza la automatización bajo demanda pero sin escribir la instrucción cada vez
- Cada ejecución crea un registro en `WorkflowExecution` y puede generar `Task`s hijas si la acción lo requiere.
- Los workflows son **adaptativos**: si una ejecución falla, el sistema puede reintentar con parámetros ajustados o notificar al usuario.

#### Diferencia clave en una tabla

| | Tarea | Automatización |
|---|---|---|
| **¿Quién la lanza?** | El usuario, manualmente | El sistema, automáticamente |
| **¿Cuántas veces?** | Una vez | Repetidamente (según regla) |
| **¿Cómo se define?** | Instrucción en el momento | Regla preestablecida en lenguaje natural |
| **Modelo en BD** | `Task` | `Workflow` + `WorkflowExecution` |
| **Caso de uso** | *"Hazlo ahora"* | *"Hazlo siempre que..."* |

> **Regla de oro**: Una automatización puede generar tareas. Una tarea no crea automatizaciones.

---

### Principios fundamentales — NO negociables

#### 1. Los agentes pueden crear y modificar datos reales
Los agentes de IA tienen **acceso completo de escritura** al sistema. Esto incluye:
- **Crear** facturas, clientes, presupuestos, nóminas, documentos, entradas contables, eventos, reservas.
- **Modificar** registros existentes (actualizar estado de factura, corregir datos de cliente, editar contenido de documento).
- **Generar archivos** en disco (PDFs de facturas, informes bancarios, documentos de nóminas) y registrarlos en `TenantDocument`.
- **Eliminar o cancelar** entidades cuando el usuario lo ordene explícitamente.

Ningún agente debe ser solo de lectura por defecto. La capacidad de escritura es el núcleo del valor del producto.

#### 2. Las automatizaciones se definen en lenguaje natural
El sistema de automatizaciones (`Workflow` / `WorkflowExecution`) permite al usuario crear reglas del tipo:
- *"Cada vez que se cree una factura superior a 5.000€, notifícame por email y crea una tarea de revisión."*
- *"El día 1 de cada mes, genera el informe bancario y archívalo en Documentos."*
- *"Si un cliente tiene facturas vencidas hace más de 30 días, envíale un recordatorio."*

Estas reglas NO son código hard-coded. Se almacenan en la tabla `workflows` como configuración JSONB (`trigger_config`, `action_config`) y se ejecutan interpretadas por el orquestador o directamente por agentes. El lenguaje natural del usuario se convierte en parámetros de workflow dinámicamente.

#### 3. Los workflows deben ser adaptativos
Los workflows **no son estáticos**. El sistema debe ser capaz de:
- **Re-planificarse** si una subtarea falla (el orquestador reintenta con parámetros distintos).
- **Aprender del contexto**: si el usuario modifica manualmente un resultado de un agente, esa corrección puede retroalimentar el comportamiento futuro.
- **Encadenar agentes dinámicamente**: una tarea de billing puede disparar automáticamente una tarea de documentos (guardar PDF) y una de banking (registrar el cobro esperado), sin que el usuario lo indique explícitamente.
- **Pausar y esperar aprobación humana** cuando detecten operaciones de riesgo, retomando la ejecución tras la decisión del usuario sin perder el estado.

#### 4. ERP local independiente — siempre
Los datos **siempre se persisten localmente** en PostgreSQL (modelos propios: `Invoice`, `Client`, `InvoiceLine`, `Payroll`, `TenantDocument`, etc.), independientemente de si hay integraciones externas activas (Holded, Gmail, PSD2). Las integraciones son espejos opcionales, no la fuente de verdad.

#### 5. Multi-tenant y seguro
Cada empresa (tenant) tiene sus datos completamente aislados. Las credenciales de integraciones externas se cifran con Fernet (AES-256) por tenant. Un agente nunca debe acceder a datos de otro tenant.

#### 6. Integridad Transaccional y Robustez (DDD)
El sistema aplica principios de Diseño Orientado al Dominio para garantizar que los datos nunca queden en un estado inconsistente:
- **Transacciones Atómicas**: Las operaciones complejas de los agentes (ej: Billing) se ejecutan en un bloque atómico. Si la generación de un PDF falla, la factura no se guarda en BD para evitar huérfanos.
- **Máquinas de Estado**: Las entidades críticas (`Invoice`, `Payroll`, `WorkflowExecution`, `Task`) tienen transiciones de estado validadas. No se pueden saltar estados o realizar acciones ilegales (ej: pagar una factura cancelada).
- **Idempotencia con Redis**: Todas las tareas críticas de Celery están protegidas contra duplicaciones. Si una tarea se reintenta por un fallo de red, el sistema detecta que ya se completó y evita realizar la acción de nuevo.
- **ExecutionContext**: Los agentes comparten una memoria de trabajo enriquecida. Si el Agente A crea una factura, el Agente B (Email) recibe el contexto completo del paso anterior para saber qué adjuntar sin preguntar.

### Stack tecnológico clave

| Capa | Tecnología |
|------|------------|
| Backend API | FastAPI (Python 3.11+) + Uvicorn |
| Orquestador IA | LangGraph (grafo de estados: Classify → Plan → Validate → Dispatch → Result) |
| LLM | Multi-proveedor: Ollama local (llama3.2), OpenAI, Anthropic, Gemini, Groq, OpenRouter |
| Workers asíncronos | Celery + Redis |
| Base de datos | PostgreSQL 15 (pgvector) + SQLAlchemy 2.0 async (asyncpg) |
| Migraciones | Alembic |
| Frontend | Next.js 14 + React 18 + TypeScript + Tailwind CSS |
| UI Components | Radix UI + Zustand (estado global) + Recharts (gráficos) + ReactFlow (flujos) |
| PDF | Servicio interno `pdf_service.py` (reportlab/weasyprint) |
| Datos tabulares | Pandas + OpenPyXL |
| Auth | JWT con refresh token, roles por tenant (admin, user, viewer) |
| Cifrado | Fernet (AES-256) para credenciales de integraciones por tenant |
| CI/CD | GitHub Actions (lint, test, build, Docker push a GHCR) |
| Contenedores | Docker + docker-compose (4 servicios por defecto: api, worker, db, redis; ollama opcional con `--profile llm`) |

### Flujo de una tarea típica

```
Usuario (lenguaje natural)
    → POST /api/v1/tasks  {domain, user_intent}
    → Orquestador LangGraph:
        1. classify_node   → detecta dominio (billing/documents/hr/...)
        2. plan_node       → genera lista de subtareas
        3. validate_node   → validación determinista pre-ejecución
        4. dispatch_node   → invoca el agente especializado
        5. Agente:
           - Llama al LLM para extraer/generar datos
           - Escribe en BD (Invoice, Client, TenantDocument, etc.)
           - Genera archivos en disco si aplica
           - Sincroniza con integraciones externas si están activas
        6. Resultado → guardado en task.agent_results (JSONB)
           + log de auditoría inmutable en AuditLog
```

### Convenciones de código a respetar

- Los **endpoints de la API** viven en `backend/app/api/v1/routes/`.
- Los **agentes** viven en `backend/app/agents/` y devuelven un `Result` tipado (dataclass/pydantic).
- Los **modelos de BD** viven en `backend/app/db/models/models.py`. Al añadir campos, crear siempre la migración Alembic correspondiente.
- El **orquestador** (`backend/app/agents/orchestrator.py`) es el único punto de entrada para lanzar agentes. No llamar a agentes directamente desde endpoints de API salvo casos justificados.
- El **frontend** usa `frontend/src/lib/api.ts` como cliente centralizado de la API. Nunca hacer `fetch()` directo a URLs hardcodeadas en componentes; usar siempre `api.*` o la constante `NEXT_PUBLIC_API_URL`.
- Las **descargas de archivos** del frontend deben usar `fetch()` con el token JWT en la cabecera `Authorization`, nunca un `<a href>` directo a la URL del backend.

---

## Arquitectura de tres capas

```
┌──────────────────────────────────────────────────────────────────────┐
│                      ORQUESTADOR (capa superior)                      │
│                                                                        │
│  El usuario configura reglas en lenguaje natural → el sistema las     │
│  convierte en Workflows persistentes. Una vez configurado, se ejecuta │
│  automáticamente. El usuario puede reconfigurar en cualquier momento. │
│                                                                        │
│  Funciones:                                                            │
│  • Configurar reglas en lenguaje natural ("hazme la nómina de este    │
│    cliente en Excel todos los días a las 14:00")                       │
│  • Reconfigurar workflows: añadir pasos, eliminar tareas, cambiar     │
│    horarios sin recrear el flujo desde cero                            │
│  • Trigger por TIEMPO: diario, semanal, mensual, cada X horas...      │
│  • Trigger por EVENTO: "cada vez que entre un archivo en la BD,       │
│    rellena automáticamente cliente, proyectos y facturas"              │
│  • Trigger CONTINUO/PERMANENTE: regla siempre activa sin evento ni    │
│    horario. Ej: "todos los Excels se rellenan siempre de esta forma"  │
│    → el sistema aplica la norma de forma ininterrumpida               │
│  • Ejecutar múltiples workflows en paralelo por tenant                 │
│  • Reintentar ejecuciones fallidas con parámetros ajustados           │
│  • Pausar y esperar aprobación humana en operaciones de riesgo        │
│                                                                        │
│  Modelo BD: Workflow + WorkflowExecution                              │
│  Motor: Celery Beat + Redis + LangGraph                               │
└───────────────────────────┬──────────────────────────────────────────┘
                             │ puede generar
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    COORDINADOR GENERAL (capa media)                   │
│                                                                        │
│  El usuario lanza UNA instrucción compleja puntual → recibe UN        │
│  resultado final. Se ejecuta una sola vez. No crea reglas.            │
│                                                                        │
│  Funciones:                                                            │
│  • Descomponer la tarea compleja en subtareas secuenciales            │
│  • Asignar cada subtarea al agente especializado correcto             │
│  • Pasar el contexto y resultado de cada paso al siguiente            │
│  • Consolidar el output final (informe, PDF, email enviado...)        │
│                                                                        │
│  Ejemplo puntual: «Rellena las nóminas con estos modelos para        │
│  presentar el IRPF» → se ejecuta una vez y finaliza                   │
│                                                                        │
│  Modelo BD: Task (domain = 'coordinator')                             │
│  Motor: LangGraph (Classify → Plan → Validate → Dispatch)            │
└───────────────────────────┬──────────────────────────────────────────┘
                             │ delega en
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  AGENTES ESPECIALIZADOS (capa base)                   │
│                                                                        │
│  Cada agente es experto en un único dominio.                          │
│  Reciben una instrucción concreta y devuelven un resultado tipado.    │
│                                                                        │
│  billing │ documents │ compliance │ hr │ banking                      │
│  crm     │ excel     │ email      │ rag                               │
│                                                                        │
│  Motor: LangGraph por agente + LLM (Ollama / OpenAI / Anthropic)     │
└──────────────────────────────────────────────────────────────────────┘
```

---

```
/
├── backend/             # API FastAPI + Orquestador LangGraph + Workers Celery
│   ├── app/
│   │   ├── agents/      # Agentes IA especializados (billing, hr, crm, rag, etc.)
│   │   ├── api/v1/      # Endpoints REST (routes/)
│   │   ├── core/        # Configuración (config.py)
│   │   ├── db/          # Modelos SQLAlchemy + migraciones Alembic
│   │   ├── integrations/# Conectores externos (Holded, PSD2, Azure OCR, BOE)
│   │   ├── middleware/  # Rate limiting
│   │   ├── schemas/     # Schemas Pydantic
│   │   ├── services/    # Lógica de negocio (17 servicios)
│   │   ├── skills/      # Sistema de skills extensible
│   │   └── workers/     # Celery tasks y jobs programados
│   └── Dockerfile
├── frontend/            # Dashboard Next.js 14
│   └── src/
│       ├── app/         # Páginas (App Router, 44+ páginas)
│       ├── components/  # Componentes React reutilizables
│       ├── lib/         # API client centralizado + utilidades
│       └── store/       # Zustand stores
├── scripts/             # Utilidades (generación de contratos, tests)
├── infra/               # Configuración de infraestructura (PostgreSQL init)
├── .github/workflows/   # CI/CD (GitHub Actions)
├── levantar.bat         # Script de arranque (Windows)
├── parar.bat            # Script de parada (Windows)
├── .env                 # Variables de entorno para Docker Compose (API keys, DB, LLM provider)
└── docker-compose.yml   # 4 servicios: api, worker, db, redis (ollama con --profile llm)
```

---

## Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en ejecución
- [Python 3.11+](https://www.python.org/downloads/) (para desarrollo local sin Docker)
- [Node.js 18+](https://nodejs.org/) (para el frontend)
- [Poetry](https://python-poetry.org/docs/#installation) (gestor de dependencias Python)
- [Docker Compose](https://docs.docker.com/compose/) (incluido en Docker Desktop)

---

## Arranque rápido (recomendado con Docker)

### ⚡ Opción A — Script automático (Windows)

Desde la raíz del proyecto hay dos scripts `.bat` listos para usar:

| Script | Acción |
|---|---|
| **`levantar.bat`** | Arranca Docker, aplica migraciones y lanza el frontend |
| **`parar.bat`** | Para todos los servicios Docker limpiamente |

Simplemente haz **doble clic** en `levantar.bat`. El script:
1. Detecta si Docker Desktop está corriendo (si no, lo abre y espera)
2. Ejecuta `docker-compose up -d`
3. Espera a que la BD esté lista y aplica las migraciones Alembic
4. Abre el frontend Next.js en una ventana separada

---

### 🛠️ Opción B — Manual paso a paso

### 1. Copia el archivo de entorno
```bash
cd backend
copy .env.example .env
```
Edita `backend/.env` y añade tu `OPENAI_API_KEY` o `ANTHROPIC_API_KEY` si usas modelos cloud. Sin claves, el sistema funciona con **Ollama local** (llama3.2).

### 2. Levanta todos los servicios
```bash
docker-compose up -d
```

Esto arranca (desde tu máquina):
| Servicio | URL | Notas |
|---|---|---|
| API Backend | `http://localhost:8080` | |
| Docs Swagger | `http://localhost:8080/docs` | |
| PostgreSQL | `localhost:5432` | Límite: 512 MB RAM |
| Redis | `localhost:6379` | Límite: 256 MB RAM, política LRU |
| Ollama (LLM local) | `http://localhost:11434` | **No arranca por defecto** — ver nota abajo |

> **Ollama es opcional.** Por defecto el sistema usa `openrouter` como proveedor LLM (ver `.env`).
> Para levantar Ollama: `docker-compose --profile llm up -d`

### 3. Aplica las migraciones de base de datos
```bash
docker-compose exec api alembic upgrade head
```

### 4. Instala y arranca el frontend
```bash
cd frontend
npm install
npm run dev
```
Abre http://localhost:3000 en tu navegador.

---

## Datos de demo rápidos

Gestiona los datos demo manualmente con estos comandos:

```bat
# Poblar con datos realistas (clientes, facturas, empleados, CRM, banca)
docker-compose exec api python scripts/seed_demo.py

# Resetear: borrar todo y repoblar desde cero
docker-compose exec api python scripts/seed_demo.py --reset

# Limpiar: borrar todos los datos y dejar la cuenta vacía
docker-compose exec api python scripts/seed_demo.py --clear
```

El seed crea automáticamente:
- 7 contactos (5 clientes + 2 proveedores) con NIF y datos reales
- 8 productos y servicios en el catálogo
- 13 facturas emitidas (pagadas, pendientes y borradores) + 6 recibidas
- 5 empleados con fecha de alta, cargo y salario
- 12 nóminas (últimos 3 meses)
- 5 oportunidades CRM en distintas fases + 6 actividades
- 20 movimientos bancarios con saldo acumulado

## Test integral del sistema

Prueba automatizada que cubre todas las funcionalidades: ERP, CRM, RRHH, contabilidad, motor de workflows y agentes IA.

```bash
docker-compose exec api python scripts/full_system_test.py
```

El script:
- Se autentica y crea datos de prueba completos
- Recorre los 17 módulos del sistema con verificaciones PASS/FAIL
- Lanza tareas IA (billing, hr, crm, advisory) y espera su resultado
- Prueba el motor de workflows: parse NL, event-based, schedule-based, fire-event, pause/resume, historial de ejecuciones
- Imprime al final un resumen de ratio de éxito y un checklist de qué verificar en la UI

- **Usuario demo**: `demo@automatizapyme.com` / `Demo1234!`
- **Dashboard**: `http://localhost:3000` (Next.js en desarrollo)
- **Backend API** (para pruebas manuales): `http://localhost:8080`

Con esto tendrás:
- Al menos un cliente, producto y varias facturas emitidas.
- Una nómina de ejemplo con su PDF en Documentos.
- Varias tareas IA en distintos dominios y aprobaciones pendientes de facturación.

---

## Desarrollo local (sin Docker)

### Backend

```bash
cd backend

# Instalar dependencias
poetry install

# Crear base de datos local (necesitas PostgreSQL y Redis corriendo)
cp .env.example .env   # editar con tus credenciales locales
alembic upgrade head

# Arrancar la API
uvicorn app.main:app --reload --port 8000

# Arrancar el worker Celery (en otra terminal)
celery -A app.workers.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Rutas de la API (v1)

### Autenticación y sistema
| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/auth/register` | Registro (crea tenant + usuario admin) |
| `POST` | `/api/v1/auth/login` | Login, devuelve JWT |
| `POST` | `/api/v1/auth/refresh` | Renueva el token JWT |
| `GET`  | `/health` | Health check |

### Tareas IA y aprobaciones
| Método | Ruta | Descripción |
|---|---|---|
| `GET`  | `/api/v1/tasks` | Lista tareas del tenant |
| `POST` | `/api/v1/tasks` | Crea nueva tarea IA |
| `GET`  | `/api/v1/tasks/{id}` | Detalle de una tarea |
| `DELETE` | `/api/v1/tasks/{id}` | Cancela una tarea |
| `GET`  | `/api/v1/tasks/{id}/audit` | Log de auditoría de una tarea |
| `GET`  | `/api/v1/approvals` | Lista aprobaciones pendientes |
| `POST` | `/api/v1/approvals/{id}/decide` | Aprobar o rechazar |

### ERP (facturación, clientes, productos)
| Grupo | Prefijo | Operaciones |
|---|---|---|
| Facturas | `/api/v1/invoices` | CRUD, generación de PDF, líneas de factura |
| Presupuestos | `/api/v1/quotes` | CRUD, líneas de presupuesto |
| Clientes | `/api/v1/clients` | CRUD |
| Productos | `/api/v1/products` | CRUD |

### Módulos de dominio
| Grupo | Prefijo | Descripción |
|---|---|---|
| RRHH | `/api/v1/hr` | Empleados, nóminas, generación de PDF |
| CRM | `/api/v1/crm` | Oportunidades, actividades, eventos, reservas |
| Banca | `/api/v1/banking` | Cuentas, transacciones, informes |
| Contabilidad | `/api/v1/accounting` | Asientos contables, libro diario |
| Compliance | `/api/v1/compliance` | Modelos fiscales AEAT, vencimientos |
| Documentos | `/api/v1/documents` | Upload, descarga, clasificación |
| Proyectos | `/api/v1/projects` | Proyectos y tareas de proyecto |
| Workflows | `/api/v1/workflows` | CRUD automatizaciones, ejecución manual |
| Integraciones | `/api/v1/integrations` | Configuración de conectores externos |
| Skills | `/api/v1/skills` | Registro y ejecución de skills |
| Asesoría | `/api/v1/advisory` | Recomendaciones de compliance |

> Documentación interactiva completa en **Swagger UI**: `http://localhost:8080/docs`

---

## Comportamiento real de tareas, aprobaciones y documentos

- **Tareas (`/tareas`)**
  - `POST /api/v1/tasks` crea una tarea ligada a un dominio (`billing`, `documents`, `hr`, `banking`, `rag`, `crm`, `compliance`).
  - El orquestador (`LangGraph`) clasifica, planifica y delega en el agente correspondiente.
  - El resultado se guarda en `task.agent_results` y se audita en `AuditLog`.

- **Aprobaciones (`/aprobaciones`)**
  - Sólo se usan cuando un **agente IA** considera que una acción es de riesgo (por ejemplo, una factura elevada).
  - El agente de facturación (`billing_agent`) puede devolver `approval_required` → se crea un `PendingApproval` y la tarea queda en `awaiting_approval`.
  - Las facturas creadas directamente desde el módulo ERP (`/erp`) **no** pasan por aprobaciones: son operaciones deterministas de ERP clásico.

- **Documentos y PDFs (`/documents`)**
  - El backend genera PDFs para:
    - Facturas (`/api/v1/invoices/{id}/pdf` + tareas de billing IA).
    - Nóminas (`/api/v1/hr/payrolls/{id}/pdf` y `/approve`).
  - Los archivos se guardan bajo `backend/uploads/` y se registran en `TenantDocument` con categoría:
    - `Facturas` para PDFs de factura.
    - `Nominas` para PDFs de nómina.
    - Otras categorías (`RRHH`, `CRM`, `otros`) para resultados de agentes IA en texto.
  - El frontend debe descargar siempre los archivos mediante `fetch()` con token JWT en `Authorization`, nunca con enlaces directos.

---

## Páginas del Dashboard

### Generales

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/login` | Login | Pantalla de inicio de sesion con email y contraseña |
| `/registro` | Registro | Registro de nueva empresa (crea tenant + usuario admin) |
| `/` | Dashboard | Resumen general de actividad: KPIs, ultimas facturas, tareas recientes, graficos de ingresos |
| `/primeros-pasos` | Primeros pasos | Guia de onboarding para configurar la empresa paso a paso |
| `/tareas` | Tareas IA | Lista de tareas enviadas a los agentes IA. Crear nueva tarea en lenguaje natural, ver estado y resultado |
| `/aprobaciones` | Aprobaciones | Acciones de riesgo detectadas por la IA que requieren confirmacion del usuario antes de ejecutarse |
| `/auditoria` | Auditoria | Log inmutable de todas las acciones realizadas por agentes IA, con detalle por tarea |
| `/automatizaciones` | Automatizaciones | Crear y gestionar reglas automaticas en lenguaje natural (workflows). Historial de ejecuciones, pause/resume |
| `/analitica` | Analitica | Dashboard de metricas: ingresos, gastos, evolucion mensual, top clientes y productos |
| `/documentos` | Documentos | Gestor documental: subir, clasificar y buscar archivos. Los PDFs generados (facturas, nominas) se guardan aqui |
| `/escaner` | Escaner OCR | Subir documentos fisicos (facturas, contratos) y extraer datos automaticamente con OCR |

### ERP — Ventas

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/ventas/facturas` | Facturas emitidas | Listado de facturas de venta con estados (borrador, pendiente, pagada, cancelada). Crear nueva factura, ver detalle, cambiar estado, descargar PDF |
| `/ventas/facturas/nueva` | Nueva factura | Formulario para crear una factura seleccionando cliente, productos/servicios, cantidades y precios |
| `/ventas/facturas/[id]` | Detalle de factura | Vista completa de una factura con lineas, totales, botones de cambio de estado y descarga de PDF |
| `/ventas/presupuestos` | Presupuestos | Crear y gestionar presupuestos. Se pueden convertir directamente en factura con un clic |
| `/ventas/pedidos` | Pedidos de venta | Seguimiento de pedidos con flujo de estados: pendiente, confirmado, enviado, entregado |
| `/ventas/recurrentes` | Facturas recurrentes | Plantillas de facturacion periodica (mensual, trimestral). Se pueden pausar y reactivar |
| `/ventas/servicios` | Servicios | Catalogo de servicios que ofrece la empresa, con precio y descripcion. Se usan al crear facturas |

### ERP — Compras

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/compras/facturas` | Facturas de compra | Registro de facturas recibidas de proveedores con totales calculados desde BD |
| `/compras/pedidos` | Pedidos de compra | Pedidos a proveedores con flujo de estados: pendiente, confirmado, recibido |
| `/compras/proveedores` | Proveedores | Directorio de proveedores con datos de contacto y NIF |

### ERP — Catalogo, clientes e inventario

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/catalogo` | Catalogo de productos | Alta, edicion y eliminacion de productos y servicios. Busqueda en tiempo real, precios e IVA |
| `/clientes` | Clientes | Listado de clientes con nombre, NIF, email y telefono. Editar y eliminar desde drawer lateral |
| `/clientes/[id]` | Ficha de cliente | Vista detallada de un cliente con timeline de actividad: facturas emitidas, interacciones CRM, documentos |
| `/inventario/stock` | Stock | Movimientos de stock (entradas, salidas, ajustes) por producto con trazabilidad completa |

### RRHH

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/rrhh/empleados` | Empleados | Listado de empleados con cargo, departamento y salario. Crear, editar y eliminar con menu contextual |
| `/rrhh/nominas` | Nominas | Generar nominas por empleado con bruto, deducciones y neto. Aprobar para generar PDF descargable |

### CRM

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/crm/embudo-de-ventas` | Embudo de ventas | Oportunidades comerciales organizadas por etapa (lead, contactado, propuesta, negociacion, ganada/perdida). Busqueda y eliminacion. Boton "Pedir a la IA" para analisis del pipeline |
| `/crm/actividades` | Actividades | Registro de llamadas, emails, notas y visitas asociadas a clientes u oportunidades. Historial completo de interacciones comerciales |
| `/crm/calendario` | Calendario | Vista de calendario con todos los eventos (reuniones, llamadas, citas). Crear nuevos eventos y ver detalle de cada uno |
| `/crm/reuniones` | Reuniones | Listado de reuniones programadas con fecha, ubicacion y notas. Crear, buscar y eliminar reuniones |
| `/crm/reservas` | Reservas | Gestion de reservas de clientes con estados (pendiente, confirmada, finalizada, cancelada). Confirmar, finalizar o cancelar desde la lista |

### Contabilidad

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/contabilidad/libro-diario` | Libro diario | Asientos contables con cuentas del PGC, importes Debe/Haber y fecha. Crear nuevos asientos equilibrados |
| `/contabilidad/cuadro-de-cuentas` | Cuadro de cuentas | Arbol interactivo del Plan General Contable expandible por grupo, subcuenta. Muestra Debe, Haber y Saldo con busqueda en tiempo real |
| `/contabilidad/balance-de-situacion` | Balance de situacion | Balance de activo, pasivo y patrimonio neto calculado desde el libro diario |
| `/contabilidad/perdidas-y-ganancias` | Cuenta de PyG | Cuenta de resultados con ingresos (grupo 7) y gastos (grupo 6) del PGC, porcentajes y estado vacio limpio |
| `/contabilidad/activos` | Activos fijos | CRUD de activos fijos con amortizacion lineal calculada automaticamente. Preview de cuota en modal de creacion |
| `/contabilidad/asesorias` | Asesoria juridica y fiscal | Guias normativas por seccion (fiscal, laboral, mercantil) con referencias al BOE, consejos para PYMEs, noticias del BOE y chat con asesor IA |

### Tesoreria

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/tesoreria/cashflow` | Cash flow | Prevision de tesoreria con entradas y salidas esperadas, grafico de evolucion de saldo |
| `/tesoreria/pagos-y-cobros` | Pagos y cobros | Control de pagos pendientes a proveedores y cobros pendientes de clientes |
| `/tesoreria/remesas` | Remesas | Agrupacion de cobros/pagos en remesas bancarias para envio al banco |

### Proyectos

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/proyectos` | Vista general | Resumen de todos los proyectos activos con progreso y estado |
| `/proyectos/proyectos` | Proyectos | Listado y creacion de proyectos con nombre, descripcion, fechas y estado |
| `/proyectos/tareas` | Tareas de proyecto | Tareas asociadas a proyectos con asignacion, prioridad y seguimiento |
| `/proyectos/mis-tareas` | Mis tareas | Vista filtrada con solo las tareas asignadas al usuario actual |

### Otros

| Ruta | Pagina | Descripcion |
|---|---|---|
| `/banca` | Banca | Cuentas bancarias, movimientos y conciliacion. Informes financieros generados por IA |
| `/compliance` | Compliance | Calendario de obligaciones fiscales AEAT, novedades del BOE y consultas al asesor IA |
| `/impuestos` | Impuestos | Calendario fiscal con KPIs de vencimientos urgentes y proximos. Consulta al asesor IA |
| `/integraciones` | Integraciones | Configurar conexiones externas: Holded, banca PSD2, email, Azure OCR |
| `/configuracion/empresa` | Empresa | Datos de la empresa: razon social y NIF/CIF |

---

## Estado de implementación de agentes

| Agente | Dominio | Estado | Notas |
|---|---|---|---|
| **Billing** | `billing` | ✅ Implementado | Crea facturas, genera PDF, aprobaciones de riesgo |
| **Documents** | `documents` | ✅ Implementado | OCR, clasificación, gestión documental |
| **Compliance** | `compliance` | ✅ Implementado | Modelos fiscales AEAT, vencimientos, BOE |
| **HR** | `hr` | ✅ Implementado | Nóminas, empleados, PDFs de nómina |
| **Banking** | `banking` | ✅ Implementado | Saldos, movimientos, informe financiero (mock PSD2) |
| **CRM** | `crm` | ✅ Implementado | Leads, oportunidades, embudo de ventas |
| **Excel** | `excel` | ✅ Implementado | Cruce de datos, generación de informes tabulares |
| **Email** | `email` | ✅ Implementado | Lectura y envío de correos (mock inbox, real send pendiente) |
| **RAG** | `rag` | ✅ Implementado | Consultas semánticas sobre documentos archivados |
| **Orquestador multiagente** | `coordinator` | ✅ Implementado | Resuelve tareas complejas puntuales coordinando agentes en secuencia (usa `ExecutionContext`) |
| **Workflow Agent** | `workflow` | ✅ Implementado | Gestiona la creación y modificación de automatizaciones desde lenguaje natural |

### Automatizaciones y Workflows

| Módulo | Estado | Notas |
|---|---|---|
| Crear/editar workflows en lenguaje natural | ✅ Implementado | Tabla `Workflow` + `WorkflowExecution` |
| Triggers por tiempo (`schedule_based`) | ✅ Implementado | Celery Beat + cron expresions |
| Triggers por evento (`event_based`) | ✅ Implementado | Emisión de `DomainEvent` y respuesta automática de workflows |
| Triggers manuales | ✅ Implementado | Botón en la UI |
| Historial de ejecuciones | ✅ Implementado | Vista `/automatizaciones` en el dashboard |
| Persistencia de Eventos | ✅ Implementado | Tabla `domain_events` para auditoría y triggering reactivo |

### Integraciones externas

| Integración | Archivo | Estado |
|---|---|---|
| **Holded** (ERP) | `integrations/holded.py` | Conector implementado |
| **PSD2 Banking** | `integrations/psd2.py` | Mock (Nordigen/GoCardless pendiente) |
| **Azure Form Recognizer** | `integrations/azure_forms.py` | OCR de documentos |
| **BOE Scraper** | `integrations/boe_scraper.py` | Scraping del Boletín Oficial del Estado |

### Modelo de datos (28 tablas)

| Grupo | Tablas |
|---|---|
| Multi-tenancy | `tenants`, `users`, `tenant_integrations`, `tenant_knowledge`, `tenant_documents` |
| Tareas IA | `tasks`, `audit_log`, `pending_approvals`, `domain_events` |
| ERP | `products`, `clients`, `invoices`, `invoice_lines`, `quotes`, `quote_lines` |
| RRHH | `employees`, `payrolls` |
| CRM | `opportunities`, `activities`, `events`, `reservations` |
| Contabilidad | `journal_entries`, `journal_lines`, `bank_transactions` |
| Proyectos | `projects`, `project_tasks` |
| Automatizaciones | `workflows`, `workflow_executions` |

### Modos de ejecución de Workflows

Cada Workflow tiene un campo `execution_mode` que determina cómo se ejecutan sus pasos:

#### Modo `reasoning` (por defecto)

El orquestador LangGraph interpreta la instrucción del workflow en tiempo real en cada ejecución. El LLM recibe el contexto actual del tenant (facturas pendientes, empleados activos, etc.) y decide los pasos a ejecutar en ese momento concreto.

- **Ventajas**: Flexible y adaptable al contexto actual. Puede tomar decisiones diferentes según el estado real de los datos.
- **Inconvenientes**: Consume tokens LLM en cada ejecución. Mayor latencia.
- **Ideal para**: Workflows que requieren razonamiento complejo o que dependen de datos cambiantes (ej: "analiza las facturas vencidas y actúa según el importe").

#### Modo `deterministic`

Al crear el workflow, se realiza una llamada extra al LLM para **compilar** los pasos concretos de ejecución una sola vez. Estos pasos se almacenan en el campo `compiled_steps` (JSONB). En cada ejecución posterior, los pasos se ejecutan directamente llamando a las funciones `_dispatch_*` del orquestador sin ninguna llamada adicional al LLM.

Ejemplo de `compiled_steps`:
```json
[
  {"agent": "billing", "action": "generate_recurring_invoices", "params": {"intent": "Generar facturas recurrentes para todos los clientes activos"}},
  {"agent": "email", "action": "send_notifications", "params": {"intent": "Enviar PDF de factura a cada cliente por email"}}
]
```

- **Ventajas**: Ejecución instantánea sin latencia de LLM. Coste cero en cada ejecución (solo se consume un token al crear la regla). Comportamiento predecible y reproducible.
- **Inconvenientes**: No se adapta al contexto. Los pasos son fijos desde el momento de creación.
- **Ideal para**: Workflows repetitivos y bien definidos (ej: "el día 1 de cada mes, genera las nóminas de todos los empleados").

#### Tabla comparativa

| | `reasoning` | `deterministic` |
|---|---|---|
| **Coste LLM por ejecución** | Tokens por ejecución | 0 (compilado al crear) |
| **Latencia** | Mayor (llamada LLM) | Mínima (ejecución directa) |
| **Adaptabilidad** | Alta (contexto real) | Baja (pasos fijos) |
| **Predictibilidad** | Media | Alta |
| **Caso de uso** | Workflows complejos o contextuales | Workflows repetitivos y definidos |

#### Cambios en la base de datos

La migración `c9e1f3a5b7d2` añade dos columnas a la tabla `workflows`:
- `execution_mode VARCHAR(20) NOT NULL DEFAULT 'reasoning'`
- `compiled_steps JSONB`

### Próximas mejoras

- **Email Agent real**: integración OAuth Gmail/IMAP para bandeja de entrada real
- **PSD2 real**: conexión con bancos vía Nordigen/GoCardless
- **Memoria entre conversaciones**: contexto persistente por tenant para el orquestador
- **Aprendizaje adaptativo**: retroalimentación de correcciones manuales del usuario

---

## Infraestructura Docker — Optimizaciones

### Límites de recursos por servicio

| Servicio | RAM máx | CPU máx | Notas |
|---|---|---|---|
| `db` (PostgreSQL) | 512 MB | 1 core | `shared_buffers=128MB`, `max_connections=50` |
| `redis` | 384 MB | 0.5 core | `maxmemory 256mb`, política `allkeys-lru`, sin persistencia en disco |
| `api` (FastAPI) | 1 GB | 1.5 cores | Modo `--reload` en desarrollo |
| `worker` (Celery) | 768 MB | 1 core | `--concurrency 2 --max-tasks-per-child 50` |
| `ollama` | 4 GB | 2 cores | Solo activo con `--profile llm`; GPU si disponible |

### Dockerfile multi-stage
El `backend/Dockerfile` usa **dos etapas**:
1. **`builder`**: compila con `build-essential` + instala solo dependencias de producción (`--only main`)
2. **Imagen final**: sin compiladores, solo `libpq-dev`. Excluye pytest, mypy, ruff y otras dev-deps.

El `backend/.dockerignore` excluye `.venv/` (323 MB), `__pycache__/`, `.mypy_cache/`, `.ruff_cache/`, `uploads/` y `.env` del contexto de build.

### Cambiar proveedor LLM
Edita `.env` en la raíz del proyecto:
```
DEFAULT_LLM_PROVIDER=openrouter   # Por defecto (usa OPENROUTER_API_KEY)
DEFAULT_LLM_PROVIDER=openai       # Usa OPENAI_API_KEY
DEFAULT_LLM_PROVIDER=groq         # Usa GROQ_API_KEY
DEFAULT_LLM_PROVIDER=ollama       # Local — requiere: docker-compose --profile llm up -d
```

---

## Variables de entorno (backend/.env)

| Variable | Descripción |
|---|---|
| `ENVIRONMENT` | Entorno de ejecución (`development` / `production`) |
| `SECRET_KEY` | Clave secreta para JWT (generar con `openssl rand -hex 32`) |
| `TENANT_ENCRYPTION_KEY` | Clave Fernet para cifrar credenciales de integraciones |
| `DATABASE_URL` | Conexión PostgreSQL (asyncpg) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales PostgreSQL (para Docker) |
| `REDIS_URL` | URL de Redis |
| `CELERY_BROKER_URL` | URL del broker Celery (Redis) |
| `CELERY_RESULT_BACKEND` | URL del backend de resultados Celery (Redis) |
| `DEFAULT_LLM_PROVIDER` | Proveedor LLM por defecto: `ollama`, `openai`, `anthropic`, `gemini`, `groq`, `openrouter` |
| `OLLAMA_BASE_URL` | URL del servidor Ollama local |
| `OPENAI_API_KEY` | API key de OpenAI (opcional) |
| `ANTHROPIC_API_KEY` | API key de Anthropic (opcional) |
| `GEMINI_API_KEY` | API key de Google Gemini (opcional) |
| `GROQ_API_KEY` | API key de Groq (opcional) |
| `OPENROUTER_API_KEY` | API key de OpenRouter (opcional) |

> Ver `backend/.env.example` para una plantilla completa con valores por defecto.
