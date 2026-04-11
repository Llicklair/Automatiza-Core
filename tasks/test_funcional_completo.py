"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          AUTOMATIZAPYME — TEST FUNCIONAL COMPLETO                           ║
║  Simula un usuario real probando TODAS las funcionalidades via API          ║
║  Ejecutar: python tasks/test_funcional_completo.py                          ║
║  Opciones: --base-url URL  --skip-agents  --report-dir DIR                  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import argparse
import asyncio
import json
import os
import sys
import time

# Fix Windows console encoding for Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx

# ─── CLI ──────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="AutomatizaPyme — Test Funcional Completo")
parser.add_argument("--base-url", default="http://localhost:8080/api/v1")
parser.add_argument("--email", default="marcosreciosanchez@gmail.com")
parser.add_argument("--password", default="marcos3448")
parser.add_argument("--skip-agents", action="store_true", help="Saltar fases de agentes IA")
parser.add_argument("--report-dir", default="tasks/reports")
ARGS: argparse.Namespace = None  # type: ignore  # set in main()

# ─── Utilidades ───────────────────────────────────────────────────────────────

PASS_ICON = "✅"
FAIL_ICON = "❌"
SKIP_ICON = "⚠️ "
INFO_ICON = "ℹ️ "

HEADERS: dict = {}


@dataclass
class TestResult:
    phase: str
    test_name: str
    status: str  # PASS | FAIL | SKIP
    response_ms: float = 0.0
    error: str = ""
    http_status: int = 0


results: list[TestResult] = []
created_ids: dict[str, list[str]] = {
    "clients": [], "products": [], "invoices": [], "quotes": [],
    "sales_orders": [], "purchase_orders": [], "recurring_invoices": [],
    "employees": [], "payrolls": [], "projects": [], "project_tasks": [],
    "opportunities": [], "activities": [], "events": [],
    "journal_entries": [], "workflows": [], "ai_employees": [],
    "generative_ui": [], "documents": [], "tasks": [],
}


def ok(phase: str, test_name: str, detail: str = "", ms: float = 0, http_status: int = 200):
    msg = f"  {PASS_ICON} {test_name}"
    if detail:
        msg += f" → {detail}"
    if ms > 0:
        msg += f" ({ms:.0f}ms)"
    print(msg)
    results.append(TestResult(phase, test_name, "PASS", ms, "", http_status))


def fail(phase: str, test_name: str, detail: str = "", ms: float = 0, http_status: int = 0):
    msg = f"  {FAIL_ICON} {test_name}"
    if detail:
        msg += f" → {detail}"
    print(msg)
    results.append(TestResult(phase, test_name, "FAIL", ms, detail, http_status))


def skip(phase: str, test_name: str, reason: str = ""):
    msg = f"  {SKIP_ICON} {test_name}"
    if reason:
        msg += f" → {reason}"
    print(msg)
    results.append(TestResult(phase, test_name, "SKIP", 0, reason, 0))


def info(msg: str):
    print(f"  {INFO_ICON} {msg}")


def section(title: str):
    print(f"\n{'═' * 60}")
    print(f"  {title}")
    print(f"{'═' * 60}")


async def timed_request(client: httpx.AsyncClient, method: str, url: str, **kwargs) -> tuple[httpx.Response, float]:
    t0 = time.perf_counter()
    r = await client.request(method, url, headers=HEADERS, **kwargs)
    ms = (time.perf_counter() - t0) * 1000
    # Handle rate limiting
    if r.status_code == 429:
        info("Rate limited — esperando 10s...")
        await asyncio.sleep(10)
        t0 = time.perf_counter()
        r = await client.request(method, url, headers=HEADERS, **kwargs)
        ms = (time.perf_counter() - t0) * 1000
    return r, ms


async def poll_task(client: httpx.AsyncClient, task_id: str, max_wait: int = 180) -> dict | None:
    for _ in range(max_wait):
        r = await client.get(f"/tasks/{task_id}", headers=HEADERS)
        if r.status_code == 200:
            t = r.json()
            if t["status"] in ("done", "failed"):
                return t
        await asyncio.sleep(1)
    return None


# ─── FASE 0: Health ──────────────────────────────────────────────────────────

async def phase_health(client: httpx.AsyncClient):
    phase = "0-Health"
    section("0. HEALTH & CONECTIVIDAD")

    try:
        r, ms = await timed_request(client, "GET", "/../../health")
        if r.status_code == 200:
            ok(phase, "GET /health", f"status={r.status_code}", ms, r.status_code)
        else:
            fail(phase, "GET /health", f"status={r.status_code}", ms, r.status_code)
    except httpx.ConnectError:
        fail(phase, "GET /health", "Servidor no accesible — ¿está arrancado?")
        return False

    try:
        r, ms = await timed_request(client, "GET", "/../../ready")
        if r.status_code == 200:
            ok(phase, "GET /ready", f"BD conectada", ms, r.status_code)
        else:
            fail(phase, "GET /ready", f"status={r.status_code}", ms, r.status_code)
    except Exception as e:
        fail(phase, "GET /ready", str(e)[:100])

    return True


# ─── FASE 1: Auth ────────────────────────────────────────────────────────────

async def phase_auth(client: httpx.AsyncClient) -> bool:
    phase = "1-Auth"
    section("1. AUTENTICACIÓN")

    r, ms = await timed_request(client, "POST", "/auth/login", json={
        "email": ARGS.email,
        "password": ARGS.password,
    })
    if r.status_code == 200:
        data = r.json()
        HEADERS["Authorization"] = f"Bearer {data['access_token']}"
        ok(phase, "Login", f"token obtenido", ms, r.status_code)
    else:
        fail(phase, "Login", f"status={r.status_code} {r.text[:100]}", ms, r.status_code)
        return False

    r, ms = await timed_request(client, "GET", "/auth/me")
    if r.status_code == 200:
        me = r.json()
        ok(phase, "GET /auth/me", f"email={me.get('email')} role={me.get('role')}", ms, r.status_code)
    else:
        fail(phase, "GET /auth/me", f"status={r.status_code}", ms, r.status_code)

    return True


# ─── FASE 2: Clientes ────────────────────────────────────────────────────────

async def phase_clients(client: httpx.AsyncClient) -> tuple[str, str]:
    phase = "2-Clientes"
    section("2. ERP — CLIENTES Y PROVEEDORES")
    client_id = ""
    supplier_id = ""

    # Crear cliente
    r, ms = await timed_request(client, "POST", "/clients", json={
        "name": "E2E_TEST_Client SL",
        "nif": "B_E2E_001",
        "email": "e2e@test.com",
        "city": "Madrid",
        "client_type": "customer",
    })
    if r.status_code == 201:
        client_id = r.json()["id"]
        created_ids["clients"].append(client_id)
        ok(phase, "Crear cliente", f"id={client_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear cliente", r.text[:100], ms, r.status_code)

    # Crear proveedor
    r, ms = await timed_request(client, "POST", "/clients", json={
        "name": "E2E_TEST_Proveedor SA",
        "nif": "B_E2E_002",
        "client_type": "supplier",
    })
    if r.status_code == 201:
        supplier_id = r.json()["id"]
        created_ids["clients"].append(supplier_id)
        ok(phase, "Crear proveedor", f"id={supplier_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear proveedor", r.text[:100], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/clients")
    if r.status_code == 200:
        ok(phase, "Listar clientes", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar clientes", r.text[:100], ms, r.status_code)

    # Actualizar
    if client_id:
        r, ms = await timed_request(client, "PATCH", f"/clients/{client_id}", json={"city": "Barcelona"})
        if r.status_code == 200:
            ok(phase, "Actualizar cliente", "city=Barcelona", ms, r.status_code)
        else:
            fail(phase, "Actualizar cliente", r.text[:100], ms, r.status_code)

    return client_id, supplier_id


# ─── FASE 3: Productos ───────────────────────────────────────────────────────

async def phase_products(client: httpx.AsyncClient) -> tuple[str, str]:
    phase = "3-Productos"
    section("3. ERP — PRODUCTOS Y STOCK")
    prod_id = ""
    svc_id = ""

    # Producto
    r, ms = await timed_request(client, "POST", "/products", json={
        "name": "E2E_TEST_Producto",
        "item_type": "product",
        "price": 150.0,
        "tax_percentage": 21.0,
        "stock_quantity": 0,
        "sku": "E2E-PROD-001",
    })
    if r.status_code == 201:
        prod_id = r.json()["id"]
        created_ids["products"].append(prod_id)
        ok(phase, "Crear producto", f"id={prod_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear producto", r.text[:100], ms, r.status_code)

    # Servicio
    r, ms = await timed_request(client, "POST", "/products", json={
        "name": "E2E_TEST_Servicio",
        "item_type": "service",
        "price": 80.0,
        "sku": "E2E-SVC-001",
    })
    if r.status_code == 201:
        svc_id = r.json()["id"]
        created_ids["products"].append(svc_id)
        ok(phase, "Crear servicio", f"id={svc_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear servicio", r.text[:100], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/products")
    if r.status_code == 200:
        ok(phase, "Listar productos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar productos", r.text[:100], ms, r.status_code)

    # Stock movement
    if prod_id:
        r, ms = await timed_request(client, "POST", f"/products/{prod_id}/stock-movements", json={
            "movement_type": "entry",
            "quantity": 10,
            "reason": "E2E test stock entry",
        })
        if r.status_code == 201:
            ok(phase, "Mov. stock entrada +10", "", ms, r.status_code)
        else:
            fail(phase, "Mov. stock entrada", r.text[:100], ms, r.status_code)

        r, ms = await timed_request(client, "GET", f"/products/{prod_id}/stock-movements")
        if r.status_code == 200:
            ok(phase, "Historial stock", f"count={len(r.json())}", ms, r.status_code)
        else:
            fail(phase, "Historial stock", r.text[:100], ms, r.status_code)

    return prod_id, svc_id


# ─── FASE 4: Facturas ────────────────────────────────────────────────────────

async def phase_invoices(client: httpx.AsyncClient, client_id: str, prod_id: str) -> str:
    phase = "4-Facturas"
    section("4. ERP — FACTURAS")
    invoice_id = ""

    if not client_id:
        skip(phase, "Facturas", "Sin client_id previo")
        return ""

    now = datetime.now().isoformat()
    due = (datetime.now() + timedelta(days=30)).isoformat()

    lines = [{"description": "E2E_TEST_Línea 1", "quantity": 2, "unit_price": 100.0, "tax_percentage": 21.0}]
    if prod_id:
        lines[0]["product_id"] = prod_id

    r, ms = await timed_request(client, "POST", f"/clients/{client_id}/invoices", json={
        "date": now,
        "due_date": due,
        "status": "draft",
        "invoice_type": "issued",
        "notes": "Factura E2E test",
        "lines": lines,
    })
    if r.status_code == 201:
        invoice_id = r.json()["id"]
        created_ids["invoices"].append(invoice_id)
        total = r.json().get("amount_total", "?")
        ok(phase, "Crear factura", f"id={invoice_id[:8]}… total={total}", ms, r.status_code)
    else:
        fail(phase, "Crear factura", r.text[:150], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/invoices")
    if r.status_code == 200:
        ok(phase, "Listar facturas", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar facturas", r.text[:100], ms, r.status_code)

    # Detalle
    if invoice_id:
        r, ms = await timed_request(client, "GET", f"/invoices/{invoice_id}")
        if r.status_code == 200:
            ok(phase, "Detalle factura", f"status={r.json().get('status')}", ms, r.status_code)
        else:
            fail(phase, "Detalle factura", r.text[:100], ms, r.status_code)

        # Marcar pagada
        r, ms = await timed_request(client, "PATCH", f"/invoices/{invoice_id}/status", json={"status": "paid"})
        if r.status_code == 200:
            ok(phase, "Marcar factura pagada", "", ms, r.status_code)
        else:
            fail(phase, "Marcar factura pagada", r.text[:100], ms, r.status_code)

        # PDF
        r, ms = await timed_request(client, "GET", f"/invoices/{invoice_id}/pdf")
        if r.status_code == 200:
            ct = r.headers.get("content-type", "")
            ok(phase, "Descargar PDF", f"content-type={ct[:30]}", ms, r.status_code)
        else:
            fail(phase, "Descargar PDF", f"status={r.status_code}", ms, r.status_code)

    # Facturas de cliente
    if client_id:
        r, ms = await timed_request(client, "GET", f"/clients/{client_id}/invoices")
        if r.status_code == 200:
            ok(phase, "Facturas de cliente", f"count={len(r.json())}", ms, r.status_code)
        else:
            fail(phase, "Facturas de cliente", r.text[:100], ms, r.status_code)

    return invoice_id


# ─── FASE 5: Presupuestos ────────────────────────────────────────────────────

async def phase_quotes(client: httpx.AsyncClient, client_id: str) -> str:
    phase = "5-Presupuestos"
    section("5. ERP — PRESUPUESTOS")
    quote_id = ""

    if not client_id:
        skip(phase, "Presupuestos", "Sin client_id")
        return ""

    r, ms = await timed_request(client, "POST", "/quotes", json={
        "client_id": client_id,
        "status": "draft",
        "notes": "E2E_TEST presupuesto",
        "lines": [{"description": "E2E_TEST_Línea presupuesto", "quantity": 5, "unit_price": 200.0, "tax_percentage": 21.0}],
    })
    if r.status_code == 201:
        quote_id = r.json()["id"]
        created_ids["quotes"].append(quote_id)
        ok(phase, "Crear presupuesto", f"id={quote_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear presupuesto", r.text[:100], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/quotes")
    if r.status_code == 200:
        ok(phase, "Listar presupuestos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar presupuestos", r.text[:100], ms, r.status_code)

    # Convertir a factura
    if quote_id:
        r, ms = await timed_request(client, "POST", f"/quotes/{quote_id}/convert-to-invoice")
        if r.status_code in (200, 201):
            inv_id = r.json().get("id", "")
            if inv_id:
                created_ids["invoices"].append(inv_id)
            ok(phase, "Convertir a factura", f"invoice_id={str(inv_id)[:8]}…", ms, r.status_code)
        else:
            fail(phase, "Convertir a factura", r.text[:100], ms, r.status_code)

    return quote_id


# ─── FASE 6: Pedidos Venta ───────────────────────────────────────────────────

async def phase_sales_orders(client: httpx.AsyncClient, client_id: str, prod_id: str) -> str:
    phase = "6-PedidosVenta"
    section("6. ERP — PEDIDOS DE VENTA")
    order_id = ""

    if not client_id:
        skip(phase, "Pedidos venta", "Sin client_id")
        return ""

    lines = [{"description": "E2E_TEST_Línea pedido", "quantity": 3, "unit_price": 150.0, "tax_percentage": 21.0}]
    if prod_id:
        lines[0]["product_id"] = prod_id

    r, ms = await timed_request(client, "POST", "/orders", json={
        "client_id": client_id,
        "notes": "E2E_TEST pedido venta",
        "lines": lines,
    })
    if r.status_code == 201:
        order_id = r.json()["id"]
        created_ids["sales_orders"].append(order_id)
        ok(phase, "Crear pedido venta", f"id={order_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear pedido venta", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/orders")
    if r.status_code == 200:
        ok(phase, "Listar pedidos venta", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar pedidos venta", r.text[:100], ms, r.status_code)

    if order_id:
        r, ms = await timed_request(client, "PATCH", f"/orders/{order_id}", json={"status": "confirmed"})
        if r.status_code == 200:
            ok(phase, "Confirmar pedido", "", ms, r.status_code)
        else:
            fail(phase, "Confirmar pedido", r.text[:100], ms, r.status_code)

    return order_id


# ─── FASE 7: Pedidos Compra ──────────────────────────────────────────────────

async def phase_purchase_orders(client: httpx.AsyncClient, supplier_id: str, prod_id: str) -> str:
    phase = "7-PedidosCompra"
    section("7. ERP — PEDIDOS DE COMPRA")
    po_id = ""

    if not supplier_id:
        skip(phase, "Pedidos compra", "Sin supplier_id")
        return ""

    lines = [{"description": "E2E_TEST_Línea compra", "quantity": 20, "unit_price": 50.0, "tax_percentage": 21.0}]
    if prod_id:
        lines[0]["product_id"] = prod_id

    r, ms = await timed_request(client, "POST", "/purchase-orders", json={
        "supplier_id": supplier_id,
        "notes": "E2E_TEST pedido compra",
        "lines": lines,
    })
    if r.status_code == 201:
        po_id = r.json()["id"]
        created_ids["purchase_orders"].append(po_id)
        ok(phase, "Crear pedido compra", f"id={po_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear pedido compra", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/purchase-orders")
    if r.status_code == 200:
        ok(phase, "Listar pedidos compra", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar pedidos compra", r.text[:100], ms, r.status_code)

    return po_id


# ─── FASE 8: Facturas Recurrentes ────────────────────────────────────────────

async def phase_recurring(client: httpx.AsyncClient, client_id: str) -> str:
    phase = "8-Recurrentes"
    section("8. ERP — FACTURAS RECURRENTES")
    rec_id = ""

    if not client_id:
        skip(phase, "Recurrentes", "Sin client_id")
        return ""

    next_run = (date.today() + timedelta(days=30)).isoformat()

    r, ms = await timed_request(client, "POST", "/recurring-invoices", json={
        "client_id": client_id,
        "name": "E2E_TEST_Recurrente mensual",
        "interval_type": "monthly",
        "next_run_date": next_run,
        "lines": [{"description": "E2E_TEST_Servicio mensual", "quantity": 1, "unit_price": 500.0, "tax_percentage": 21.0}],
    })
    if r.status_code == 201:
        rec_id = r.json()["id"]
        created_ids["recurring_invoices"].append(rec_id)
        ok(phase, "Crear recurrente", f"id={rec_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear recurrente", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/recurring-invoices")
    if r.status_code == 200:
        ok(phase, "Listar recurrentes", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar recurrentes", r.text[:100], ms, r.status_code)

    return rec_id


# ─── FASE 9: Contabilidad ────────────────────────────────────────────────────

async def phase_accounting(client: httpx.AsyncClient):
    phase = "9-Contabilidad"
    section("9. CONTABILIDAD")

    # Asiento contable
    now = datetime.now().isoformat()
    r, ms = await timed_request(client, "POST", "/accounting/journal", json={
        "date": now,
        "description": "E2E_TEST_Asiento contable",
        "lines": [
            {"account_code": "430", "account_name": "Clientes", "debit": 1210.0, "credit": 0.0},
            {"account_code": "700", "account_name": "Ventas", "debit": 0.0, "credit": 1000.0},
            {"account_code": "477", "account_name": "IVA repercutido", "debit": 0.0, "credit": 210.0},
        ],
    })
    if r.status_code in (200, 201):
        je_id = r.json().get("id", "")
        if je_id:
            created_ids["journal_entries"].append(je_id)
        ok(phase, "Crear asiento", f"id={str(je_id)[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear asiento", r.text[:100], ms, r.status_code)

    # Listar asientos
    r, ms = await timed_request(client, "GET", "/accounting/journal")
    if r.status_code == 200:
        ok(phase, "Listar asientos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar asientos", r.text[:100], ms, r.status_code)

    # Activos fijos
    r, ms = await timed_request(client, "GET", "/accounting/assets")
    if r.status_code == 200:
        ok(phase, "Listar activos fijos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar activos fijos", r.text[:100], ms, r.status_code)


# ─── FASE 10: CRM ────────────────────────────────────────────────────────────

async def phase_crm(client: httpx.AsyncClient, client_id: str):
    phase = "10-CRM"
    section("10. CRM")

    opp_id = ""

    if not client_id:
        skip(phase, "CRM", "Sin client_id")
        return

    # Oportunidad
    r, ms = await timed_request(client, "POST", "/crm/opportunities", json={
        "client_id": client_id,
        "title": "E2E_TEST_Oportunidad venta",
        "expected_value": 15000.0,
        "stage": "new",
    })
    if r.status_code == 201:
        opp_id = r.json()["id"]
        created_ids["opportunities"].append(opp_id)
        ok(phase, "Crear oportunidad", f"id={opp_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear oportunidad", r.text[:100], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/crm/opportunities")
    if r.status_code == 200:
        ok(phase, "Listar oportunidades", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar oportunidades", r.text[:100], ms, r.status_code)

    # Mover stage
    if opp_id:
        r, ms = await timed_request(client, "PATCH", f"/crm/opportunities/{opp_id}", json={"stage": "negotiation"})
        if r.status_code == 200:
            ok(phase, "Mover oportunidad a negotiation", "", ms, r.status_code)
        else:
            fail(phase, "Mover oportunidad", r.text[:100], ms, r.status_code)

    # Actividad
    r, ms = await timed_request(client, "POST", "/crm/activities", json={
        "client_id": client_id,
        "type": "call",
        "description": "E2E_TEST_Llamada de seguimiento",
    })
    if r.status_code == 201:
        act_id = r.json()["id"]
        created_ids["activities"].append(act_id)
        ok(phase, "Crear actividad", f"id={act_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear actividad", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/crm/activities")
    if r.status_code == 200:
        ok(phase, "Listar actividades", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar actividades", r.text[:100], ms, r.status_code)

    # Evento
    r, ms = await timed_request(client, "POST", "/crm/events", json={
        "client_id": client_id,
        "title": "E2E_TEST_Reunión comercial",
        "event_type": "meeting",
        "start_time": datetime.now().isoformat(),
        "end_time": (datetime.now() + timedelta(hours=1)).isoformat(),
    })
    if r.status_code == 201:
        evt_id = r.json()["id"]
        created_ids["events"].append(evt_id)
        ok(phase, "Crear evento", f"id={evt_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear evento", r.text[:100], ms, r.status_code)


# ─── FASE 11: RRHH ───────────────────────────────────────────────────────────

async def phase_hr(client: httpx.AsyncClient) -> str:
    phase = "11-RRHH"
    section("11. RECURSOS HUMANOS")
    emp_id = ""

    r, ms = await timed_request(client, "POST", "/hr/employees", json={
        "name": "E2E_TEST_Empleado",
        "nif": "12345678Z",
        "email": "e2e_empleado@test.com",
        "department": "IT",
        "role": "Developer",
        "base_salary": 30000.0,
        "irpf_rate": 15.0,
        "status": "active",
    })
    if r.status_code == 201:
        emp_id = r.json()["id"]
        created_ids["employees"].append(emp_id)
        ok(phase, "Crear empleado", f"id={emp_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear empleado", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/hr/employees")
    if r.status_code == 200:
        ok(phase, "Listar empleados", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar empleados", r.text[:100], ms, r.status_code)

    if emp_id:
        r, ms = await timed_request(client, "PATCH", f"/hr/employees/{emp_id}", json={"department": "Engineering"})
        if r.status_code == 200:
            ok(phase, "Actualizar empleado", "dept=Engineering", ms, r.status_code)
        else:
            fail(phase, "Actualizar empleado", r.text[:100], ms, r.status_code)

    # Nómina
    if emp_id:
        period_start = date.today().replace(day=1).isoformat()
        period_end = (date.today().replace(day=28)).isoformat()
        r, ms = await timed_request(client, "POST", "/hr/payrolls", json={
            "employee_id": emp_id,
            "period_start": period_start,
            "period_end": period_end,
            "issue_date": datetime.now().isoformat(),
            "base_salary": 2500.0,
            "net_salary": 2000.0,
            "irpf": 375.0,
            "deductions": 125.0,
        })
        if r.status_code == 201:
            pay_id = r.json()["id"]
            created_ids["payrolls"].append(pay_id)
            ok(phase, "Crear nómina", f"id={pay_id[:8]}…", ms, r.status_code)
        else:
            fail(phase, "Crear nómina", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/hr/payrolls")
    if r.status_code == 200:
        ok(phase, "Listar nóminas", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar nóminas", r.text[:100], ms, r.status_code)

    return emp_id


# ─── FASE 12: Proyectos ──────────────────────────────────────────────────────

async def phase_projects(client: httpx.AsyncClient):
    phase = "12-Proyectos"
    section("12. PROYECTOS")
    proj_id = ""

    r, ms = await timed_request(client, "POST", "/projects", json={
        "name": "E2E_TEST_Proyecto",
        "description": "Proyecto de prueba E2E",
        "budget": 50000.0,
        "status": "active",
    })
    if r.status_code == 201:
        proj_id = r.json()["id"]
        created_ids["projects"].append(proj_id)
        ok(phase, "Crear proyecto", f"id={proj_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear proyecto", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/projects")
    if r.status_code == 200:
        ok(phase, "Listar proyectos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar proyectos", r.text[:100], ms, r.status_code)

    # Tarea de proyecto
    if not proj_id:
        skip(phase, "Crear tarea proyecto", "Sin project_id")
        return

    r, ms = await timed_request(client, "POST", "/projects/tasks", json={
        "project_id": proj_id,
        "title": "E2E_TEST_Tarea proyecto",
        "description": "Tarea de prueba",
        "status": "todo",
    })
    if r.status_code == 201:
        task_id = r.json()["id"]
        created_ids["project_tasks"].append(task_id)
        ok(phase, "Crear tarea proyecto", f"id={task_id[:8]}…", ms, r.status_code)

        # Actualizar tarea
        r, ms = await timed_request(client, "PATCH", f"/projects/tasks/{task_id}", json={"status": "in_progress"})
        if r.status_code == 200:
            ok(phase, "Actualizar tarea", "status=in_progress", ms, r.status_code)
        else:
            fail(phase, "Actualizar tarea", r.text[:100], ms, r.status_code)
    else:
        fail(phase, "Crear tarea proyecto", r.text[:100], ms, r.status_code)


# ─── FASE 13: Banca ──────────────────────────────────────────────────────────

async def phase_banking(client: httpx.AsyncClient):
    phase = "13-Banca"
    section("13. BANCA")

    r, ms = await timed_request(client, "GET", "/banking/summary")
    if r.status_code == 200:
        ok(phase, "Resumen financiero", "", ms, r.status_code)
    else:
        fail(phase, "Resumen financiero", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/banking/transactions")
    if r.status_code == 200:
        ok(phase, "Listar transacciones", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar transacciones", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/banking/analytics")
    if r.status_code == 200:
        ok(phase, "Analytics banca", "", ms, r.status_code)
    else:
        fail(phase, "Analytics banca", r.text[:100], ms, r.status_code)


# ─── FASE 14: Documentos ─────────────────────────────────────────────────────

async def phase_documents(client: httpx.AsyncClient):
    phase = "14-Documentos"
    section("14. DOCUMENTOS")

    # Upload de un PDF ficticio
    fake_pdf = b"%PDF-1.4 E2E_TEST fake pdf content"
    r, ms = await timed_request(client, "POST", "/documents/upload",
                                 files={"file": ("e2e_test.pdf", fake_pdf, "application/pdf")})
    if r.status_code in (200, 201):
        doc_id = r.json().get("id", "")
        if doc_id:
            created_ids["documents"].append(doc_id)
        ok(phase, "Upload documento", f"id={str(doc_id)[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Upload documento", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/documents")
    if r.status_code == 200:
        ok(phase, "Listar documentos", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar documentos", r.text[:100], ms, r.status_code)


# ─── FASE 15: Workflows ──────────────────────────────────────────────────────

async def phase_workflows(client: httpx.AsyncClient):
    phase = "15-Workflows"
    section("15. AUTOMATIZACIONES / WORKFLOWS")
    wf_id = ""

    r, ms = await timed_request(client, "POST", "/workflows", json={
        "name": "E2E_TEST_Workflow",
        "description": "Workflow de prueba E2E",
        "trigger_type": "manual",
        "trigger_config": {},
        "action_type": "create_task",
        "action_config": {"domain": "chat", "user_intent": "E2E test action"},
    })
    if r.status_code == 201:
        wf_id = r.json()["id"]
        created_ids["workflows"].append(wf_id)
        ok(phase, "Crear workflow", f"id={wf_id[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear workflow", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/workflows")
    if r.status_code == 200:
        ok(phase, "Listar workflows", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Listar workflows", r.text[:100], ms, r.status_code)

    if wf_id:
        r, ms = await timed_request(client, "POST", f"/workflows/{wf_id}/run")
        if r.status_code in (200, 201, 202):
            ok(phase, "Ejecutar workflow", "", ms, r.status_code)
        else:
            fail(phase, "Ejecutar workflow", r.text[:100], ms, r.status_code)


# ─── FASE 16: AI Employees ───────────────────────────────────────────────────

async def phase_ai_employees(client: httpx.AsyncClient):
    phase = "16-AIEmployees"
    section("16. AI EMPLOYEES")

    # Seed built-ins
    r, ms = await timed_request(client, "POST", "/ai-employees/seed")
    if r.status_code in (200, 201):
        ok(phase, "Seed AI employees", "", ms, r.status_code)
    else:
        fail(phase, "Seed AI employees", r.text[:100], ms, r.status_code)

    # Listar
    r, ms = await timed_request(client, "GET", "/ai-employees")
    if r.status_code == 200:
        count = len(r.json())
        ok(phase, "Listar AI employees", f"count={count}", ms, r.status_code)
    else:
        fail(phase, "Listar AI employees", r.text[:100], ms, r.status_code)

    # Crear custom
    r, ms = await timed_request(client, "POST", "/ai-employees", json={
        "name": "E2E_TEST_AI_Worker",
        "role_description": "Asistente de pruebas E2E",
        "budget_limit_usd": 1.0,
    })
    if r.status_code == 201:
        ai_id = r.json().get("id", "")
        if ai_id:
            created_ids["ai_employees"].append(ai_id)
        ok(phase, "Crear AI employee", f"id={str(ai_id)[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Crear AI employee", r.text[:100], ms, r.status_code)


# ─── FASE 17: Generative UI ──────────────────────────────────────────────────

async def phase_generative_ui(client: httpx.AsyncClient):
    phase = "17-GenerativeUI"
    section("17. GENERATIVE UI")

    r, ms = await timed_request(client, "POST", "/generative-ui/generate", json={
        "prompt": "Dashboard de ventas del mes con gráfico de barras",
        "title": "E2E_TEST_Dashboard",
    })
    if r.status_code in (200, 201):
        gui_id = r.json().get("id", "")
        if gui_id:
            created_ids["generative_ui"].append(gui_id)
        ok(phase, "Generar UI", f"id={str(gui_id)[:8]}…", ms, r.status_code)
    else:
        fail(phase, "Generar UI", r.text[:100], ms, r.status_code)

    r, ms = await timed_request(client, "GET", "/generative-ui/history")
    if r.status_code == 200:
        ok(phase, "Historial UI", f"count={len(r.json())}", ms, r.status_code)
    else:
        fail(phase, "Historial UI", r.text[:100], ms, r.status_code)


# ─── FASE 18: Agentes IA (16 dominios) ───────────────────────────────────────

AGENT_PROMPTS = [
    ("billing", "Lista las facturas emitidas este mes"),
    ("hr", "Lista empleados activos y calcula coste salarial total"),
    ("crm", "Muestra oportunidades de venta abiertas"),
    ("banking", "Dame resumen financiero del mes actual"),
    ("compliance", "Verifica obligaciones fiscales pendientes"),
    ("documents", "Lista documentos recientes del tenant"),
    ("excel", "Genera informe Excel con facturas del trimestre"),
    ("email", "Redacta email de cobro para facturas vencidas"),
    ("workflow", "Lista automatizaciones activas"),
    ("rag", "Busca info sobre facturación electrónica en España"),
    ("recruitment", "Lista ofertas de empleo publicadas"),
    ("marketing", "Sugiere ideas de campaña para Q2 2026"),
    ("chat", "Hola, ¿qué funcionalidades tiene AutomatizaPyme?"),
]


async def phase_agents(client: httpx.AsyncClient):
    phase = "18-Agentes"
    section("18. AGENTES IA — PRUEBA POR DOMINIO")

    if ARGS.skip_agents:
        skip(phase, "Agentes IA", "--skip-agents activado")
        return

    launched: list[tuple[str, str]] = []  # (domain, task_id)

    for domain, prompt in AGENT_PROMPTS:
        r, ms = await timed_request(client, "POST", "/tasks", json={
            "domain": domain,
            "user_intent": prompt,
        })
        if r.status_code in (200, 201):
            task_id = r.json()["id"]
            created_ids["tasks"].append(task_id)
            launched.append((domain, task_id))
            ok(phase, f"Lanzar tarea [{domain}]", f"task_id={task_id[:8]}…", ms, r.status_code)
        else:
            fail(phase, f"Lanzar tarea [{domain}]", r.text[:80], ms, r.status_code)
        await asyncio.sleep(2)  # Rate-limit mitigation

    info(f"Esperando {len(launched)} agentes (máx 180s cada uno)…")

    for domain, task_id in launched:
        result = await poll_task(client, task_id, max_wait=180)
        if result:
            status = result["status"]
            if status == "done":
                agent_results = result.get("agent_results", result.get("result", ""))
                summary = str(agent_results)[:80] if agent_results else "sin resultado"
                ok(phase, f"Agente [{domain}] completado", summary)
            else:
                error = result.get("error") or result.get("error_message") or result.get("result") or "sin detalle"
                fail(phase, f"Agente [{domain}] falló", str(error)[:100])
        else:
            fail(phase, f"Agente [{domain}] timeout", "180s sin respuesta")


# ─── FASE 19: Coordinador Multi-agente ───────────────────────────────────────

async def phase_coordinator(client: httpx.AsyncClient):
    phase = "19-Coordinador"
    section("19. COORDINADOR MULTI-AGENTE")

    if ARGS.skip_agents:
        skip(phase, "Coordinador", "--skip-agents activado")
        return

    tasks_to_test = [
        ("Genera presupuesto de 5000 EUR para el cliente E2E y crea oportunidad CRM", "coordinator"),
        ("Revisa tareas pendientes del equipo y genera resumen", "coordinator"),
    ]

    for prompt, domain in tasks_to_test:
        r, ms = await timed_request(client, "POST", "/tasks", json={
            "domain": domain,
            "user_intent": prompt,
        })
        if r.status_code in (200, 201):
            task_id = r.json()["id"]
            created_ids["tasks"].append(task_id)
            ok(phase, f"Lanzar coordinador", f"task_id={task_id[:8]}…", ms, r.status_code)

            result = await poll_task(client, task_id, max_wait=180)
            if result:
                if result["status"] == "done":
                    ok(phase, "Coordinador completado", str(result.get("agent_results", ""))[:80])
                else:
                    error_detail = result.get("error") or result.get("error_message") or result.get("result") or "sin detalle"
                    fail(phase, "Coordinador falló", f"(requiere LLM) {str(error_detail)[:80]}")
            else:
                fail(phase, "Coordinador timeout", "180s")
        else:
            fail(phase, "Lanzar coordinador", r.text[:80], ms, r.status_code)

        await asyncio.sleep(3)


# ─── FASE 20: Cleanup ────────────────────────────────────────────────────────

async def phase_cleanup(client: httpx.AsyncClient):
    phase = "20-Cleanup"
    section("20. LIMPIEZA DE DATOS E2E")

    delete_routes = {
        "generative_ui": "/generative-ui/{id}",
        "ai_employees": "/ai-employees/{id}",
        "workflows": "/workflows/{id}",
        "project_tasks": "/projects/tasks/{id}",
        "projects": "/projects/{id}",
        "journal_entries": "/accounting/journal/{id}",
        "payrolls": None,  # no DELETE endpoint typically
        "employees": "/hr/employees/{id}",
        "events": "/crm/events/{id}",
        "activities": "/crm/activities/{id}",
        "opportunities": "/crm/opportunities/{id}",
        "recurring_invoices": "/recurring-invoices/{id}",
        "purchase_orders": "/purchase-orders/{id}",
        "sales_orders": "/orders/{id}",
        "quotes": "/quotes/{id}",
        "invoices": "/invoices/{id}",
        "products": "/products/{id}",
        "clients": "/clients/{id}",
    }

    total_deleted = 0
    total_failed = 0

    for entity, route_template in delete_routes.items():
        if not route_template:
            continue
        ids = created_ids.get(entity, [])
        for eid in ids:
            try:
                url = route_template.replace("{id}", str(eid))
                r, ms = await timed_request(client, "DELETE", url)
                if r.status_code in (200, 204):
                    total_deleted += 1
                else:
                    total_failed += 1
            except Exception:
                total_failed += 1

    # Cleanup tasks
    try:
        r, _ = await timed_request(client, "DELETE", "/tasks/cleanup")
        if r.status_code in (200, 204):
            info("Tasks cleanup OK")
    except Exception:
        pass

    ok(phase, "Cleanup completado", f"deleted={total_deleted} failed={total_failed}")


# ─── Reporte ──────────────────────────────────────────────────────────────────

def print_summary():
    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")

    print(f"\n{'═' * 60}")
    print(f"  RESUMEN FINAL")
    print(f"{'═' * 60}")
    print(f"  Total:    {total}")
    print(f"  {PASS_ICON} PASS:   {passed}")
    print(f"  {FAIL_ICON} FAIL:   {failed}")
    print(f"  {SKIP_ICON} SKIP:   {skipped}")
    print(f"  Tasa éxito: {passed / max(total, 1) * 100:.1f}%")

    # Slowest endpoints
    timed = sorted([r for r in results if r.response_ms > 0], key=lambda r: r.response_ms, reverse=True)
    if timed:
        print(f"\n  ⏱️  Top 5 más lentos:")
        for r in timed[:5]:
            print(f"    {r.response_ms:>7.0f}ms  {r.test_name}")

    # Failures detail
    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        print(f"\n  {FAIL_ICON} Detalle de fallos:")
        for r in failures:
            print(f"    [{r.phase}] {r.test_name}")
            if r.error:
                print(f"      → {r.error[:120]}")

    print(f"\n{'═' * 60}")


def save_json_report(duration_s: float):
    report_dir = Path(ARGS.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    report_path = report_dir / f"e2e_report_{timestamp}.json"

    total = len(results)
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    skipped = sum(1 for r in results if r.status == "SKIP")

    report = {
        "timestamp": datetime.now().isoformat(),
        "base_url": ARGS.base_url,
        "email": ARGS.email,
        "skip_agents": ARGS.skip_agents,
        "duration_seconds": round(duration_s, 2),
        "summary": {
            "total": total,
            "pass": passed,
            "fail": failed,
            "skip": skipped,
            "success_rate": round(passed / max(total, 1) * 100, 1),
        },
        "results": [asdict(r) for r in results],
        "slowest": [
            {"test": r.test_name, "ms": round(r.response_ms, 1)}
            for r in sorted(
                [r for r in results if r.response_ms > 0],
                key=lambda r: r.response_ms, reverse=True,
            )[:10]
        ],
        "errors": [
            {"phase": r.phase, "test": r.test_name, "error": r.error, "http_status": r.http_status}
            for r in results if r.status == "FAIL"
        ],
    }

    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  📄 Reporte JSON guardado en: {report_path}")
    return report_path


# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    global ARGS
    ARGS = parser.parse_args()

    print(f"\n{'═' * 60}")
    print("  AUTOMATIZAPYME — TEST FUNCIONAL COMPLETO")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Base URL: {ARGS.base_url}")
    print(f"  Usuario: {ARGS.email}")
    print(f"  Skip agents: {ARGS.skip_agents}")
    print(f"{'═' * 60}")

    t_start = time.perf_counter()

    async with httpx.AsyncClient(base_url=ARGS.base_url, timeout=60.0, follow_redirects=True) as http:

        # Fase 0: Health
        server_ok = await phase_health(http)
        if not server_ok:
            print(f"\n{FAIL_ICON} Servidor no accesible. Abortando.")
            print_summary()
            return

        # Fase 1: Auth (FATAL si falla)
        auth_ok = await phase_auth(http)
        if not auth_ok:
            print(f"\n{FAIL_ICON} No se pudo autenticar. Abortando.")
            print_summary()
            return

        # Fases ERP
        try:
            client_id, supplier_id = await phase_clients(http)
        except Exception as e:
            fail("2-Clientes", "EXCEPCIÓN", str(e)[:100])
            client_id, supplier_id = "", ""

        try:
            prod_id, svc_id = await phase_products(http)
        except Exception as e:
            fail("3-Productos", "EXCEPCIÓN", str(e)[:100])
            prod_id, svc_id = "", ""

        try:
            invoice_id = await phase_invoices(http, client_id, prod_id)
        except Exception as e:
            fail("4-Facturas", "EXCEPCIÓN", str(e)[:100])

        try:
            await phase_quotes(http, client_id)
        except Exception as e:
            fail("5-Presupuestos", "EXCEPCIÓN", str(e)[:100])

        try:
            await phase_sales_orders(http, client_id, prod_id)
        except Exception as e:
            fail("6-PedidosVenta", "EXCEPCIÓN", str(e)[:100])

        try:
            await phase_purchase_orders(http, supplier_id, prod_id)
        except Exception as e:
            fail("7-PedidosCompra", "EXCEPCIÓN", str(e)[:100])

        try:
            await phase_recurring(http, client_id)
        except Exception as e:
            fail("8-Recurrentes", "EXCEPCIÓN", str(e)[:100])

        # Contabilidad
        try:
            await phase_accounting(http)
        except Exception as e:
            fail("9-Contabilidad", "EXCEPCIÓN", str(e)[:100])

        # CRM
        try:
            await phase_crm(http, client_id)
        except Exception as e:
            fail("10-CRM", "EXCEPCIÓN", str(e)[:100])

        # RRHH
        try:
            emp_id = await phase_hr(http)
        except Exception as e:
            fail("11-RRHH", "EXCEPCIÓN", str(e)[:100])

        # Proyectos
        try:
            await phase_projects(http)
        except Exception as e:
            fail("12-Proyectos", "EXCEPCIÓN", str(e)[:100])

        # Banca
        try:
            await phase_banking(http)
        except Exception as e:
            fail("13-Banca", "EXCEPCIÓN", str(e)[:100])

        # Documentos
        try:
            await phase_documents(http)
        except Exception as e:
            fail("14-Documentos", "EXCEPCIÓN", str(e)[:100])

        # Workflows
        try:
            await phase_workflows(http)
        except Exception as e:
            fail("15-Workflows", "EXCEPCIÓN", str(e)[:100])

        # AI Employees
        try:
            await phase_ai_employees(http)
        except Exception as e:
            fail("16-AIEmployees", "EXCEPCIÓN", str(e)[:100])

        # Generative UI
        try:
            await phase_generative_ui(http)
        except Exception as e:
            fail("17-GenerativeUI", "EXCEPCIÓN", str(e)[:100])

        # Agentes IA
        try:
            await phase_agents(http)
        except Exception as e:
            fail("18-Agentes", "EXCEPCIÓN", str(e)[:100])

        # Coordinador
        try:
            await phase_coordinator(http)
        except Exception as e:
            fail("19-Coordinador", "EXCEPCIÓN", str(e)[:100])

        # Cleanup
        try:
            await phase_cleanup(http)
        except Exception as e:
            fail("20-Cleanup", "EXCEPCIÓN", str(e)[:100])

    duration = time.perf_counter() - t_start
    print_summary()
    save_json_report(duration)
    print(f"  Duración total: {duration:.1f}s")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    asyncio.run(main())
