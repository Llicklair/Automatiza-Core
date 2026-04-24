# AutomatizaPyme — Scope & Objetivos Reales

> Documento de alineación basado en análisis exhaustivo del código fuente. Define honestamente qué existe implementado, qué está incompleto, y qué debe funcionar impecablemente end-to-end.
>
> _Última revisión: 2026-04-24 (v2) — actualizado tras refactorización arquitectural + audit frontend completo._

---

## 0. Qué es y qué puede hacer este sistema

AutomatizaPyme es un ERP con inteligencia artificial integrada para pequeñas y medianas empresas españolas. En lugar de navegar por menús y formularios, el usuario escribe en lenguaje natural — "crea una factura para García S.L. por 1.200€" — y el sistema lo ejecuta.

### Lo que SÍ puede hacer hoy

**Facturación y ventas**
El sistema puede crear facturas, albaranes, presupuestos y pedidos a partir de una instrucción de texto. Calcula totales con IVA, asigna número correlativo, vincula al cliente en base de datos y deja la factura visible en la UI sin intervención manual. También genera facturas recurrentes de forma automática según la periodicidad configurada.

**Recursos Humanos**
Puede dar de alta empleados, calcular nóminas, registrar jornadas y generar liquidaciones. Entiende instrucciones como "calcula la nómina de marzo de todos los empleados" y escribe los resultados en la base de datos.

**CRM y clientes**
Gestiona el ciclo de ventas: crea clientes, registra oportunidades, anota actividades y lleva el pipeline. También gestiona reservas y reuniones.

**Banca y contabilidad**
Permite cargar extractos bancarios, ver saldos, listar movimientos y hacer conciliación. Genera informes financieros (pérdidas y ganancias, balance, cashflow) consultando directamente la base de datos.

**Documentos e inteligencia documental (RAG)**
El usuario puede subir contratos, facturas en PDF o cualquier documento. El sistema los indexa con embeddings vectoriales (pgvector) y después puede responder preguntas sobre su contenido: "¿cuándo vence el contrato con Telefónica?" extrae la fecha directamente del PDF.

**Correo electrónico**
Si el tenant configura Gmail, Outlook o SMTP, el sistema puede enviar correos, leer la bandeja de entrada y ejecutar instrucciones como "envía un resumen de facturas pendientes a contabilidad@empresa.com". Sin credenciales configuradas, funciona en modo demo.

**Automatizaciones (workflows)**
El usuario puede programar tareas recurrentes con lenguaje natural: "cada lunes, envíame un resumen de facturas pendientes". El sistema guarda el workflow, lo ejecuta automáticamente según el cron definido, y registra cada ejecución. Los workflows soportan condiciones lógicas (AND, OR, NOT, umbrales) y condiciones basadas en datos en tiempo real: al momento del disparo, pueden consultar la BD ("ejecutar solo si hay más de 10 facturas pendientes" o "solo si el total impagado supera 5.000€"). Los providers disponibles cubren billing y RRHH, y son extensibles.

**Reclutamiento**
Gestiona posiciones abiertas, recibe CVs, hace seguimiento de candidatos y permite al agente analizar perfiles.

**Compliance y asesoría fiscal**
Consulta el BOE automáticamente, avisa de vencimientos fiscales (IVA, IRPF, etc.) y responde preguntas de asesoría basándose en documentos indexados.

---

### Lo que NO puede hacer (limitaciones reales)

**Sin integración bancaria real (Open Banking / PSD2)**
Los saldos y movimientos bancarios se alimentan de extractos importados manualmente (.csv, .ofx). No hay conexión directa con ningún banco español. Para eso se necesitaría integrar la API de un proveedor como Belvo o Salt Edge, que está fuera del scope v1.

**Sin firma electrónica**
Los contratos y documentos generados no pueden firmarse digitalmente desde la plataforma. No hay integración con DocuSign, Autofirma ni similar.

**Sin presentación automática a la AEAT**
El sistema calcula el IVA, el IRPF y genera los modelos fiscales, pero no los envía a la Agencia Tributaria. Eso requeriría certificado digital del contribuyente e integración con la sede electrónica de la AEAT.

**Una empresa por instalación**
La versión de escritorio está diseñada para que cada empresa instale su propia copia con su propia base de datos local. No hay un modo "multitenant en la nube" donde una empresa pueda gestionar múltiples sociedades desde una sola cuenta.

**Los datos no salen del ordenador del cliente**
Por diseño, todos los datos del ERP (facturas, empleados, clientes) se almacenan en la base de datos PostgreSQL local. No hay sincronización con ningún servidor externo. Esto es una decisión deliberada de privacidad, no una limitación técnica.

---

## 1. Qué existe REALMENTE en el código

### Agentes completamente implementados

| Agente | Archivo | Herramientas reales implementadas | BD conectada | Ruta API |
|--------|---------|-----------------------------------|--------------|----------|
| **Billing** | `agents/billing/agent.py` | create/query/write invoice, PDF, albaranes, quotelines | Invoice, InvoiceLine, DeliveryNote, QuoteLine, RecurringInvoice | ✅ `/api/v1/invoices/*` `/api/v1/albaranes/*` |
| **HR** | `agents/hr/agent.py` | employee mgmt, payroll calc, liquidaciones, jornada | Employee, Payroll, Settlement, JornadaRecord | ✅ `/api/v1/hr/*` |
| **CRM** | `agents/crm/agent.py` | clientes, oportunidades, actividades | Client, Opportunity, Activity | ✅ `/api/v1/crm/*` |
| **Banking** | `agents/banking/agent.py` | check_balances, list_transactions, financial_summary, reconcile | BankTransaction, accounts (accounting.py) | ✅ `/api/v1/banking/*` `/api/v1/accounting/*` |
| **Compliance** | `agents/compliance/agent.py` | fiscal_deadlines, BOE scraper, document search | DocumentEmbedding, Tenant | ✅ `/api/v1/advisory/*` |
| **Documents** | `agents/documents/agent.py` | upload, search, retrieval | TenantDocument | ✅ `/api/v1/documents/*` |
| **Recruitment** | `agents/recruitment/agent.py` | posiciones, candidatos, tracking | RecruitmentPosition, Candidate | ✅ `/api/v1/recruitment/*` |
| **RAG** | `agents/rag/agent.py` | search_documents (vector, top_k=5) | DocumentEmbedding (pgvector real) | Interno (sin ruta propia) |
| **Workflow** | `agents/workflow/agent.py` | workflow_execution, task_planning | Workflow, WorkflowExecution, DomainEvent | ✅ `/api/v1/workflows/*` |

### Orquestador — implementado con LangGraph completo

- **Archivo**: `agents/orchestrator/_core.py`
- **Arquitectura real**: máquina de estados LangGraph con nodos: `classifier → dispatcher → validator → summarizer`
- **Clasificador de intención**: `classifier.py` — enruta a los 10+ agentes especializados
- **Dispatcher por dominio**: `banking.py`, `billing.py`, `compliance.py`, `crm.py`, `documents.py`, `hr.py`, `email.py`, `custom.py`, `misc.py`, `reports.py`
- **Entrada principal**: `POST /api/v1/ai_employees/instruct`

### Scheduler / Automatizaciones — APScheduler real

- **Archivo**: `services/scheduler.py` — `AsyncIOScheduler` registrado en lifespan de FastAPI
- **Jobs registrados al arrancar**:
  - `check_scheduled_workflows` — cada minuto
  - `process_recurring_invoices` — diario 8:00 AM
  - `cleanup_stuck_executions` — cada 10 minutos
  - `catchup_missed_workflows` — arranque diferido
  - `bootstrap_employee_heartbeats` — arranque diferido

### Worker / Task system

- `workers/tasks_orchestrator.py` — ejecuta LangGraph en background
- `workers/tasks_scheduler.py` — integración APScheduler
- `workers/tasks_node_engine.py` — motor de ejecución de nodos

### Modelos de BD reales (SQLAlchemy async)

`billing.py`, `accounting.py`, `hr.py`, `crm.py`, `embeddings.py`, `workflows.py`, `auth.py` — todos con ORM completo y soporte multi-tenant.

---

## 2. Qué está PARCIALMENTE implementado (código existe, integración incompleta)

| Componente | Estado real |
|-----------|------------|
| **Email agent** | ✅ Rutas expuestas: `POST /messaging/email/send`, `POST /messaging/email/instruct`, `GET /messaging/email/status` |
| **Excel agent** | Herramientas completas (`export_erp_data`, `import_excel`, `modify_excel`). **Sin ruta API wired** |
| **Marketing agent** | Código existe (campañas, contenido). **Sin ruta API encontrada** |
| **Frontend pages** | `/ventas/facturas`, `/rrhh/empleados`, `/rrhh/documentos` — ✅ conectadas al API. Sin conectar: `/ai-employees/`, `/email/`, `/excel/` (Fase 1.5) |

---

## 3. Qué NO puede hacer (limitaciones reales, no de diseño futuro)

| Limitación | Razón real |
|-----------|-----------|
| **Integración bancaria real (PSD2/Open Banking)** | Solo carga manual de extractos — no hay OAuth bancario |
| **Firma electrónica** | No implementado |
| **Envío/recepción de email desde UI** | Ruta API expuesta; falta página frontend `/email/` (Fase 1.5) |
| **Exportación Excel desde chat** | El agente excel existe pero sin ruta wired ni página frontend |
| **Presentación automática AEAT** | Sin integración con APIs fiscales oficiales |
| **Multi-empresa por instalación** | Local-first: una empresa = una instalación |
| **Sincronización cloud de datos ERP** | Por diseño: datos nunca salen del cliente |
| **Flujos de workflow con condiciones complejas** | ✅ Resuelto: evaluador de condiciones lógicas (AND/OR/NOT/threshold) + consultas a BD en tiempo real via query providers |

---

## 4. Qué debe funcionar IMPECABLEMENTE end-to-end

> **Hacer 5 flujos perfectos vale más que 15 flujos rotos.**
> Cualquier nueva funcionalidad solo entra si estos 5 flujos siguen funcionando.

### 🎯 Flujo 1 — Factura desde lenguaje natural
```
Usuario: "Crea una factura para Cliente X por 1500€ de consultoría"
→ Orquestador clasifica → billing agent → valida cliente en BD →
→ crea Invoice + InvoiceLines → responde con número de factura →
→ visible en UI /facturas
```
**Criterio**: La factura existe en BD con número correlativo, estado correcto, aparece en UI sin recarga manual.

---

### 🎯 Flujo 2 — Consulta de estado financiero
```
Usuario: "¿Cuánto hemos facturado este mes y qué facturas están pendientes de cobro?"
→ Orquestador → billing agent → query BD → agrega totales → responde
```
**Criterio**: Los números coinciden con un SELECT manual en PostgreSQL.

---

### 🎯 Flujo 3 — Alta de empleado
```
Usuario: "Da de alta a María García, contrato indefinido, 2200€/mes, inicio 1 junio"
→ Orquestador → HR agent → Employee + contrato en BD → confirma en chat → aparece en /hr
```
**Criterio**: Empleado en BD con todos los campos requeridos, sin errores de validación.

---

### 🎯 Flujo 4 — Workflow recurrente end-to-end
```
Usuario: "Cada lunes envíame un resumen de facturas pendientes"
→ Workflow guardado en BD → APScheduler programa job →
→ lunes: billing agent genera resumen → email agent envía →
→ WorkflowExecution registrado con status: success
```
**Criterio**: Email recibido, log en BD con `status: success`, sin intervención humana.
> ⚠️ Este flujo requiere primero exponer la ruta del email agent (ver sección 2).

---

### 🎯 Flujo 5 — Consulta documental (RAG)
```
Usuario sube contrato PDF → "¿Cuándo vence el contrato con Proveedor X?"
→ Documents agent indexa → RAG busca chunks (pgvector) → responde con fecha
```
**Criterio**: Fecha extraída del PDF sin alucinaciones. Verificable comparando con el documento.

---

## 5. Deuda técnica bloqueante (para los 5 flujos)

| Deuda | Impacto | Flujo afectado | Estado |
|------|---------|---------------|--------|
| Email agent sin ruta API | Workflows que envían emails no completan el ciclo | Flujo 4 | ✅ Resuelto |
| Frontend pages desconectadas | Usuario ve UI vacía aunque BD tiene datos | Flujos 1, 3 | ✅ Resuelto (audit confirmó conexión) |
| Excel agent sin ruta API | Exportación no accesible desde chat | — | ⚠️ Fase 1.5 |
| Condiciones de workflow solo time-based | Automatizaciones complejas (umbral de facturación, etc.) imposibles | Flujo 4 (extendido) | ⚠️ Fase 2 |

---

## 6. Estado: real vs. objetivo

| Flujo | Estado código | Frontend | Objetivo |
|-------|--------------|----------|----------|
| Factura desde chat | ✅ Implementado | ✅ /ventas/facturas conectado | ✅ Impecable |
| Consulta financiera | ✅ Implementado | ✅ N/A (respuesta en chat) | ✅ Impecable |
| Alta de empleado | ✅ Implementado | ✅ /rrhh/empleados conectado | ✅ Impecable |
| Workflow recurrente | ✅ Email ruta expuesta | N/A | ✅ Impecable |
| RAG documental | ✅ Implementado | ✅ /documentos conectado | ✅ Impecable (requiere pgvector en prod) |
| Email desde chat | ✅ Agente + ruta ok | ❌ Página /email sin conectar | Fase 1.5 |
| Excel desde chat | ⚠️ Agente ok, ruta falta | ❌ Página /excel sin conectar | Fase 1.5 |
| Workflows con condiciones complejas | ❌ Solo time-based | ❌ | Fase 2 |
| Integración bancaria PSD2 | ❌ Solo manual | ❌ | Fuera de scope v1 |
| Presentación AEAT | ❌ | ❌ | Fuera de scope v1 |
