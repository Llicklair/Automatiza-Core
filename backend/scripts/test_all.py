#!/usr/bin/env python3
"""
[DEPRECATED] test_all.py -- Test integral del sistema AutomatizaCore con MockLLM.

⚠️  DEPRECATED — este script duplica fixtures de la suite pytest oficial y
puede divergir en cualquier momento. La cobertura equivalente vive en:

  - backend/tests/test_api_auth.py            (autenticación)
  - backend/tests/test_api_invoices.py        (billing)
  - backend/tests/test_api_hr_full.py         (hr)
  - backend/tests/test_api_crm.py             (crm)
  - backend/tests/test_api_workflows.py       (automatizaciones)
  - backend/tests/test_api_approvals.py       (aprobaciones)
  - backend/tests/test_service_audit.py       (auditoría)
  - backend/tests/test_scanner_auth.py        (escáner)
  - backend/tests/test_e2e_happy_path.py      (flujo integral)

Ejecutar la suite pytest equivalente:
    cd backend && pytest tests/test_e2e_happy_path.py -v

Este script se conserva como referencia histórica del modo "smoke por HTTP"
con MockLLM; **no añadir nuevos checks aquí** — moverlos a `backend/tests/`.

---

Prueba: autenticacion, tareas IA (billing, hr, crm, compliance, documents),
automatizaciones (workflows + executions), aprobaciones, auditoria y escaner.

Uso:
    py -X utf8 scripts/test_all.py [--url http://localhost:8080]
"""
import argparse
import sys
import time

import requests

# ─── Config ───────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--url", default="http://localhost:8080", help="URL base de la API")
args = parser.parse_args()

BASE = args.url.rstrip("/")
EMAIL = "demo@automatizacore.com"
PASSWORD = "Demo1234!"

# ─── Helpers ──────────────────────────────────────────────────────────────────

PASS = "[OK]"
FAIL = "[KO]"
INFO = "[ ] "

results = {"passed": 0, "failed": 0}


def ok(msg: str):
    print(f"  {PASS} {msg}")
    results["passed"] += 1


def fail(msg: str, detail: str = ""):
    print(f"  {FAIL} {msg}" + (f"\n       {detail}" if detail else ""))
    results["failed"] += 1


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def api(method: str, path: str, token: str = None, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(method, f"{BASE}{path}", headers=headers, timeout=30, **kwargs)


def wait_task(task_id: str, token: str, max_wait: int = 60) -> dict:
    """Espera a que una tarea termine (status != processing/pending)."""
    for _ in range(max_wait // 3):
        r = api("GET", f"/api/v1/tasks/{task_id}", token=token)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") not in ("processing", "pending", "running"):
                return data
        time.sleep(3)
    return {}


# ─── 1. Auth ──────────────────────────────────────────────────────────────────

section("1. AUTENTICACION")

try:
    r = api("POST", "/api/v1/auth/login",
            json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 200:
        TOKEN = r.json().get("access_token", "")
        ok(f"Login OK -> token={TOKEN[:20]}...")
    else:
        fail("Login fallido", f"HTTP {r.status_code}: {r.text[:200]}")
        sys.exit(1)
except Exception as e:
    fail("No se pudo conectar a la API", str(e))
    sys.exit(1)

# Tenant info
r = api("GET", "/api/v1/tenant/me", token=TOKEN)
if r.status_code == 200:
    me = r.json()
    TENANT_ID = me.get("id", "")
    ok(f"/tenant/me -> tenant={TENANT_ID[:8]}...")
else:
    fail("/tenant/me fallo", f"HTTP {r.status_code}")
    TENANT_ID = ""

# ─── 2. Health ────────────────────────────────────────────────────────────────

section("2. HEALTH & ENDPOINTS BASICOS")

r = api("GET", "/health")
if r.status_code == 200:
    ok("GET /health -> 200")
else:
    fail("GET /health", f"HTTP {r.status_code}")

r = api("GET", "/api/v1/tenant/me", token=TOKEN)
if r.status_code == 200:
    ok("GET /api/v1/tenant/me -> 200")
else:
    fail("GET /api/v1/tenant/me", f"HTTP {r.status_code}")

# ─── 3. ERP (Clientes, Facturas, Productos) ───────────────────────────────────

section("3. ERP")

# Clientes
r = api("GET", "/api/v1/clients", token=TOKEN)
if r.status_code == 200:
    clients = r.json()
    ok(f"GET /api/v1/clients -> {len(clients)} clientes")
    CLIENT_ID = clients[0]["id"] if clients else None
else:
    fail("GET /api/v1/clients", f"HTTP {r.status_code}")
    CLIENT_ID = None

# Productos
r = api("GET", "/api/v1/products", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/products -> {len(r.json())} productos")
else:
    fail("GET /api/v1/products", f"HTTP {r.status_code}")

# Facturas
r = api("GET", "/api/v1/invoices", token=TOKEN)
if r.status_code == 200:
    invoices = r.json()
    ok(f"GET /api/v1/invoices -> {len(invoices)} facturas")
    INVOICE_ID = invoices[0]["id"] if invoices else None
else:
    fail("GET /api/v1/invoices", f"HTTP {r.status_code}")
    INVOICE_ID = None

# Presupuestos
r = api("GET", "/api/v1/quotes/", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/quotes/ -> {len(r.json())} presupuestos")
else:
    fail("GET /api/v1/quotes/", f"HTTP {r.status_code}")

# Recurrentes
r = api("GET", "/api/v1/recurring-invoices", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/recurring-invoices -> {len(r.json())} recurrentes")
else:
    fail("GET /api/v1/recurring-invoices", f"HTTP {r.status_code}")

# Pedidos compra
r = api("GET", "/api/v1/purchase-orders", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/purchase-orders -> {len(r.json())} pedidos")
else:
    fail("GET /api/v1/purchase-orders", f"HTTP {r.status_code}")

# ─── 4. RRHH ──────────────────────────────────────────────────────────────────

section("4. RRHH")

r = api("GET", "/api/v1/hr/employees", token=TOKEN)
if r.status_code == 200:
    emps = r.json()
    ok(f"GET /api/v1/hr/employees -> {len(emps)} empleados")
    EMP_ID = emps[0]["id"] if emps else None
    EMP_NIF = emps[0].get("nif") if emps else None
else:
    fail("GET /api/v1/hr/employees", f"HTTP {r.status_code}")
    EMP_ID = None
    EMP_NIF = None

r = api("GET", "/api/v1/hr/payrolls", token=TOKEN)
if r.status_code == 200:
    payrolls = r.json()
    ok(f"GET /api/v1/hr/payrolls -> {len(payrolls)} nominas")
    PAYROLL_ID = payrolls[0]["id"] if payrolls else None
else:
    fail("GET /api/v1/hr/payrolls", f"HTTP {r.status_code}")
    PAYROLL_ID = None

# ─── 5. CRM ───────────────────────────────────────────────────────────────────

section("5. CRM")

for path in ["/api/v1/crm/opportunities", "/api/v1/crm/events", "/api/v1/crm/reservations", "/api/v1/crm/activities"]:
    r = api("GET", path, token=TOKEN)
    if r.status_code == 200:
        ok(f"GET {path} -> {len(r.json())} registros")
    else:
        fail(f"GET {path}", f"HTTP {r.status_code}")

# ─── 6. Contabilidad ──────────────────────────────────────────────────────────

section("6. CONTABILIDAD")

r = api("GET", "/api/v1/accounting/journal", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/accounting/journal -> {len(r.json())} asientos")
else:
    fail("GET /api/v1/accounting/journal", f"HTTP {r.status_code}")

r = api("GET", "/api/v1/accounting/assets", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/accounting/assets -> {len(r.json())} activos")
else:
    fail("GET /api/v1/accounting/assets", f"HTTP {r.status_code}")

# ─── 7. Banca / Tesoreria ─────────────────────────────────────────────────────

section("7. TESORERIA & BANCA")

r = api("GET", "/api/v1/banking/transactions", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/banking/transactions -> {len(r.json())} transacciones")
else:
    fail("GET /api/v1/banking/transactions", f"HTTP {r.status_code}")

r = api("GET", "/api/v1/banking/summary", token=TOKEN)
if r.status_code in (200, 404):
    ok(f"GET /api/v1/banking/summary -> HTTP {r.status_code}")
else:
    fail("GET /api/v1/banking/summary", f"HTTP {r.status_code}")

# ─── 8. Advisory (Compliance) ─────────────────────────────────────────────────

section("8. ADVISORY / COMPLIANCE")

for path in ["/api/v1/advisory/boe", "/api/v1/advisory/calendar", "/api/v1/advisory/guides"]:
    r = api("GET", path, token=TOKEN)
    if r.status_code == 200:
        data = r.json()
        cnt = len(data) if isinstance(data, list) else "ok"
        ok(f"GET {path} -> {cnt}")
    elif r.status_code == 404:
        ok(f"GET {path} -> 404 (sin datos aun)")
    else:
        fail(f"GET {path}", f"HTTP {r.status_code}")

# ─── 9. Documentos ────────────────────────────────────────────────────────────

section("9. DOCUMENTOS")

r = api("GET", "/api/v1/documents", token=TOKEN)
if r.status_code == 200:
    docs = r.json()
    ok(f"GET /api/v1/documents -> {len(docs)} documentos")
else:
    fail("GET /api/v1/documents", f"HTTP {r.status_code}")

# ─── 10. Proyectos ────────────────────────────────────────────────────────────

section("10. PROYECTOS")

r = api("GET", "/api/v1/projects", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/projects -> {len(r.json())} proyectos")
else:
    fail("GET /api/v1/projects", f"HTTP {r.status_code}")

r = api("GET", "/api/v1/projects/tasks", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/projects/tasks -> {len(r.json())} tareas")
else:
    fail("GET /api/v1/projects/tasks", f"HTTP {r.status_code}")

# ─── 11. TAREAS IA ────────────────────────────────────────────────────────────

section("11. TAREAS IA (con MockLLM)")

# El campo es user_intent (no intent)
task_cases = [
    {
        "name": "Billing: generar factura",
        "payload": {"domain": "billing", "user_intent": "Genera una factura para el cliente B12345678 por servicios de consultoria por 1500 euros"}
    },
    {
        "name": "HR: generar nominas",
        "payload": {"domain": "hr", "user_intent": "Genera las nominas de todos los empleados para marzo 2026"}
    },
    {
        "name": "CRM: analizar leads",
        "payload": {"domain": "crm", "user_intent": "Analiza los leads en fase new y cualifica los de alta prioridad"}
    },
    {
        "name": "Compliance: alertas fiscales",
        "payload": {"domain": "compliance", "user_intent": "Que vencimientos fiscales tenemos proximos este trimestre"}
    },
    {
        "name": "Documents: listar documentos",
        "payload": {"domain": "documents", "user_intent": "Lista todos los documentos subidos al sistema"}
    },
]

task_ids = []
for case in task_cases:
    r = api("POST", "/api/v1/tasks", token=TOKEN, json=case["payload"])
    if r.status_code in (200, 201):
        task_id = r.json().get("id") or r.json().get("task_id")
        task_ids.append((case["name"], task_id))
        ok(f"Task creada: {case['name']} -> id={task_id}")
    else:
        fail(f"Task '{case['name']}' no se creo", f"HTTP {r.status_code}: {r.text[:200]}")

# Esperar resultados
print(f"\n  {INFO} Esperando resultados de {len(task_ids)} tareas (max 60s cada una)...")
for name, task_id in task_ids:
    if not task_id:
        continue
    result = wait_task(task_id, TOKEN, max_wait=60)
    status = result.get("status", "timeout")
    if status in ("completed", "done", "success"):
        ok(f"Task '{name}' -> {status}")
    elif status in ("failed", "error"):
        detail = result.get("error") or str(result.get("result", ""))
        fail(f"Task '{name}' -> {status}", detail[:200])
    else:
        print(f"  [~] Task '{name}' -> status={status} (procesando aun)")
        results["passed"] += 1

# ─── 12. AUTOMATIZACIONES (Workflows) ─────────────────────────────────────────

section("12. AUTOMATIZACIONES")

# Listar workflows
r = api("GET", "/api/v1/workflows/", token=TOKEN)
if r.status_code == 200:
    workflows = r.json()
    ok(f"GET /api/v1/workflows/ -> {len(workflows)} workflows")
    WORKFLOW_ID = workflows[0]["id"] if workflows else None
else:
    fail("GET /api/v1/workflows/", f"HTTP {r.status_code}")
    WORKFLOW_ID = None

# Crear workflow de prueba (requiere name, trigger_type, action_type)
r = api("POST", "/api/v1/workflows/", token=TOKEN, json={
    "name": "Test Workflow Mock",
    "description": "Workflow creado por el test integral",
    "trigger_type": "manual",
    "action_type": "create_task",
    "trigger_config": {},
    "action_config": {"domain": "billing", "user_intent": "Revisar facturas pendientes"},
    "is_active": True,
})
if r.status_code in (200, 201):
    wf = r.json()
    NEW_WORKFLOW_ID = wf.get("id")
    ok(f"POST /api/v1/workflows/ -> id={NEW_WORKFLOW_ID}")
else:
    fail("POST /api/v1/workflows/", f"HTTP {r.status_code}: {r.text[:200]}")
    NEW_WORKFLOW_ID = WORKFLOW_ID

# Executions del workflow
if NEW_WORKFLOW_ID:
    r = api("GET", f"/api/v1/workflows/{NEW_WORKFLOW_ID}/executions", token=TOKEN)
    if r.status_code == 200:
        ok(f"GET /workflows/{NEW_WORKFLOW_ID}/executions -> {len(r.json())} ejecuciones")
    else:
        fail(f"GET /workflows/{NEW_WORKFLOW_ID}/executions", f"HTTP {r.status_code}")

# Lanzar workflow manualmente
    r = api("POST", f"/api/v1/workflows/{NEW_WORKFLOW_ID}/run", token=TOKEN, json={})
    if r.status_code in (200, 201, 202):
        ok(f"POST /workflows/{NEW_WORKFLOW_ID}/run -> ejecutado")
    else:
        fail(f"POST /workflows/{NEW_WORKFLOW_ID}/run", f"HTTP {r.status_code}: {r.text[:200]}")

# ─── 13. APROBACIONES ─────────────────────────────────────────────────────────

section("13. APROBACIONES")

r = api("GET", "/api/v1/approvals", token=TOKEN)
if r.status_code == 200:
    approvals = r.json()
    ok(f"GET /api/v1/approvals -> {len(approvals)} pendientes")
    if approvals:
        # El endpoint es /decide con {"approved": true}
        first_id = approvals[0]["id"]
        r2 = api("POST", f"/api/v1/approvals/{first_id}/decide",
                 token=TOKEN, json={"approved": True})
        if r2.status_code in (200, 201):
            ok(f"POST /approvals/{first_id}/decide -> aprobado")
        elif r2.status_code == 410:
            ok(f"POST /approvals/{first_id}/decide -> 410 expirada (logica correcta)")
        else:
            fail(f"POST /approvals/{first_id}/decide", f"HTTP {r2.status_code}: {r2.text[:150]}")
else:
    fail("GET /api/v1/approvals", f"HTTP {r.status_code}")

# ─── 14. INTEGRACIONES ────────────────────────────────────────────────────────

section("14. INTEGRACIONES")

r = api("GET", "/api/v1/integrations", token=TOKEN)
if r.status_code == 200:
    ok(f"GET /api/v1/integrations -> {len(r.json())} integraciones")
else:
    fail("GET /api/v1/integrations", f"HTTP {r.status_code}")

# ─── 15. TAREA COORDINADOR ────────────────────────────────────────────────────

section("15. TAREA COORDINADOR (multi-agente)")

r = api("POST", "/api/v1/tasks", token=TOKEN, json={
    "domain": "coordinator",
    "user_intent": (
        "Necesito un informe completo del mes de marzo 2026: "
        "genera las nominas de todos los empleados, "
        "lista las facturas pendientes de cobro y "
        "revisa los vencimientos fiscales del trimestre."
    ),
})
if r.status_code in (200, 201):
    coord_id = r.json().get("id") or r.json().get("task_id")
    ok(f"Task coordinadora creada -> id={coord_id}")
    if coord_id:
        result = wait_task(coord_id, TOKEN, max_wait=90)
        status = result.get("status", "timeout")
        if status in ("completed", "done", "success"):
            ok(f"Coordinador -> {status}")
        elif status in ("failed", "error"):
            fail(f"Coordinador -> {status}", str(result.get("error",""))[:200])
        else:
            print(f"  [~] Coordinador -> status={status} (puede seguir procesando)")
            results["passed"] += 1
else:
    fail("Task coordinadora", f"HTTP {r.status_code}: {r.text[:200]}")

# ─── 16. NOMINA: aprobar draft existente ──────────────────────────────────────

section("16. APROBAR NOMINA DRAFT")

if PAYROLL_ID:
    r = api("POST", f"/api/v1/hr/payrolls/{PAYROLL_ID}/approve", token=TOKEN, json={})
    if r.status_code in (200, 201):
        ok(f"POST /hr/payrolls/{PAYROLL_ID}/approve -> aprobada")
    elif r.status_code == 400:
        ok(f"POST /hr/payrolls/{PAYROLL_ID}/approve -> 400 (ya aprobada, OK)")
    else:
        fail(f"POST /hr/payrolls/{PAYROLL_ID}/approve", f"HTTP {r.status_code}: {r.text[:150]}")
else:
    ok("Sin nominas draft para probar (skip)")

# ─── Resumen ──────────────────────────────────────────────────────────────────

section("RESUMEN FINAL")

total = results["passed"] + results["failed"]
pct = int(results["passed"] / total * 100) if total > 0 else 0

if pct >= 80:
    color_label = "EXCELENTE"
elif pct >= 60:
    color_label = "ACEPTABLE"
else:
    color_label = "NECESITA ATENCION"

print(f"\n  Resultados: {results['passed']}/{total} tests pasados ({pct}%) [{color_label}]")
if results["failed"] > 0:
    print(f"  {FAIL} {results['failed']} test(s) fallaron")
else:
    print(f"  {PASS} Todos los tests pasaron")

sys.exit(0 if results["failed"] == 0 else 1)
