# Protocolo de prueba y debug del sistema de agentes

Documento operativo para no re-explicar el setup en cada sesión. Lo que necesita Claude (o cualquiera) para retomar las pruebas end-to-end del proyecto.

---

## TL;DR — flujo de una iteración típica

1. **Editar código** en `c:\Users\Marcos\Desktop\automatizacion de empresas\Automatiza-pyme-main\`
2. **Commit + push** (con `git push origin master`).
3. **Sincronizar al exe instalado**:
   ```
   cd desktop && npm run sync
   ```
4. **Cerrar Electron completo** (incluida la bandeja del sistema).
5. **Reabrir Electron** → backend arranca con código nuevo.
6. **Lanzar prompts contra los agentes** vía API (PowerShell, ver más abajo).
7. **Verificar resultado** en BD (ver más abajo).

> El paso 3 + 4 es el más fácil de olvidar. El backend lleva minutos sin reiniciar y se prueba con código viejo. Confirmar siempre `uptime_seconds < 300` antes de declarar conclusiones.

---

## Credenciales locales (solo desarrollo)

```
email:    marcosreciosanchez@gmail.com
password: marcos3448
base URL: http://localhost:8080/api/v1
health:   http://localhost:8080/health
```

---

## IDs de los empleados IA (para prompts directos)

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

> El listado se obtiene con `GET /api/v1/ai-employees` autenticado.

---

## Lanzar un prompt — plantilla PowerShell

Tres claves importantes:
- **Body en bytes UTF-8** (sin esto, las tildes y `ñ` rompen el body con `400 parsing error`).
- **`Content-Type: application/json; charset=utf-8`**.
- **Timeout amplio en el polling** (al menos 360s para informes largos).

```powershell
$ErrorActionPreference = "Stop"
$base = "http://localhost:8080/api/v1"
$loginBody = '{"email":"marcosreciosanchez@gmail.com","password":"marcos3448"}'
$login = Invoke-RestMethod -Uri "$base/auth/login" -Method POST `
    -Body $loginBody -ContentType "application/json; charset=utf-8"
$h = @{ Authorization = "Bearer $($login.access_token)" }

$employeeId = "6b1d51ac-b2c2-4c97-95b2-7bbd037a14ad"   # CTO custom
$msg = "Genera un informe en PDF sobre <X>. Usa create_pdf_text_report. ..."

$payload = @{ message = $msg } | ConvertTo-Json -Compress
$bytes   = [System.Text.Encoding]::UTF8.GetBytes($payload)

$resp = Invoke-RestMethod -Uri "$base/ai-employees/$employeeId/instruct" `
    -Method POST -Body $bytes -Headers $h `
    -ContentType "application/json; charset=utf-8" -TimeoutSec 30
$taskId = $resp.task_id

# Polling
$deadline = (Get-Date).AddSeconds(420)
$final = $null
while ((Get-Date) -lt $deadline) {
    Start-Sleep -Seconds 5
    try { $r = Invoke-RestMethod -Uri "$base/tasks/$taskId" -Headers $h -TimeoutSec 15 } catch { continue }
    if ($r.status -in @("done","failed","completed","success")) { $final = $r; break }
}
$final.status
```

> **No usar `here-strings + here-docs anidados` en PowerShell** — se rompen al embeberse en el tool Bash. Si necesitas SQL/Python complejo, escribe a `C:\Users\Marcos\Desktop\<temp>.py` y lo ejecutas.

---

## Verificación en base de datos

Postgres del exe portable:
```
URL:  postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db
```

Python embebido para queries directas:
```
"C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe"
```

### Plantilla de inspección rápida (Python)

```python
import os
from sqlalchemy import create_engine, text
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db")
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
```

> **Ojo**: la tabla `tasks` **no tiene `updated_at`**. Solo `created_at`.

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

Hay que pasar `DATABASE_URL` con dialect `psycopg2` (no `psycopg`):

```bash
cd "C:/Users/Marcos/AppData/Local/Programs/automatizapyme-desktop/resources/project/backend"
DATABASE_URL="postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db" \
  "C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe" -m alembic current
DATABASE_URL="postgresql+psycopg2://pyme_user:pyme_pass@localhost:5433/pyme_db" \
  "C:/Users/Marcos/AppData/Roaming/AutomatizaPyme/python/python.exe" -m alembic upgrade head
```

### Verificar que el sync llevó un cambio concreto al exe

```bash
grep -c "<patrón_nuevo>" "C:/Users/Marcos/AppData/Local/Programs/automatizapyme-desktop/resources/project/backend/<archivo.py>"
```

Si devuelve 0 → el sync no se hizo (o estás mirando archivo equivocado). Repetir `cd desktop && npm run sync`.

### Verificar uptime del backend

```bash
powershell -Command "(Invoke-RestMethod -Uri http://localhost:8080/health).uptime_seconds"
```

- < 60s → recién reiniciado, listo para probar
- > 300s → backend quizá tiene código viejo en RAM, no fiar de las pruebas

---

## Paths importantes

```
Repo dev:     c:\Users\Marcos\Desktop\automatizacion de empresas\Automatiza-pyme-main\
Exe instalado: C:\Users\Marcos\AppData\Local\Programs\automatizapyme-desktop\resources\project\
.env real:    C:\Users\Marcos\AppData\Local\Programs\automatizapyme-desktop\resources\project\.env
Python embed: C:\Users\Marcos\AppData\Roaming\AutomatizaPyme\python\python.exe
Uploads del tenant: C:\Users\Marcos\AppData\Roaming\AutomatizaPyme\uploads\<categoría>\
Logs LLM (si trace activo): logs/llm/YYYY-MM-DD.jsonl (relativo al cwd del backend)
```

> **El `.env` del repo NO es el que el backend lee** en producción local. El backend lee del `.env` del exe instalado. Cualquier cambio en variables (`LLM_TRACE_ENABLED`, etc.) hay que aplicarlo en **ambos** (.env del repo y .env del exe), o el `npm run sync` lo sobreescribe.

---

## Variables de entorno relevantes

```bash
DEFAULT_LLM_PROVIDER=claude_code   # provider activo en local (sin coste API)
LLM_TRACE_ENABLED=true             # opcional, escribe JSONL con cada llamada LLM
LLM_TRACE_DIR=logs/llm             # destino de los JSONL
UPLOAD_DIR=                         # vacío → usa AppData/Roaming/AutomatizaPyme/uploads (Windows)
```

> **Limitación conocida**: con `claude_code` los callbacks de LangChain (incluido `LLMTraceCallback`) **no se disparan** porque el provider es un wrapper subprocess que no llama a `run_manager`. Resultado: `LLM_TRACE_ENABLED=true` produce 0 archivos cuando el provider activo es claude_code. Para diagnóstico real hay que usar otro provider con function calling nativo (Anthropic API, Gemini) o leer stdout del backend en vivo.

---

## Bugs conocidos (al cierre 2026-05-08)

1. **Custom employee timeout no se propaga rápido**: tasks dirigidas al CTO custom (`Marcos Recio`) tardan ~8 minutos en pasar de `executing` a `failed`, aunque el `wait_for(timeout=300)` está configurado. Cleanup de BD post-error parece colgarse. Ver `tasks/lessons.md`.

2. **API `/ai-employees/{id}` devuelve `skills: []`** aunque la BD tenga las skills correctamente — bug del serializer de respuesta. Cosmético, runtime no afectado.

3. **El classifier del orchestrator** despacha por intención, ignorando `addressed_employee_id` cuando viene de `instruct_employee`. Por eso prompts dirigidos al CTO custom acaban procesados por el built-in de su dominio. Cosmético — funciona, pero no usa el `system_prompt` específico del custom.

4. **`UPLOAD_DIR=/app/uploads`** (default Linux) en Windows se resuelve como `C:\app\uploads`. Ya lo cubre `_resolve_upload_dir` que detecta Windows y usa AppData, **siempre que `UPLOAD_DIR` esté vacío o sea distinto al default**.

---

## Plantilla de prompts útiles

### Probar generación de PDF
> *"Genera un informe profundo en PDF sobre [TEMA]. Usa create_pdf_text_report. Title 'X'. Author 'Y'. Body markdown con secciones ##, tablas pipe, listas con -, blockquotes con > Nota:/Recomendación:/Importante:."*

### Probar agente de billing
> *"Lista las facturas de los últimos 30 días con su estado."*

### Probar agente de HR
> *"Lista los empleados activos con NIF y salario base."*

### Probar agente de CRM
> *"Lista las oportunidades en fase qualified con cliente y valor esperado."*

### Probar agente de compliance
> *"Qué vencimientos fiscales tengo en los próximos 30 días?"*

### Caso negativo (NO debe usar create_pdf_*)
> *"Apunta en una nota txt que tengo reunión mañana a las 10."*

---

## Migraciones aplicadas hasta hoy

```
0001_initial_squashed
0002_add_cross_domain_accounting_fks
0003_create_document_embeddings_jsonb
0004_tenant_logo_pdf_skill          # logo de tenant + skill create_pdf_report
0005_pdf_text_report_skill          # backfill skill create_pdf_text_report
```

Si una próxima sesión añade nuevas, aplicar con el comando de Alembic de arriba. **El usuario puede que no las haya aplicado** — comprobar con `alembic current` antes de probar.
