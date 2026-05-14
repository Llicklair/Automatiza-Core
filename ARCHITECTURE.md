# AutomatizaPyme — Arquitectura Limpia & Principios de Código

> Reglas no negociables para mantener el proyecto escalable conforme crece. Basadas en la estructura real del código existente.

---

## 1. Capas del sistema — Fronteras estrictas

```
┌─────────────────────────────────────────────┐
│  Frontend (Next.js)                         │  ← solo habla con /api/v1/*
│  src/lib/api/         ← único punto de acceso al backend
└────────────────────┬────────────────────────┘
                     │ HTTP
┌────────────────────▼────────────────────────┐
│  Routes  (api/v1/routes/*.py)               │  ← valida input, responde HTTP
│  Schemas (api/v1/schemas/*.py)              │  ← Pydantic: in/out de cada ruta
└────────────────────┬────────────────────────┘
                     │ llama a
┌────────────────────▼────────────────────────┐
│  Services  (services/*.py)  [OPCIONAL]      │  ← lógica de negocio reutilizable
│                                             │     que NO pertenece a un agente
└────────────────────┬────────────────────────┘
                     │ llama a
┌────────────────────▼────────────────────────┐
│  Agents  (agents/<domain>/agent.py)         │  ← toda la IA vive aquí
│  Tools   (agents/<domain>/tools.py)         │  ← herramientas declaradas al LLM
│  _tools  (agents/<domain>/_*.py)            │  ← implementación privada
│  Prompts (agents/<domain>/prompts.py)       │  ← strings de sistema separados
└────────────────────┬────────────────────────┘
                     │ accede a
┌────────────────────▼────────────────────────┐
│  DB Models  (db/models/<domain>.py)         │  ← SQLAlchemy ORM, solo aquí
│  DB Session (db/session.py)                 │  ← get_db() inyectado, no global
└─────────────────────────────────────────────┘
```

**Regla**: Las capas solo se comunican hacia abajo. Una ruta nunca importa un modelo de BD directamente. Un agente nunca importa una ruta.

---

## 2. Contrato del módulo agente

Cada agente debe respetar esta estructura. Sin excepciones.

```
agents/
└── <domain>/
    ├── __init__.py       ← exporta solo: run_agent()
    ├── agent.py          ← LangGraph/LangChain graph + run_agent(input, tenant_id) → AgentResult
    ├── tools.py          ← lista de tools declaradas al LLM (solo @tool + docstring)
    ├── prompts.py        ← SYSTEM_PROMPT y constantes de texto. Nada de lógica.
    └── _*.py             ← implementación privada. Prefijo _ = no importar desde fuera.
```

### Firma obligatoria de `run_agent`

```python
async def run_agent(
    instruction: str,
    tenant_id: int,
    db: AsyncSession,
    context: dict | None = None,
) -> AgentResult:
    ...
```

```python
# agents/base.py — usar siempre este tipo de retorno
class AgentResult(BaseModel):
    success: bool
    message: str           # respuesta legible para el usuario
    data: dict | None = None
    error: str | None = None
```

**Regla**: `run_agent` es la única función pública de cada agente. Los `_tools` son detalles de implementación. Nada externo los importa directamente.

---

## 3. Aislamiento entre agentes — Prohibido el acoplamiento directo

```python
# ❌ NUNCA: un agente importando herramientas de otro agente
from app.agents.billing._invoice_tools import create_invoice
from app.agents.hr._employee_tools import get_employee

# ✅ CORRECTO: comunicación solo a través del orquestador o servicios compartidos
from app.agents.billing import run_agent as billing_agent
result = await billing_agent(instruction, tenant_id, db)
```

Si dos agentes necesitan el mismo dato, ese dato pertenece a un **servicio compartido** en `services/`:

```python
# services/client_service.py — lógica compartida entre billing y crm
async def get_client_by_name(name: str, tenant_id: int, db: AsyncSession) -> Client | None:
    ...
```

---

## 4. Modelos de BD — Un dominio, un archivo

```python
# ✅ db/models/billing.py → Invoice, InvoiceLine, QuoteLine, RecurringInvoice
# ✅ db/models/hr.py      → Employee, Payroll, Settlement
# ✅ db/models/crm.py     → Client, Opportunity

# ❌ NUNCA: importar modelos de otro dominio dentro de un agente privado (_*.py)
#    Si un _tool de billing necesita Client (crm), usar una query directa o un service.
```

**Regla**: Un modelo de BD nunca importa otro modelo de un dominio diferente. Las relaciones entre dominios se resuelven por ID, no por ORM join entre archivos de modelos distintos.

---

## 5. Rutas — Solo validación y respuesta HTTP

Las rutas no contienen lógica de negocio. Delegan siempre.

```python
# ✅ Ruta limpia
@router.post("/invoices", response_model=InvoiceResponse)
async def create_invoice(
    body: CreateInvoiceRequest,
    db: AsyncSession = Depends(get_db),
    tenant: Tenant = Depends(get_current_tenant),
):
    result = await billing_agent(body.instruction, tenant.id, db)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return result.data

# ❌ Ruta con lógica de negocio — no hacer esto
@router.post("/invoices")
async def create_invoice(body: ..., db: ...):
    invoice = Invoice(...)       # lógica de BD en la ruta
    db.add(invoice)
    await db.commit()
    ...
```

---

## 6. Schemas Pydantic — Separar entrada, salida y dominio interno

```
api/v1/schemas/
├── billing.py    → CreateInvoiceRequest, InvoiceResponse  (HTTP I/O)
├── hr.py         → CreateEmployeeRequest, EmployeeResponse
└── ...

# Los schemas de ruta NUNCA se usan dentro de los agentes.
# Los agentes trabajan con tipos internos o directamente con modelos ORM.
```

---

## 7. Gestión de sesión de BD — Siempre inyectada, nunca global

```python
# ✅ Correcto: inyectada desde la ruta
async def run_agent(instruction: str, tenant_id: int, db: AsyncSession, ...):
    result = await db.execute(select(Invoice).where(...))

# ❌ Incorrecto: sesión creada dentro del agente o herramienta
async def _create_invoice(...):
    async with get_db() as db:   # crea una sesión paralela — rompe transacciones
        ...
```

---

## 8. Motor de condiciones para Workflows

El motor de condiciones evalúa reglas declarativas (JSON dicts) para decidir si un workflow se dispara. Consta de tres módulos en `services/workflow/`:

```
services/workflow/
├── conditions.py          ← evaluador puro/síncrono: AND/OR/NOT + hojas (field/op/value)
├── db_conditions.py       ← pre-fetch: resuelve hojas "provider" consultando BD
└── db_query_providers.py  ← registro de queries seguras por dominio
```

**Condición hoja estándar** (contra contexto temporal o de evento):
```json
{"field": "now_weekday", "op": "lte", "value": 4}
```

**Condición hoja con provider** (consulta BD en tiempo real):
```json
{"provider": "billing.pending_invoice_count", "params": {"status": "pending"}, "op": "gt", "value": 10}
```

**Condición compuesta** (mezcla temporal + BD):
```json
{
  "operator": "AND",
  "conditions": [
    {"field": "now_weekday", "op": "lte", "value": 4},
    {"provider": "billing.pending_invoice_count", "params": {}, "op": "gt", "value": 10}
  ]
}
```

**Flujo de evaluación**:
1. `resolve_db_conditions()` recorre el árbol, ejecuta los providers, inyecta resultados en `context["db"]`
2. `evaluate_conditions()` evalúa el árbol completo contra el contexto enriquecido (síncrono, sin saber de BD)

**Añadir un nuevo provider**: definir la función en `db_query_providers.py` y registrarla en `QUERY_PROVIDERS`. Firma: `async def fn(tenant_id: UUID, db: AsyncSession, params: dict) -> int | float | bool`.

**Reglas**:
- El evaluador (`conditions.py`) es puro — no sabe de BD, agentes ni APScheduler
- Los providers siempre filtran por `tenant_id` y retornan escalares (nunca filas)
- El scheduler solo llama `resolve_db_conditions()` + `evaluate_conditions()` — no contiene lógica condicional propia

---

## 9. Frontend — Un cliente API por dominio, nunca fetch directo

```
frontend/src/lib/api/
├── billing.ts     → createInvoice(), listInvoices(), getInvoice()
├── hr.ts          → createEmployee(), listEmployees()
├── crm.ts         → ...
└── client.ts      → instancia base de axios/fetch con token + tenant
```

```typescript
// ✅ Correcto
import { createInvoice } from '@/lib/api/billing'
const result = await createInvoice({ instruction: '...' })

// ❌ Incorrecto — fetch directo en un componente
const res = await fetch('/api/v1/invoices', { method: 'POST', ... })
```

**Regla**: Los componentes React nunca hacen HTTP directamente. Si un endpoint nuevo no tiene cliente en `lib/api/`, créalo antes de usarlo.

---

## 10. Prompts — Separados del código, versionables

```python
# agents/billing/prompts.py
SYSTEM_PROMPT = """
Eres el agente de facturación de AutomatizaPyme...
"""

INVOICE_CREATION_CONTEXT = """
Cuando crees una factura, siempre verifica que el cliente existe...
"""
```

**Reglas**:
- Ningún string de prompt vive en `agent.py` o `_tools.py`.
- Si el prompt cambia, solo cambia `prompts.py`. El grafo LangGraph no se toca.
- Los prompts no contienen lógica Python — son strings puros.

---

## 11. Manejo de errores — Tipado, no excepciones silenciosas

```python
# ✅ Retornar AgentResult con error
async def run_agent(...) -> AgentResult:
    try:
        invoice = await _create_invoice(...)
        return AgentResult(success=True, message="Factura creada", data=invoice.dict())
    except ClientNotFoundError as e:
        return AgentResult(success=False, error=str(e))

# ❌ Excepciones genéricas que pierden contexto
except Exception as e:
    raise HTTPException(500, "Error interno")
```

**Regla**: Los agentes nunca lanzan excepciones al orquestador. Devuelven `AgentResult(success=False)`. Las excepciones se convierten en errores tipados lo más cerca posible de donde ocurren.

---

## 12. Tests — Qué testear y cómo

| Nivel | Qué cubre | Herramienta |
|-------|-----------|-------------|
| Unit | Lógica pura de `_tools` (cálculos, transformaciones) | pytest, sin BD |
| Integration | `run_agent()` completo contra BD real (PostgreSQL de test) | pytest + asyncio, BD real |
| E2E | Flujo HTTP completo: request → ruta → agente → BD → respuesta | httpx + TestClient |

**Reglas**:
- Los tests de integración usan BD real, nunca mocks de SQLAlchemy.
- Cada uno de los 5 flujos prioritarios del SCOPE.md tiene un test e2e obligatorio.
- Un test que mockea el LLM es válido para unit; para e2e, usa un provider determinista (modo tool-only sin LLM si es posible).

---

## 13. Excepciones conocidas y justificadas

| Excepción | Archivo | Justificación |
|-----------|---------|---------------|
| `services/` importa `agents/` | `services/workflow/_execution.py` | `execute_deterministic_steps` invoca agentes directamente para pasos "reasoning" de workflows híbridos. Es acoplamiento inevitable: el servicio de ejecución de workflows necesita llamar dispatchers. Usa `DISPATCHER_MAP` canónico del orquestador — nunca imports individuales. |
| `AsyncSessionLocal()` dentro de `@tool` y sus helpers privados | `agents/*/tools.py`, `agents/billing/_*.py`, `agents/banking/_*.py` | Los `@tool` de LangChain son invocados por el LLM con args JSON — no pueden recibir `db: AsyncSession` inyectada. Cada tool debe gestionar su propia sesión. Patrón aceptado: **una sesión por función**, abierta con `async with AsyncSessionLocal() as db`. Excepción conocida: `create_invoice` abre 3 sesiones encadenadas (create → load_template → generate_pdf) por limitaciones de reutilización de helpers. |

---

## 14. Lo que está prohibido

| Prohibido | Alternativa |
|----------|-------------|
| Importar `_tools` de otro agente | Usar `run_agent()` del agente destino o extraer a `services/` |
| Lógica de negocio en rutas | Moverla al agente o a `services/` |
| `fetch()` directo en componentes React | Función en `src/lib/api/<domain>.ts` |
| Prompts inline en `agent.py` | Moverlos a `prompts.py` |
| Sesión de BD creada dentro de un tool | Recibir `db: AsyncSession` como parámetro |
| `except Exception: pass` o log sin re-raise | `AgentResult(success=False, error=...)` |
| Un modelo ORM con FK a un modelo de otro dominio (cross-import) | Relación por `tenant_id` + `foreign_key` declarado en el modelo hijo |
| Condiciones de workflow en el job de APScheduler | Delegar a `conditions.py` + `db_conditions.py` (servicios separados) |

---

## 15. Checklist antes de hacer merge

- [ ] ¿El nuevo código respeta las capas del diagrama de la sección 1?
- [ ] ¿El agente modificado sigue el contrato de `run_agent()`?
- [ ] ¿Ningún agente importa `_tools` de otro agente?
- [ ] ¿Las rutas nuevas tienen schema Pydantic de entrada y salida?
- [ ] ¿El frontend usa `src/lib/api/` y no fetch directo?
- [ ] ¿Los prompts están en `prompts.py`?
- [ ] ¿Hay al menos un test de integración para el flujo nuevo?
- [ ] ¿`gitnexus_impact` fue ejecutado para todos los símbolos modificados?

---

## 16. Invariante de centralización de datos (MULTI.2)

> Regla no negociable consensuada en el debate IA-1↔IA-2 sobre AutomatizaPyme
> (`DISCUSION_OTRA_IA.md` §0ter — Ronda 16-19).

**AutomatizaPyme no centraliza datos de negocio del cliente en servidores propios.**

Datos de negocio = facturas, clientes, NIFs, IBANs, importes, nóminas,
contabilidad, contenido de prompts y outputs de agentes. Estos viven
exclusivamente en el equipo del cliente (Postgres local gestionado por el
desktop Electron).

Servicios opcionales del cliente que pueden enviar datos al VPS:

- **Backup remoto Backblaze B2** (opt-in en onboarding, cifrado E2E
  client-side con clave derivada de password del usuario — el servidor
  guarda blobs cifrados que no puede leer).
- **Telemetría técnica** (opt-in, scrubbed con regex bloqueante de
  NIF/IBAN/email/IP, retención 90d eventos / 18m agregados; ver
  `docs/telemetry-data-policy.md`).

Ambos usan proveedores externos que **el cliente puede sustituir** y el
cliente **conserva las claves**. AutomatizaPyme nunca recibe datos del
negocio en plano.

### Implicaciones de diseño

1. **No SaaS cloud puro** — AutomatizaPyme no expondrá nunca un endpoint
   `/api/v1/...` corriendo en infraestructura central que reciba facturas
   de un tenant. La API existe pero corre en el equipo del cliente.
2. **Multi-actor por LAN/VPN del cliente, no por servidor central** —
   modo "Servidor compartido" (MULTI.1, roadmap v1.2) expone el Postgres
   del cliente principal a otros dispositivos vía Tailscale/WireGuard.
   Nunca vía servidor de AutomatizaPyme.
3. **El VPS de AutomatizaPyme solo gestiona licencias** y opcionalmente
   recibe blobs cifrados (backup B2) o eventos scrubbed (telemetría).
   No tiene rutas de lectura de datos de negocio del cliente.

### Cuándo se permite romper este invariante

Solo bajo:

- **Roadmap explícito** firmado en una nueva ronda del debate (no
  decisión unilateral de un dev senior).
- **Decisión escrita en `DISCUSION_OTRA_IA.md`** con justificación,
  alternativas evaluadas y plan de migración para clientes existentes.
- **Cambio de copy de marketing** sincronizado — la frase *"Tu base de
  datos vive en tu equipo. Nunca enviamos tus datos de negocio sin tu
  permiso explícito."* (A.9bis) debe actualizarse o este invariante se
  convierte en publicidad engañosa.
