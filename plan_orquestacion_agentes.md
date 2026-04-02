# Blueprint Maestro: AutomatizaPyme (Visión + Arquitectura Exhaustiva)

Este documento centraliza la hoja de ruta integral para la evolución del ERP AutomatizaPyme hacia una plataforma de automatización extrema ("Empresa Cero-Humanos"). Se bifurca en una definición detallada del producto (Casos de Uso) y una Especificación de Ingeniería (Estructuras de Datos, Seguridad y Redes) diseñada explícitamente sin ambigüedades arquitectónicas para su correcta implementación en código.

---

# PARTE 1: VISIÓN ESTRATÉGICA DE PRODUCTO

El objetivo fundamental es pivotar de un "Software de Gestión Reactivo" (donde el usuario navega menús e introduce datos) a una "Agencia Autonómica Proactiva" (donde el usuario contrata agentes virtuales que trabajan en segundo plano y solicitan aprobación únicamente en decisiones críticas).

## 1. Módulo Core: El Organigrama IA (`/mi-equipo`)
El usuario no configura "Workflows de LangGraph", sino que visualiza un organigrama empresarial tradicional compuesto por perfiles virtuales (Ej: "Ana - Directora Financiera", "Carlos - Responsable de RRHH").
* **Paradigma The Heartbeat:** Los agentes no solo reaccionan a webhooks. Tienen un "latido" (Cron interno) mediante el cual revisan su "Bandeja de Entrada" (Inbox de Tareas Pendientes).
* **Estados en Tiempo Real:** Visualmente, cada agente tiene un indicador de estado. `Durmiendo` (procesamiento inactivo para ahorro de API), `Analizando` (LLM actuando), o `Requiere Firma` (Bloqueado esperando un click del Manager/Usuario humano).

![Mockup del Organigrama del Equipo de IA](C:/Users/Marcos/.gemini/antigravity/brain/76bb3043-fba5-468e-8743-68a1f1a28eee/ai_empleados_organigrama_1774999771065.png)

## 2. Casos de Uso "Killer" (Módulos Expansivos)

### A. Módulo Legal y Contractual ("Gestora Documental")
* **Problema:** Redactar contratos laborales o NDAs toma horas y requiere copiado y pegado propenso a errores.
* **Solución IA:** Un agente extrae los metadatos del CRM o del módulo de Nóminas y utiliza un motor como `docxtpl` para inyectar los datos reales en plantillas `.docx` con formato original de la empresa (respetando tablas, logos y estilos). Permite la generación de borradores de cláusulas redactadas a medida a petición del gerente.

> [!WARNING]
> **Responsabilidad Legal:** Ningún LLM garantiza corrección jurídica. Las cláusulas generadas por la IA son **siempre borradores** que requieren revisión y aprobación humana explícita antes de generar el documento definitivo. El sistema debe forzar el paso por un nodo de "Aprobación Obligatoria" antes de exportar el `.docx`/PDF final. Esto protege al desarrollador y al cliente de responsabilidad civil por contenido alucinado.

### B. Módulo de Reclutamiento ("Técnico Seleccionador")
* **Problema:** Criba caótica de cientos de PDFs recibidos por ofertas de empleo.
* **Solución IA:** El sistema lee cada PDF usando LLMs multimodales, normaliza la información (Años de experiencia, Stack Tecnológico, Idiomas) y la vuelca estructurada en una base de datos relacional interna (`candidatos`), emitiendo una puntuación (Scoring) basada en los requisitos del puesto abierto.

### C. Almacén Móvil Omnicanal ("Gestor de Inventario Local")
* **Problema:** Hardware de escaneo costoso que no se integra en tiempo real con la nube sin pagar grandes licencias.
* **Solución IA:** Usar la arquitectura Localhost del ERP para exponer un servidor en la WiFi de la empresa. Los operarios con smartphones estándar entran en la IP local, usan su cámara y actualizan el inventario bidireccionalmente.

### D. Módulo de Marketing ("Planificador de Contenidos")
* **Problema:** PYMEs con stock inmovilizado sin conocimientos ni tiempo para publicitarlo en redes sociales.
* **Solución IA (V1 — Planificación y Sugerencias):** El agente de Marketing **no publica directamente en redes sociales**. Analiza el catálogo de productos (stock, precios, tendencias) y genera un plan de contenidos: textos sugeridos (copies), ideas de imágenes, hashtags recomendados y un calendario de publicación óptimo. El usuario revisa las sugerencias, las ajusta si lo desea, y las ejecuta manualmente en sus redes.
* **Solución IA (V2 — Conectores de Publicación Programada):** Integración con APIs de redes sociales (Meta Graph API para Instagram/Facebook, LinkedIn API, Twitter/X API) para publicación programada. El agente prepara el contenido y lo encola con fecha y hora. El usuario aprueba con un clic y el conector lo publica automáticamente a la hora programada. La integración con Meta requiere un proceso de revisión de apps que puede tardar semanas, por lo que esta fase no se debe prometer en demos iniciales.

> [!NOTE]
> **Sobre generación de imágenes:** DALL-E 3 cuesta ~0.04$/imagen. Si se ofrece generación de banners, el coste se descuenta del presupuesto del agente (`budget_limit_usd`). Las imágenes generadas se almacenan en la carpeta local del tenant (`/data/tenants/{id}/marketing/assets/`), no en la nube.

## 3. Ventaja Competitiva: El Búnker Operativo
Frente a orquestadores de la nube (Ej. Paperclip AI), AutomatizaPyme basa su defensa comercial en su estado híbrido-local (Electron):

* **Privacidad Híbrida (RAG Local + Cloud Anonimizado):** El sistema RAG actual ya procesa documentos sensibles (facturas, nóminas, DNIs) localmente mediante embeddings almacenados en pgvector. El LLM en la nube (Claude/Gemini) únicamente recibe el contexto extraído y estructurado, nunca el documento original en crudo.

* **Comunicación Externa Escalonada:**
  - **V1 (Inmediato):** Email bidireccional vía SMTP (ya implementado). El agente "Sofía" puede enviar facturas, recordatorios de pago y confirmaciones por correo electrónico de forma autónoma.
  - **V2 (Medio plazo):** Bot de Telegram integrado. API gratuita, sin proceso de revisión, ideal para notificaciones internas y consultas rápidas de empleados o clientes.
  - **V3 (Largo plazo):** WhatsApp Business API. Requiere número verificado por Meta, Business Manager aprobado, y plantillas de mensajes pre-aprobadas. No se debe prometer hasta tener la infraestructura de V1 y V2 validada.
### E. Feed de Actividad ("¿Qué han hecho mis empleados hoy?")
* **Problema:** Cuando varios agentes trabajan en segundo plano de forma autónoma (enviando emails, generando nóminas, actualizando inventario), el gerente abre la app y no tiene forma rápida de saber qué ocurrió mientras no estaba. Tiene que ir módulo por módulo revisando cambios.
* **Solución:** Un Timeline cronológico unificado en la pantalla principal del ERP que muestra la actividad de todos los empleados virtuales en lenguaje natural. Es el equivalente a entrar a la oficina por la mañana y que cada empleado te cuente en 10 segundos qué hizo ayer. Cada herramienta (Tool) del sistema, al completar su ejecución, escribe una entrada en este feed. El usuario ve de un vistazo el pulso completo de su empresa sin navegar a ningún módulo específico.

---

# PARTE 2: ESPECIFICACIÓN DE INGENIERÍA (Hard Architecture)

Este bloque define las implementaciones de bajo nivel necesarias para materializar la capa superior de manera estricta y segura.


## 1. Esquema Relacional de Agentes Dinámicos (PostgreSQL)
Reemplazar los agentes en código duro por un sistema "Data-Driven". Se exige el uso de UUIDs para fragmentación horizontal futura.

```python
# backend/app/models/ai_employees.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

class AIEmployee(Base):
    __tablename__ = "ai_employees"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    name = Column(String(100), nullable=False)          # e.g., "Ana Valdés"
    role = Column(String(100), nullable=False)           # e.g., "Directora Financiera"
    domain = Column(String(50), nullable=False)          # e.g., "billing", "hr", "legal" — used for routing
    system_prompt = Column(Text, nullable=False)         # Strict behavioral instructions for the LLM
    budget_limit_usd = Column(Numeric(10, 2), default=10.00) # Monthly spending cap in USD
    status = Column(String(20), default="idle")          # State machine: idle | working | paused | blocked
    is_builtin = Column(Boolean, default=False)          # True for pre-shipped agents (Ana, Carlos), False for user-created
    created_at = Column(DateTime, default=datetime.utcnow)

class AgentSkill(Base):
    """Many-to-Many mapping table authorizing tools to explicit agents.
    If a tool_module is NOT listed here for an employee, that employee
    physically cannot invoke it, regardless of what the LLM hallucinates."""
    __tablename__ = "agent_skills"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    employee_id = Column(UUID, ForeignKey("ai_employees.id", ondelete="CASCADE"))
    tool_module = Column(String(255), nullable=False)    # Registry key, e.g., "billing.create_invoice"

class TokenLedger(Base):
    """Immutable Append-Only Audit Log for API Cost Governance.
    Every single LLM invocation inserts a row here. Never updated, never deleted."""
    __tablename__ = "token_ledger"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    employee_id = Column(UUID, ForeignKey("ai_employees.id"))
    task_id = Column(UUID, nullable=True)                # Traceability to the triggering workflow
    prompt_tokens = Column(Integer, nullable=False)
    completion_tokens = Column(Integer, nullable=False)
    cost_usd = Column(Numeric(10, 6), nullable=False)    # 6 decimal precision for micro-costs
    llm_provider = Column(String(50))                    # "gemini", "claude_cli", "ollama"
    created_at = Column(DateTime, default=datetime.utcnow)
```

## 1b. Motor del Heartbeat (APScheduler — Agentes Proactivos)

El "paradigma Heartbeat" requiere que cada `AIEmployee` activo tenga un cron job asociado que revise su inbox periódicamente. Como los agentes son dinámicos (creados/pausados por el usuario en runtime), los jobs de APScheduler deben registrarse y cancelarse dinámicamente, no en el arranque.

### A. Scheduler Singleton
```python
# backend/app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler(timezone="UTC")

def get_scheduler() -> AsyncIOScheduler:
    return scheduler
```

### B. Registro/Cancelación Dinámica de Jobs
```python
# backend/app/services/heartbeat_service.py
from backend.app.core.scheduler import get_scheduler

HEARTBEAT_INTERVAL_SECONDS = 300  # 5 minutes default — overridable per employee in future

def register_employee_heartbeat(employee_id: str, tenant_id: str):
    """Registers a recurring job for an AIEmployee. Safe to call on duplicates
    (remove_if_exists before re-adding). Called when an employee is created or unpaused."""
    scheduler = get_scheduler()
    job_id = f"heartbeat_{employee_id}"

    # Idempotent: remove existing job before re-registering
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        func=run_employee_heartbeat,
        trigger="interval",
        seconds=HEARTBEAT_INTERVAL_SECONDS,
        id=job_id,
        kwargs={"employee_id": employee_id, "tenant_id": tenant_id},
        replace_existing=True,
        misfire_grace_time=60,  # If the job missed its slot by <60s, still run it
    )

def unregister_employee_heartbeat(employee_id: str):
    """Cancels the cron job. Called when an employee is paused or deleted."""
    scheduler = get_scheduler()
    job_id = f"heartbeat_{employee_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

async def run_employee_heartbeat(employee_id: str, tenant_id: str):
    """The actual heartbeat logic. Checks if the employee has pending tasks
    in their inbox and dispatches them to the dynamic agent graph."""
    # Uses a fresh DB session per execution (scheduler runs outside request context)
    async with get_async_db_session() as db:
        has_budget = await check_agent_budget(employee_id, db)
        if not has_budget:
            unregister_employee_heartbeat(employee_id)  # Stop waking a paused agent
            return

        pending_tasks = db.query(Task).filter(
            Task.assigned_employee_id == employee_id,
            Task.status == "pending"
        ).all()

        for task in pending_tasks:
            graph = compile_dynamic_agent(employee_id, db)
            await graph.ainvoke({"messages": [HumanMessage(content=task.description)]})
```

### C. Bootstrap al Arranque de la App
Al iniciar FastAPI, se restauran los jobs para todos los empleados activos (por si el servidor se reinició):
```python
# backend/app/main.py  — en el evento startup
@app.on_event("startup")
async def startup_event():
    scheduler = get_scheduler()
    scheduler.start()

    # Re-register heartbeats for all non-paused employees across all tenants
    async with get_async_db_session() as db:
        active_employees = db.query(AIEmployee).filter(
            AIEmployee.status != "paused"
        ).all()
        for emp in active_employees:
            register_employee_heartbeat(str(emp.id), str(emp.tenant_id))
```

---

## 2. Tool Registry (Explicit Python Callable Mapping)
El Registry es un diccionario plano que mapea claves de string (las mismas almacenadas en `AgentSkill.tool_module`) a funciones Python decoradas con `@tool` de LangChain. Esto garantiza que no se usen importaciones dinámicas (`importlib`) que serían un vector de ataque.

```python
# backend/app/agents/tool_registry.py
from backend.app.agents.tools.billing_tools import create_invoice_tool, send_invoice_email_tool, get_pending_invoices_tool
from backend.app.agents.tools.hr_tools import create_employee_tool, generate_payroll_tool
from backend.app.agents.tools.crm_tools import get_client_info_tool, update_client_tool
from backend.app.agents.tools.inventory_tools import update_stock_tool, get_low_stock_tool
from backend.app.agents.tools.document_tools import fill_docx_template_tool, draft_clause_tool
from backend.app.agents.tools.notification_tools import send_notification_tool, send_email_tool

TOOL_REGISTRY: dict[str, Callable] = {
    # Billing Domain
    "billing.create_invoice":       create_invoice_tool,
    "billing.send_invoice_email":   send_invoice_email_tool,
    "billing.get_pending_invoices": get_pending_invoices_tool,
    # HR Domain
    "hr.create_employee":           create_employee_tool,
    "hr.generate_payroll":          generate_payroll_tool,
    # CRM Domain
    "crm.get_client_info":          get_client_info_tool,
    "crm.update_client":            update_client_tool,
    # Inventory Domain
    "inventory.update_stock":       update_stock_tool,
    "inventory.get_low_stock":      get_low_stock_tool,
    # Legal/Document Domain
    "legal.fill_docx_template":     fill_docx_template_tool,
    "legal.draft_clause":           draft_clause_tool,
    # Cross-Domain
    "notifications.send_alert":     send_notification_tool,
    "notifications.send_email":     send_email_tool,
}
```

## 3. Motor de Orquestación (FastAPI + LangGraph)

### A. Routing del Orquestador (¿A quién delego esta tarea?)
Cuando el usuario envía un mensaje al sistema (ej. "Hazme la factura de Acme"), el Orquestador central debe decidir qué empleado virtual se encarga. Esta decisión se toma en dos pasos:

```python
# backend/app/agents/orchestrator/router.py
async def route_task_to_employee(user_message: str, tenant_id: str, db: Session) -> AIEmployee:
    """Determines which AIEmployee should handle a given user request.
    Uses the LLM as a classifier, constrained to active (non-paused) employees."""
    
    # 1. Fetch all available employees for this tenant (exclude paused/over-budget)
    candidates = db.query(AIEmployee).filter(
        AIEmployee.tenant_id == tenant_id,
        AIEmployee.status != "paused"
    ).all()
    
    # 2. Build classification prompt
    employee_descriptions = "\n".join([
        f"- ID: {e.id}, Name: {e.name}, Domain: {e.domain}, Role: {e.role}"
        for e in candidates
    ])
    
    classification_prompt = f"""Given these available AI employees:
{employee_descriptions}

The user request is: "{user_message}"

Return ONLY the UUID of the employee best suited to handle this request.
If no employee fits, return "ORCHESTRATOR" to handle it directly."""
    
    # 3. LLM classifies (cheap, fast call — no tools needed)
    llm = get_tenant_llm_engine()
    response = await llm.ainvoke(classification_prompt)
    selected_id = response.content.strip()

    # SECURITY: Always filter by tenant_id — never trust the LLM-returned UUID directly.
    # A hallucinated UUID from another tenant would otherwise grant cross-tenant access.
    employee = db.query(AIEmployee).filter(
        AIEmployee.id == selected_id,
        AIEmployee.tenant_id == tenant_id  # ← mandatory tenant boundary
    ).first()

    return employee  # None if LLM returned "ORCHESTRATOR" or an invalid/foreign UUID
```

### B. Inicialización Dinámica del Agente (`custom_worker_agent.py`)
Para evitar inyección de prompts, los agentes no nacen sabiendo usar todas las herramientas del ERP. Se mutilan explícitamente durante la compilación del grafo basado en la entidad `AgentSkill`.

```python
# backend/app/agents/custom_worker_agent.py
from langgraph.graph import StateGraph
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    employee_id: str

def compile_dynamic_agent(employee_id: str, db_session: Session):
    # 1. Fetch Profile Data
    employee = db_session.query(AIEmployee).get(employee_id)
    skills = db_session.query(AgentSkill).filter(AgentSkill.employee_id == employee_id).all()
    
    # 2. Strict Tool Registry Mapping (Zero Trust Binding)
    # If the tool is not in allowed skills, the LLM physically cannot execute it.
    # Missing keys raise KeyError intentionally — fail loud, don't fail open.
    allowed_tools = []
    for skill in skills:
        if skill.tool_module not in TOOL_REGISTRY:
            raise ValueError(f"Tool '{skill.tool_module}' not found in registry. Agent {employee.name} misconfigured.")
        allowed_tools.append(TOOL_REGISTRY[skill.tool_module])
    
    # 3. LLM Instantiation with tenant-specific engine
    # Resolved via ContextVar: could be Claude CLI, Gemini API, or local Ollama
    llm = get_tenant_llm_engine() 
    llm_bound = llm.bind_tools(allowed_tools)
    
    # 4. StateGraph Assembly with injected system_prompt
    graph = StateGraph(AgentState)
    
    # Node: call_model — uses employee.system_prompt as the system message
    # Node: call_tools — executes the selected tool from allowed_tools
    # Edge: conditional routing between model ↔ tools based on tool_calls presence
    # ... (standard ReAct agent pattern)
    
    return graph.compile()
```

### C. Intercepción de Costes (Budget Enforcement)
Cada llamada al LLM envuelta por el grafo se le inyecta un `AsyncCallbackHandler` que intercepta el `usageInfo` de la respuesta del modelo y realiza un `INSERT` inmediato en `TokenLedger`. Antes de cada ejecución, se comprueba el presupuesto:

```python
# backend/app/agents/budget_guard.py
from sqlalchemy import func
from datetime import datetime, timedelta

async def check_agent_budget(employee_id: str, db: Session) -> bool:
    """Returns True if the agent has budget remaining. Raises HTTP 402 if exceeded."""
    employee = db.query(AIEmployee).get(employee_id)
    
    # Calculate total spend this month
    first_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
    monthly_spend = db.query(func.sum(TokenLedger.cost_usd)).filter(
        TokenLedger.employee_id == employee_id,
        TokenLedger.created_at >= first_of_month
    ).scalar() or 0
    
    if monthly_spend >= employee.budget_limit_usd:
        # Auto-pause the agent via DB state — do NOT raise HTTPException here.
        # LangGraph catches exceptions inside nodes silently; the HTTP 402 never
        # reaches the user. Instead, set status="paused" and return False.
        # The calling LangGraph node checks the return value and terminates the
        # graph gracefully, returning a user-facing message via AgentState.
        employee.status = "paused"
        db.commit()
        return False  # Caller must handle: add error message to AgentState and END graph

    return True
```

## 4. UI Generativa e Intercepción Reactiva (Next.js)
Las pantallas o dashboards a medida no se programarán nativamente en `.tsx`. La Inteligencia Artificial emitirá bloques de código en crudo (HTML + Tailwind) almacenables en BD para ser renderizados.

### A. Ejecución de Sandbox Front-End
Se bloqueará categóricamente la ejecución de inyección JavaScript `<script>` utilizando una doble capa:

```tsx
// frontend/app/components/GenerativeSandbox.tsx
import DOMPurify from 'dompurify';
import parse from 'html-react-parser';

// Whitelist estricta: solo los tags y atributos que la IA puede usar.
// Cualquier <script>, <iframe>, onclick, onerror, etc. se elimina silenciosamente.
const PURIFY_CONFIG = {
  ALLOWED_TAGS: [
    'div', 'span', 'p', 'table', 'thead', 'tbody', 'tr', 'td', 'th',
    'button', 'b', 'i', 'strong', 'em', 'h1', 'h2', 'h3', 'h4',
    'ul', 'ol', 'li', 'img', 'br', 'hr', 'a'
  ],
  ALLOWED_ATTR: [
    'class',              // Para clases de Tailwind
    'data-erp-action',    // Identificador de acción del ERP (ej: "block_client")
    'data-payload',       // JSON serializado con parámetros de la acción
    'src', 'alt',         // Para imágenes
    'href',               // Para links (se sanitizan automáticamente)
  ],
  // NOTE: data-payload survives DOMPurify because it's a whitelisted attribute.
  // DOMPurify only removes XSS vectors (scripts/events) — it does NOT validate
  // the JSON content inside data-payload. A prompt-injected agent could embed
  // a malicious payload that the interceptor executes blindly.
  // REQUIRED: the onAction handler (or the /api/v1/internal-actions endpoint)
  // MUST validate the payload against a strict Zod/Pydantic schema per action type
  // before executing anything. Never pass data-payload content directly to the API.
  FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input'],
  FORBID_ATTR: ['onclick', 'onerror', 'onload', 'onmouseover'],
};

interface SandboxProps {
  rawHtmlResponse: string;  // HTML crudo devuelto por el agente
  onAction?: (action: string, payload: Record<string, any>) => void;
}

export const GenerativeSandbox = ({ rawHtmlResponse, onAction }: SandboxProps) => {
  // Capa 1: Sanitización estricta (elimina cualquier vector XSS)
  const cleanHtml = DOMPurify.sanitize(rawHtmlResponse, PURIFY_CONFIG);

  // Capa 2: Interceptor de acciones ERP delegadas desde el HTML generado
  const handleInterceptActions = async (event: React.MouseEvent<HTMLDivElement>) => {
    const target = event.target as HTMLElement;
    const erpAction = target.getAttribute('data-erp-action');
    
    if (erpAction) {
      event.preventDefault();
      event.stopPropagation();
      
      let payload = {};
      try {
        payload = JSON.parse(target.getAttribute('data-payload') || '{}');
      } catch (e) {
        console.error('Invalid data-payload JSON on generative button:', e);
        return;
      }
      
      if (onAction) {
        onAction(erpAction, payload);
      } else {
        // Fallback: direct API call
        await fetch(`/api/v1/internal-actions/${erpAction}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }
    }
  };

  // Capa 3: Render seguro como nodos React (no innerHTML directo)
  return (
    <div className="w-full flex-col generative-container" onClickCapture={handleInterceptActions}>
      {parse(cleanHtml)}
    </div>
  );
};
```

## 5. Arquitectura Gatekeeper (Seguridad de Red Local para Almacén Móvil)
El módulo "Almacén Móvil" obliga a sacar al servidor de su zona de confort `localhost`. Se requiere una defensa de dos frentes coordinada entre Process IPC e inyección JWT.

### A. Binding de Red Dinámico en Electron Main Process
Por defecto, tanto Next.js como FastAPI arrancan ligados a `127.0.0.1` (solo accesible desde el mismo ordenador). Cuando el usuario activa el "Modo Almacén" en ajustes, el proceso de renderizado de Electron envía una señal IPC al proceso principal:

```typescript
// electron/main.ts (proceso principal)
import { ipcMain } from 'electron';

let networkMode: '127.0.0.1' | '0.0.0.0' = '127.0.0.1';

ipcMain.handle('toggle-local-network', async (_event, enable: boolean) => {
  networkMode = enable ? '0.0.0.0' : '127.0.0.1';
  // Restart the FastAPI/Next.js subprocess with new bind address
  await restartBackendServer({ host: networkMode, port: 3000 });
  return { host: networkMode, localIp: getLocalIpAddress() };
});
```

### B. Circuito de Autorización Zero-Key (QR)
1. **Desktop (Generación):** El ERP genera un JWT firmado con clave secreta local (`HS256`). El payload contiene un scope restrictivo y una expiración de 2 minutos. Se renderiza como QR en pantalla usando `qrcode.react`.
   ```
   Payload: {"sub": "scanner_auth", "scope": "inventory:write", "tenant": "uuid", "exp": <unix_ts+120>}
   ```
2. **Mobile (Escaneo):** La WebApp servida en `/mobile/pair` accede a la cámara con `navigator.mediaDevices.getUserMedia()`, lee el QR, extrae el JWT y lo guarda en `localStorage`. Todas las peticiones posteriores llevan el header `Authorization: Bearer <jwt>`.
3. **Desktop (Confirmación):** Opcionalmente, el ERP muestra un popup: _"Dispositivo 192.168.1.45 solicita acceso al Modo Almacén. ¿Autorizar?"_. Solo tras aprobación, el JWT se marca como activo en una tabla `paired_devices` de PostgreSQL.

### C. Middleware de Validación en FastAPI
```python
# backend/app/api/v1/middleware/scanner_auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

security = HTTPBearer()

async def strict_scanner_auth(
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    """Validates that the incoming request has a valid scanner-scoped JWT.
    Rejects ALL requests that don't have scope='inventory:write'.
    This means a stolen scanner token can NEVER access /api/facturas or /api/rrhh."""
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SCANNER_SECRET_KEY,  # Separate key from main auth
            algorithms=["HS256"]
        )
        if payload.get("scope") != "inventory:write":
            raise HTTPException(status_code=403, detail="Scope mismatch. This token cannot access financial data.")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired QR pairing token. Re-scan required.")

# Usage: Applied ONLY to scanner routes
@router.post("/api/scanner/sku", dependencies=[Depends(strict_scanner_auth)])
async def scan_sku(payload: SKUScanPayload, db: Session = Depends(get_db)):
    """Receives a scanned SKU and updates inventory. 
    This is the ONLY endpoint accessible from paired mobile devices."""
    # ... inventory update logic
```

## 6. Internacionalización Desacoplada (Jurisdiction-As-A-Plugin)

### A. Separación de Conceptos
La internacionalización tiene dos ejes completamente independientes:
- **Eje Visual (UI Locale):** El idioma de los botones, menús y mensajes del sistema. Resuelto exclusivamente en el frontend con `next-intl`.
- **Eje Legal (Jurisdicción Fiscal):** Las reglas tributarias, formatos de factura electrónica y cálculos salariales. Resuelto en el backend mediante RAG filtrado por metadatos.

Esto permite combinaciones como: UI en inglés + Fiscalidad española (un americano con sede en Madrid).

### B. Configuración del Tenant
```python
# Campos relevantes en la tabla Tenant existente:
class Tenant(Base):
    # ... campos existentes ...
    ui_locale = Column(String(10), default="es-ES")    # Consumed by Next.js next-intl
    jurisdiction = Column(String(20), default="ES_TAX") # Consumed by RAG retriever filter
```

### C. Retriever Legal Filtrado (pgvector)
Para impedir que la base de datos de conocimiento mezcle el Derecho Español con el Panameño en la fase de Retrieval de LangChain:
```python
# backend/app/agents/tools/compliance_tools.py
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig

@tool
def query_tax_law(query: str, config: RunnableConfig) -> str:
    """Searches the tenant's jurisdictional legal knowledge base.
    The filter is HARDCODED at query time — the LLM cannot override it."""
    tenant_id = config["configurable"]["tenant_id"]
    jurisdiction_code = get_tenant_jurisdiction(tenant_id)  # Returns e.g., 'MX_TAX'
    
    # Force filtering at SQL/pgvector level. Cross-border contamination is impossible.
    retriever = pgvector_store.as_retriever(
        search_kwargs={
            "k": 5, 
            "filter": {"jurisdiction": {"$eq": jurisdiction_code}} 
        }
    )
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])
```

## 7. Editor de Plantillas Documentales (Electron-Native)
El módulo Legal/Contractual necesita que el usuario pueda gestionar sus plantillas `.docx` de forma visual, insertando variables del ERP (`{{nombre_cliente}}`, `{{salario_bruto}}`) sin conocimientos técnicos. Al correr dentro de Electron, el editor tiene acceso directo al sistema de archivos local, eliminando uploads/downloads por HTTP.

### A. Pipeline de Conversión (docx ↔ HTML ↔ docx)
El flujo completo para editar una plantilla dentro de la aplicación sin salir de Electron:

```
1. Usuario selecciona .docx del disco local
   → Electron Main: dialog.showOpenDialog({ filters: [{ extensions: ['docx'] }] })
   → fs.readFileSync(selectedPath) → Buffer

2. Backend convierte .docx → HTML para renderizado
   → Python (mammoth o python-docx) parsea el Buffer
   → Devuelve HTML preservando estructura (tablas, negritas, listas)
   → Las variables {{variable}} se detectan con regex y se resaltan visualmente

3. Frontend renderiza HTML editable (TipTap o vista previa)
   → El usuario puede ver/editar el contenido
   → Panel lateral muestra variables disponibles agrupadas por módulo

4. Al guardar: HTML editado → .docx
   → Backend reconstruye el .docx usando python-docx/docxtpl
   → Se almacena en /data/tenants/{id}/templates/contracts/
```

### B. Panel Lateral de Variables Disponibles
El frontend expone un catálogo de variables inyectables organizadas por dominio del ERP. Estas se cargan dinámicamente consultando los schemas de los modelos existentes:

```typescript
// frontend/app/components/TemplateVariablePanel.tsx
// Catálogo estático de variables disponibles, agrupadas por módulo del ERP.
// El usuario hace clic en una variable y se inserta en la posición del cursor del editor.

const VARIABLE_CATALOG = {
  cliente: {
    label: "Datos del Cliente",
    icon: "🏢",
    variables: [
      { key: "{{nombre_empresa}}", description: "Razón social del cliente" },
      { key: "{{cif}}", description: "CIF / NIF del cliente" },
      { key: "{{direccion_fiscal}}", description: "Domicilio fiscal completo" },
      { key: "{{email_contacto}}", description: "Email principal de contacto" },
      { key: "{{telefono}}", description: "Teléfono principal" },
    ]
  },
  empleado: {
    label: "Datos del Empleado",
    icon: "👤",
    variables: [
      { key: "{{nombre_trabajador}}", description: "Nombre completo del trabajador" },
      { key: "{{dni}}", description: "DNI / NIE del trabajador" },
      { key: "{{puesto}}", description: "Cargo o puesto de trabajo" },
      { key: "{{salario_bruto}}", description: "Salario bruto anual en €" },
      { key: "{{fecha_incorporacion}}", description: "Fecha de inicio del contrato" },
      { key: "{{tipo_contrato}}", description: "Indefinido / Temporal / Prácticas" },
    ]
  },
  facturacion: {
    label: "Datos de Facturación",
    icon: "💰",
    variables: [
      { key: "{{numero_factura}}", description: "Número secuencial de factura" },
      { key: "{{fecha_emision}}", description: "Fecha de emisión" },
      { key: "{{total_factura}}", description: "Importe total con IVA" },
      { key: "{{base_imponible}}", description: "Base imponible sin IVA" },
    ]
  },
  empresa: {
    label: "Datos de Mi Empresa",
    icon: "🏠",
    variables: [
      { key: "{{mi_empresa_nombre}}", description: "Nombre de tu empresa" },
      { key: "{{mi_empresa_cif}}", description: "CIF de tu empresa" },
      { key: "{{mi_empresa_direccion}}", description: "Dirección fiscal de tu empresa" },
      { key: "{{fecha_actual}}", description: "Fecha del día de generación" },
    ]
  }
};
```

### C. Implementación Escalonada (3 Niveles)
Para no sobredimensionar el esfuerzo, el editor se construye progresivamente:

**V0 — Apertura Nativa (1 día de desarrollo):**
El ERP no edita el `.docx` internamente. Al hacer clic en "Editar Plantilla", Electron invoca `shell.openPath(templatePath)`, que abre el archivo en el Word/LibreOffice instalado en el PC del usuario. El usuario inserta las variables `{{...}}` manualmente en su editor favorito. Al guardar, el ERP detecta el cambio (`fs.watch`) y actualiza la vista previa.

```typescript
// electron/main.ts
import { shell } from 'electron';
ipcMain.handle('open-template-native', async (_event, filePath: string) => {
  await shell.openPath(filePath); // Opens in default .docx handler (Word, LibreOffice)
});
```

**V1 — Vista Previa + Panel de Variables (1 semana de desarrollo):**
El backend convierte el `.docx` a HTML usando `mammoth` (Python). El frontend muestra una vista previa de solo lectura junto al panel lateral de variables. El usuario no edita el HTML directamente, pero puede copiar las etiquetas `{{variable}}` desde el panel, abrir el `.docx` en Word (botón V0), pegarlas y guardar. La vista previa se actualiza automáticamente.

```python
# backend/app/services/docx_preview.py
import mammoth
import re

def docx_to_preview_html(docx_path: str) -> dict:
    """Converts a .docx to HTML and extracts detected variables."""
    with open(docx_path, "rb") as f:
        result = mammoth.convert_to_html(f)
    
    html = result.value
    # Detect all {{variable}} patterns and highlight them
    variables_found = re.findall(r'\{\{(\w+)\}\}', html)
    highlighted_html = re.sub(
        r'(\{\{\w+\}\})',
        r'<span class="bg-yellow-200 text-yellow-800 font-mono px-1 rounded">\1</span>',
        html
    )
    return {
        "html": highlighted_html,
        "variables_detected": list(set(variables_found)),
        "warnings": result.messages  # Conversion warnings (unsupported features, etc.)
    }
```

**V2 — Editor WYSIWYG Completo con TipTap (2-3 semanas de desarrollo):**
Se integra TipTap (basado en ProseMirror) como editor de texto enriquecido embebido en la vista de plantillas. El usuario puede editar el contenido directamente en el navegador: cambiar textos, insertar variables con un botón dedicado del toolbar, ajustar formato (negritas, tablas). Al guardar, el HTML editado se convierte de vuelta a `.docx` usando `python-docx` en el backend.

> [!IMPORTANT]
> **Limitación conocida de la conversión HTML → docx:** La reconversión desde HTML editado pierde inevitablemente algunos estilos complejos del Word original (márgenes exactos, saltos de página personalizados, marcas de agua). Se recomienda que el usuario mantenga siempre el `.docx` original como "plantilla maestra" y use el editor web solo para ajustes menores y previsualización de variables. Para ediciones estructurales profundas, el botón "Abrir en Word" (V0) sigue disponible.

## 8. Feed de Actividad Unificado (Activity Timeline)
Cada herramienta (Tool) del ERP, al completar una acción significativa, inserta una entrada en lenguaje natural en un log cronológico consultable por el frontend. Es el "pulso" de la empresa virtual.

### A. Modelo de Datos
```python
# backend/app/models/activity_feed.py
class ActivityEntry(Base):
    """Append-only log. Each row represents one meaningful action
    completed by an AI employee. Written by tools, read by the dashboard."""
    __tablename__ = "activity_feed"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    employee_id = Column(UUID, ForeignKey("ai_employees.id"), nullable=True)  # Null = system-level event
    task_id = Column(UUID, nullable=True)               # Link to originating task (optional traceability)
    category = Column(String(30), nullable=False)        # "billing", "hr", "inventory", "crm", "system"
    icon = Column(String(10), default="📋")              # Emoji for quick visual scanning in the UI
    message = Column(Text, nullable=False)               # Human-readable: "He enviado 3 recordatorios de cobro..."
    metadata_json = Column(JSON, nullable=True)          # Optional structured data (invoice IDs, amounts, etc.)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
```

### B. Helper de Escritura (Usado por cualquier Tool)
Cada Tool del `TOOL_REGISTRY` puede llamar a este helper al finalizar su ejecución exitosa. El mensaje debe estar redactado en primera persona desde la perspectiva del empleado virtual.

```python
# backend/app/services/activity_service.py
from backend.app.models.activity_feed import ActivityEntry

def log_activity(
    db: Session,
    tenant_id: str,
    employee_id: str,
    category: str,
    message: str,
    icon: str = "📋",
    task_id: str = None,
    metadata: dict = None
):
    """Writes a single activity entry. Called from inside tools after successful execution.
    
    Example usage inside a billing tool:
        log_activity(
            db=db,
            tenant_id=tenant_id,
            employee_id=employee_id,
            category="billing",
            icon="📧",
            message="He enviado recordatorio de cobro a Acme S.L. "
                    "Factura F-2026-042 (1.250,00€), vencida hace 15 días.",
            metadata={"invoice_id": "uuid-...", "client": "Acme S.L.", "amount": 1250.00}
        )
    """
    entry = ActivityEntry(
        tenant_id=tenant_id,
        employee_id=employee_id,
        task_id=task_id,
        category=category,
        icon=icon,
        message=message,
        metadata_json=metadata
    )
    db.add(entry)
    # NOTE: do NOT call db.commit() here. In batch operations (e.g. sending 50
    # reminders) calling commit() per log entry causes 50 round-trips to PostgreSQL.
    # The caller (tool or LangGraph node) owns the transaction and commits once
    # after all work is done. log_activity only stages the entry.
```

### C. Endpoint de Lectura (FastAPI)
El frontend consume este feed paginado para renderizar el Timeline en la pantalla principal o en la ficha de cada empleado.

```python
# backend/app/api/v1/routes/activity.py
@router.get("/api/v1/activity")
async def get_activity_feed(
    tenant_id: str = Depends(get_current_tenant),
    employee_id: str = None,       # Optional: filter by specific employee
    category: str = None,          # Optional: filter by domain ("billing", "hr")
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Returns the activity feed for the tenant, optionally filtered.
    Used by:
      - Dashboard home page (all employees, last 24h)
      - Employee profile page (single employee, all time)
    """
    query = db.query(ActivityEntry).filter(
        ActivityEntry.tenant_id == tenant_id
    ).order_by(ActivityEntry.created_at.desc())
    
    if employee_id:
        query = query.filter(ActivityEntry.employee_id == employee_id)
    if category:
        query = query.filter(ActivityEntry.category == category)
    
    entries = query.offset(offset).limit(limit).all()
    return [
        {
            "id": str(e.id),
            "employee_id": str(e.employee_id),
            "icon": e.icon,
            "message": e.message,
            "category": e.category,
            "metadata": e.metadata_json,
            "created_at": e.created_at.isoformat()
        }
        for e in entries
    ]
```
