# Protocolo de prueba del sistema de agentes

Manual operativo evergreen para probar el sistema end-to-end. No tiene historial de sesiones; describe cómo se prueba HOY y qué hay que ir cubriendo.

---

## Filosofía

El sistema tiene **dos mecanismos de entrada** según el README, que se prueban de forma distinta:

- 🔵 **TAREAS** (`/tareas`) — instrucción puntual del usuario al sistema. Una vez. Ejemplo: *"crea una factura para X"*. Se persiste en `Task`.
- 🟢 **AUTOMATIZACIONES** (`/automatizaciones`) — regla persistente que se dispara sola. Ejemplo: *"cada lunes a las 9 envía resumen de ventas"*. Se persiste en `Workflow`.

> Una automatización **puede generar tareas**. Una tarea **jamás crea automatizaciones**.

Cada vez que se toque código de tools/agentes/dispatchers/parser, hay que validar **ambos** mecanismos. Una tarea funcional no garantiza que el mismo flujo funcione disparado por un workflow.

---

## Flujo de una iteración

1. **Editar código** en el repo dev: `c:\Users\Marcos\Desktop\automatizacion de empresas\Automatiza-pyme-main\`
2. **Commit + push** → `git push origin master`
3. **Sincronizar al exe instalado**: `cd desktop && npm run sync`
4. **Cerrar Electron completo** (también desde la bandeja del sistema)
5. **Reabrir Electron** (backend arranca con código nuevo)
6. **Verificar uptime**: `(Invoke-RestMethod -Uri http://localhost:8080/health).uptime_seconds` < 60s
7. **Probar** según el mecanismo (TAREAS o AUTOMATIZACIONES — ver más abajo)
8. **Verificar resultado** en BD (ver sección de inspección)

> **El paso más fácil de olvidar**: confirmar que el backend reinició realmente. Si el uptime es alto, las pruebas son contra código viejo.

---

## Credenciales locales (solo desarrollo)

```
email:    marcosreciosanchez@gmail.com
password: marcos3448
base URL: http://localhost:8080/api/v1
health:   http://localhost:8080/health
```

---

## IDs de los empleados IA built-in + custom

Listado vivo (puede cambiar tras `seed_builtin` o creaciones manuales). Refrescar con `GET /api/v1/ai-employees`.

| Nombre              | Rol / Dominio                | UUID |
|---------------------|------------------------------|------|
| Ana Valdés          | Directora Financiera (billing)   | `0f7c65d8-88e6-436d-8207-b2c2152e2e81` |
| Carlos Herrero      | Responsable de RRHH (hr)         | `497a24a0-01c4-49ce-b87d-c32d3116d09c` |
| Sofía Martín        | Asistente de Comunicación (email)| `f7a0a61f-83cd-4b15-832d-12908c65487c` |
| Javier Romero       | Responsable Comercial (crm)      | `202c1d33-d7c4-4144-8bdc-4d9a44c6d5d0` |
| Miguel Torres       | Responsable de Banca (banking)   | `6977404a-250b-41f2-9f29-dec54a05edd3` |
| Laura Jiménez       | Asesora Fiscal (compliance)      | `c19b814d-e0b6-4c52-b6d7-9978d715d028` |
| Elena Ruiz          | Gestora de Documentación         | `57389922-7ea7-4f33-a5fc-9c2e4ddf8804` |
| David Sánchez       | Analista de Datos (excel)        | `7891183c-c196-46ec-a00e-2ff0294caa55` |
| **Marcos Recio**    | **CTO custom (domain=custom)**   | `6b1d51ac-b2c2-4c97-95b2-7bbd037a14ad` |

---

## 🔵 Probar TAREAS (acción puntual)

Endpoint: `POST /api/v1/ai-employees/{employee_id}/instruct`
Devuelve `{ task_id, status:"queued" }`.
Polling: `GET /api/v1/tasks/{task_id}` hasta que `status ∈ {done, failed, completed, success}`.

### Plantilla PowerShell

Tres claves importantes:
- **Body en bytes UTF-8** (sin esto, las tildes y `ñ` rompen el body con `400 parsing error`).
- **Content-Type con `charset=utf-8`**.
- **Timeout de polling ≥ 360s** para informes largos.

```powershell
$ErrorActionPreference = "Stop"
$base = "http://localhost:8080/api/v1"
$loginBody = '{"email":"marcosreciosanchez@gmail.com","password":"marcos3448"}'
$login = Invoke-RestMethod -Uri "$base/auth/login" -Method POST `
    -Body $loginBody -ContentType "application/json; charset=utf-8"
$h = @{ Authorization = "Bearer $($login.access_token)" }

$employeeId = "<uuid>"
$msg        = "<instrucción>"

$payload = @{ message = $msg } | ConvertTo-Json -Compress
$bytes   = [System.Text.Encoding]::UTF8.GetBytes($payload)

$resp = Invoke-RestMethod -Uri "$base/ai-employees/$employeeId/instruct" `
    -Method POST -Body $bytes -Headers $h `
    -ContentType "application/json; charset=utf-8" -TimeoutSec 30
$taskId = $resp.task_id

$deadline = (Get-Date).AddSeconds(420)
$final = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    try { $r = Invoke-RestMethod -Uri "$base/tasks/$taskId" -Headers $h -TimeoutSec 15 } catch { continue }
    if ($r.status -in @("done","failed","completed","success")) { $final = $r; break }
}
$final | ConvertTo-Json -Depth 5
```

> **Evitar here-docs anidados** en PowerShell — se rompen al embeberse en el tool Bash. Si necesitas SQL/Python complejo, escribe a `C:\Users\Marcos\Desktop\<temp>.py` y lo ejecutas.

### Catálogo de tools a cubrir (un prompt por tool)

#### Billing — Ana Valdés (`0f7c65d8-...`)
- [ ] `list_invoices` → *"Lista las facturas de los últimos 30 días con su estado."*
- [ ] `search_client` → *"Busca el cliente con NIF B12345678"*
- [ ] `create_invoice` → *"Crea una factura para García S.L. por 1500€ de consultoría"*
- [ ] `update_invoice_status` → *"Marca como pagada la factura más reciente de García S.L."*
- [ ] `update_invoice` → *"Cambia el concepto de la última factura draft a 'mantenimiento mensual'"*
- [ ] `send_invoice_by_email` → *"Envía la última factura de García S.L. a contacto@garcia.es"*
- [ ] `list_albaranes` / `create_albaran` → *"Lista albaranes pendientes / Crea albarán para Cliente X"*
- [ ] **PDF**: *"Genera un informe en PDF de facturación del último trimestre"* (debe usar `create_pdf_text_report`)

#### HR — Carlos Herrero (`497a24a0-...`)
- [ ] `list_employees` → *"Lista los empleados activos con NIF y salario base"*
- [ ] `create_employee` → *"Crea un empleado: nombre Juan Pérez, NIF 12345678Z, salario mensual 2500€"*
- [ ] `calculate_and_create_payroll` → *"Genera la nómina de febrero 2026 para el NIF 12345678Z"*
- [ ] `generate_all_payrolls` → *"Genera las nóminas de febrero 2026 para todos los empleados"*
- [ ] `list_payrolls` → *"Lista las nóminas pendientes de aprobar"*
- [ ] `update_payroll` → *"Modifica la nómina X subiendo el bono a 200€"*
- [ ] `approve_payroll` → *"Aprueba todas las nóminas de febrero"*
- [ ] **PDF**: *"Genera un informe en PDF de plantilla y costes salariales"*

#### CRM — Javier Romero (`202c1d33-...`)
- [ ] `list_opportunities` → *"Lista oportunidades en fase qualified"*
- [ ] `create_opportunity` → *"Crea oportunidad para cliente NIF X: software ERP, valor 12000€"*
- [ ] `update_opportunity_stage` → *"Mueve la última oportunidad qualified a won"*
- [ ] `qualify_leads` → *"Cualifica los leads pendientes y dame el ranking"*
- [ ] `create_client` → *"Crea cliente: 'Innovaciones SL', NIF B98765432, contacto pedro@innov.es"*
- [ ] **PDF**: *"Informe en PDF del pipeline comercial actual"*

#### Banking — Miguel Torres (`6977404a-...`)
- [ ] `check_balances` → *"Saldos actuales de todas las cuentas"*
- [ ] `list_transactions` → *"Movimientos de los últimos 7 días"*
- [ ] `financial_summary` → *"Resumen financiero del último mes"*
- [ ] `reconcile_transactions` → *"Reconcilia los movimientos pendientes"*
- [ ] **PDF**: *"Informe en PDF de tesorería del trimestre"*

#### Compliance — Laura Jiménez (`c19b814d-...`)
- [ ] `check_fiscal_deadlines` → *"¿Qué vencimientos fiscales tengo en los próximos 30 días?"*
- [ ] `check_boe_news` → *"Novedades del BOE relevantes para mi empresa"*
- [ ] `fiscal_query` → *"¿Cómo afecta el módulo 303 a mi facturación trimestral?"*
- [ ] **PDF**: *"Informe fiscal en PDF del trimestre"*

#### Documents — Elena Ruiz (`57389922-...`)
- [ ] `classify_document` → *"Clasifica el documento ID X"* (necesita doc subido previamente)
- [ ] `search_documents_semantic` → *"Busca contratos firmados en 2024"*
- [ ] `create_document` (compartida) → *"Crea una nota txt con la lista de pendientes"*
- [ ] `list_tenant_documents` → *"Lista documentos en categoría 'facturas'"*
- [ ] `get_document_content` → *"Lee el contenido del documento más reciente"*
- [ ] `update_existing_document` → *"Añade al final del doc X la línea 'revisado'"*

#### Excel — David Sánchez (`7891183c-...`)
- [ ] `list_available_datasets` → *"Qué datasets puedo exportar"*
- [ ] `export_erp_data` → *"Exporta a Excel todas las facturas del último mes"*
- [ ] `import_excel` → *"Importa los datos del Excel uploaded_X"*
- [ ] `read_excel` / `modify_excel` → *"Lee la hoja 1 del último Excel y cambia la columna B"*

#### Email — Sofía Martín (`f7a0a61f-...`)
- [ ] `check_inbox` → *"Mira la bandeja de entrada"*
- [ ] `check_unread` → *"¿Cuántos emails sin leer tengo?"*
- [ ] `send_email` → *"Envía un email a contacto@cliente.es con asunto 'Pedido confirmado'"*

#### RAG (no tiene empleado asignado por defecto)
- [ ] `search_documents` → invocable vía cualquier agente, *"Busca en mis documentos información sobre presupuestos"*
- [ ] `answer_from_documents` → *"¿Qué dice mi contrato de alquiler sobre la rescisión?"*

#### Marketing
- [ ] `get_product_catalog` → *"Lista mi catálogo de productos"*

#### Recruitment
- [ ] `create_position` / `list_positions` → *"Crea posición para Backend Sr / Lista posiciones abiertas"*
- [ ] `process_cv` → tras subir CV, *"Procesa el CV X contra la posición Y"*
- [ ] `list_candidates` / `update_candidate_status` → *"Lista candidatos shortlisted"*

#### Tools de informes (compartidas, llaman cualquier agente)
- [ ] `create_pdf_text_report` → *(disparar con cualquier prompt que pida un informe PDF)*
- [ ] `create_pdf_report` → JSON estructurado con KPIs/tablas/charts (solo viable con providers con function calling nativo, NO con `claude_code`)

#### Caso negativo
- [ ] *"Apunta en una nota txt que tengo reunión mañana a las 10"* → debe usar `create_document`, **no** `create_pdf_*`. Si abusa, el system prompt necesita reforzar la diferencia.

---

## 🟢 Probar AUTOMATIZACIONES (regla persistente)

Endpoint para crear desde lenguaje natural:
```
POST /api/v1/workflows/parse-nl
Body: { "text": "<descripción de la regla>" }
```

Devuelve un payload listo para abrir el modal del editor con nodos pre-rellenados (mode reasoning) o pasos compilados (mode deterministic).

Para crear el workflow definitivo:
```
POST /api/v1/workflows/   { name, trigger_type, trigger_config, action_type, action_config, execution_mode }
```

### Tipos de trigger a cubrir

#### A. Trigger por TIEMPO (cron)
- [ ] *"Cada lunes a las 9 envía un resumen de ventas a comercial@empresa.es"*
- [ ] *"Cada primer día del mes genera un informe contable y guárdalo"*
- [ ] *"Cada hora reconcilia los movimientos bancarios pendientes"*
- Verificar:
  - El cron se parsea correctamente (`workflow.trigger_config.cron`).
  - APScheduler lo dispara en el siguiente tick.
  - Crea fila en `WorkflowExecution` con `status='running'`.
  - Si la acción dispara una task, se crea Task hija con `additional_metadata.workflow_id`.

#### B. Trigger por EVENTO
Eventos típicos: `invoice_created`, `invoice_paid`, `client_added`, `document_processed`, etc.

- [ ] *"Cuando entra un documento clasifícalo y guarda los datos en la BD"*
- [ ] *"Cuando se cree una factura > 5000€ pídeme aprobación humana"*
- [ ] *"Cuando un cliente nuevo se registre en el CRM, mándale el welcome email"*
- Verificar:
  - El workflow se dispara al emitir el evento (`fire_event` en `_nlp.py`).
  - Las condiciones (`trigger_config.conditions`) filtran correctamente cuando aplican.

#### C. Trigger CONTINUO / PERMANENTE
Regla siempre activa sin evento ni horario. Aplica reglas a todos los datos entrantes.

- [ ] *"Todos los Excels se rellenan siempre con la plantilla X y se renombran"*
- [ ] *"Cada email entrante con 'factura' en el asunto se archiva en Documentos"*
- Verificar:
  - El workflow se mantiene escuchando.
  - No genera tasks vacías sin trigger real.

### Modos de ejecución a cubrir

- [ ] **Deterministic**: editor visual con nodos fijos (ConditionNode, ActionNode...). Acción concreta sin LLM en runtime. Más rápido, más estable.
- [ ] **Reasoning**: el LLM crea el plan dinámicamente. Más flexible, más latente.

Probar al menos un workflow de cada modo y verificar:
- Que el modo se respeta (`workflow.execution_mode` en BD).
- Que `parse_nl` clasifica bien si una intención puede ser determinista (vía `workflow_determinism_check.txt`).

### Cosas a vigilar en automatizaciones

1. **Idempotencia**: dos disparos seguidos no deben duplicar la acción.
2. **Concurrencia**: si ya hay `running`/`pending` para un workflow, el sistema bloquea (HTTP 409).
3. **Aprobación humana**: workflows que generan acciones de riesgo (factura > umbral, transferencia) deben pausar y pedir aprobación.
4. **Reintentos**: si una ejecución falla, el orquestador debe reintentar con backoff (no entrar en loop).
5. **Generación de tasks hijas**: una automatización en modo reasoning genera Tasks descendientes — verificar que aparecen en `Task.additional_metadata.workflow_id`.

---

## Verificación en base de datos

Postgres del exe portable:
```
URL: postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db
```

Python embebido:
```
"C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe"
```

### Plantilla de inspección

```python
import os
from sqlalchemy import create_engine, text
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db",
)
e = create_engine(os.environ["DATABASE_URL"])
with e.connect() as c:
    # Documentos generados recientemente
    rows = c.execute(text("""
        SELECT created_at, file_size, file_name, file_path
        FROM tenant_documents
        WHERE created_at > NOW() - INTERVAL '15 minutes'
        ORDER BY created_at DESC
    """)).all()
    for r in rows:
        print(f"{r[0]} | {r[1]} bytes | {r[2]}\n  {r[3]}")

    # Tasks recientes
    rows = c.execute(text("""
        SELECT id, status, created_at, agent_results
        FROM tasks
        WHERE created_at > NOW() - INTERVAL '15 minutes'
        ORDER BY created_at DESC LIMIT 5
    """)).all()
    for r in rows:
        print(f"task {str(r[0])[:8]} | {r[1]} | {r[2]}")

    # Ejecuciones de workflows
    rows = c.execute(text("""
        SELECT id, workflow_id, status, started_at
        FROM workflow_executions
        WHERE started_at > NOW() - INTERVAL '15 minutes'
        ORDER BY started_at DESC LIMIT 5
    """)).all()
    for r in rows:
        print(f"exec {str(r[0])[:8]} | wf={str(r[1])[:8]} | {r[2]}")
```

> La tabla `tasks` **no tiene columna `updated_at`**. Solo `created_at`.

---

## Operaciones comunes

### Cancelar tasks colgados

```python
from sqlalchemy import create_engine, text
e = create_engine("postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db")
with e.begin() as c:
    c.execute(text("""
        UPDATE tasks SET status='failed',
                         error_message='cancelled manually'
        WHERE status IN ('executing', 'pending')
          AND created_at > NOW() - INTERVAL '30 minutes'
    """))
```

### Aplicar migraciones Alembic

`DATABASE_URL` con dialect `psycopg2` (no `psycopg`):

```bash
cd "C:/Users/Marcos/AppData/Local/Programs/automatizapyme-desktop/resources/project/backend"
DATABASE_URL="postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db" \
  "C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe" -m alembic current

DATABASE_URL="postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db" \
  "C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe" -m alembic upgrade head
```

### Verificar que el sync llevó un cambio

```bash
grep -c "<patrón_nuevo>" \
  "C:/Users/Marcos/AppData/Local/Programs/automatizapyme-desktop/resources/project/backend/<archivo.py>"
```

Si devuelve 0 → el sync no se hizo, repetir `cd desktop && npm run sync`.

### Disparar manualmente un evento (probar workflows event-based)

```python
import asyncio
from app.db.base import AsyncSessionLocal
from app.services.workflow._nlp import fire_event

async def go():
    async with AsyncSessionLocal() as db:
        triggered = await fire_event(
            event_name="invoice_created",
            context={"amount": 6000},
            tenant_id=tenant_uuid,
            user_id=user_uuid,
            db=db,
        )
        print("workflows disparados:", triggered)

asyncio.run(go())
```

---

## Paths importantes

```
Repo dev:           c:\Users\Marcos\Desktop\automatizacion de empresas\Automatiza-pyme-main\
Exe instalado:      C:\Users\Marcos\AppData\Local\Programs\automatizapyme-desktop\resources\project\
.env real:          ↑ + \.env
Python embed:       C:\Users\Marcos\AppData\Roaming\AutomatizaPyme\python\python.exe
Uploads del tenant: C:\Users\Marcos\AppData\Roaming\AutomatizaPyme\uploads\<categoría>\
Logs LLM (si trace activo): logs/llm/YYYY-MM-DD.jsonl (relativo al cwd del backend)
```

> **El `.env` del repo NO es el que el backend lee** en producción local. El backend lee del `.env` del exe instalado. Cualquier variable nueva debe ir en **ambos**, o `npm run sync` la sobreescribe en el siguiente sync.

---

## Variables de entorno relevantes

```bash
DEFAULT_LLM_PROVIDER=claude_code   # provider activo (sin coste API)
LLM_TRACE_ENABLED=true              # opcional, escribe JSONL con cada llamada LLM
LLM_TRACE_DIR=logs/llm
UPLOAD_DIR=                          # vacío en Windows → AppData/Roaming/AutomatizaPyme/uploads
```

> **Limitación con `claude_code`**: los callbacks de LangChain (incluido `LLMTraceCallback`) **no se disparan** porque el provider es un wrapper subprocess que no llama a `run_manager`. `LLM_TRACE_ENABLED=true` produce 0 archivos cuando este es el provider activo. Para diagnóstico real con trace JSONL, cambiar a `anthropic` / `gemini` (con function calling nativo) o leer stdout del backend en vivo.

---

## Checklist mínimo antes de declarar "funciona"

Para cada cambio que toque tools/agentes/dispatchers/parser:

1. ☑ La tarea termina en `status=done` o `failed` (no `executing` eterno).
2. ☑ El número de filas en `tenant_documents` corresponde al esperado (sin duplicados).
3. ☑ El `file_path` está en `AppData/Roaming/AutomatizaPyme/uploads/<categoría>/` (no en `C:\app\uploads`).
4. ☑ La duración total entra en el timeout configurado.
5. ☑ Si genera PDF, el archivo se abre correctamente y el contenido coincide con lo pedido.
6. ☑ Para tools de "consulta" (list, search), los datos vuelven de BD reales — no inventados por el LLM.
7. ☑ Para automatizaciones, un trigger genera UNA `WorkflowExecution`, no varias.
8. ☑ Caso negativo: peticiones simples NO deben usar `create_pdf_*` (debe usar `create_document` para texto plano).

---

## Cuándo escalar a investigación profunda

Si tras un cambio aparecen estos síntomas, **no insistir con re-ejecutar** — investigar:

- Tasks que se quedan en `executing` más de 2× el timeout configurado → el cleanup post-error está colgado.
- Múltiples PDFs o documentos por una sola tarea → algún dispatcher creó duplicados (revisar `_messages_already_generated_pdf` en helpers).
- Endpoints que devuelven 200 pero los datos no aparecen en BD → la transacción no se commiteó.
- LLM responde texto en lugar de llamar a la tool → falla de prompting o tool no registrada en `tool_registry.py`.
