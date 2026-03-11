"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          AUTOMATIZAPYME — TEST INTEGRAL DEL SISTEMA                         ║
║  Simula el cerebro IA probando TODAS las funcionalidades via API             ║
║  Ejecutar desde el contenedor: docker-compose exec api python full_system_test.py
║  O local: python scripts/full_system_test.py                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
import json
import time
from datetime import date, datetime, timedelta

import httpx

BASE_URL = "http://localhost:8080/api/v1"
HEADERS: dict = {}

# ─── Utilidades ───────────────────────────────────────────────────────────────

PASS = "✅"
FAIL = "❌"
SKIP = "⚠️ "
INFO = "ℹ️ "

results: list[dict] = []


def ok(section: str, detail: str = ""):
    msg = f"  {PASS} {section}"
    if detail:
        msg += f" → {detail}"
    print(msg)
    results.append({"status": "PASS", "section": section, "detail": detail})


def fail(section: str, detail: str = ""):
    msg = f"  {FAIL} {section}"
    if detail:
        msg += f" → {detail}"
    print(msg)
    results.append({"status": "FAIL", "section": section, "detail": detail})


def info(msg: str):
    print(f"  {INFO} {msg}")


def section(title: str):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


async def poll_task(client: httpx.AsyncClient, task_id: str, max_wait: int = 60) -> dict | None:
    """Espera a que una tarea IA termine (done/failed) con timeout."""
    for _ in range(max_wait):
        r = await client.get(f"/tasks/{task_id}", headers=HEADERS)
        if r.status_code == 200:
            t = r.json()
            if t["status"] in ("done", "failed"):
                return t
        await asyncio.sleep(1)
    return None


# ─── 1. AUTH ──────────────────────────────────────────────────────────────────

async def test_auth(client: httpx.AsyncClient) -> bool:
    section("1. AUTENTICACIÓN")

    r = await client.post("/auth/register", json={
        "email": "test_integral@automatizapyme.com",
        "password": "Test1234!",
        "full_name": "Test Integral",
        "tenant": {"name": "Test Corp SA", "nif": "B99887766"},
    })
    if r.status_code in (201, 400):
        ok("Registro usuario de test", f"status={r.status_code}")
    else:
        fail("Registro usuario de test", r.text[:100])

    r = await client.post("/auth/login", json={
        "email": "test_integral@automatizapyme.com",
        "password": "Test1234!",
    })
    if r.status_code == 200:
        token = r.json()["access_token"]
        HEADERS["Authorization"] = f"Bearer {token}"
        ok("Login y obtención de JWT")
        return True
    else:
        fail("Login", r.text[:100])
        return False


# ─── 2. ERP — Clientes / Proveedores ─────────────────────────────────────────

async def test_clientes(client: httpx.AsyncClient) -> tuple[str, str]:
    section("2. ERP — CLIENTES & PROVEEDORES")
    client_id = supplier_id = ""

    # Crear cliente
    r = await client.post("/clients", headers=HEADERS, json={
        "nif": "B12345001", "name": "Industrias Prueba SL",
        "email": "contabilidad@prueba.test", "city": "Madrid",
        "postal_code": "28001", "client_type": "customer",
    })
    if r.status_code == 201:
        client_id = r.json()["id"]
        ok("Crear cliente", f"id={client_id[:8]}…")
    else:
        fail("Crear cliente", r.text[:100])

    # Listar clientes
    r = await client.get("/clients", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar clientes", f"{len(r.json())} registros")
    else:
        fail("Listar clientes")

    # Filtrar por tipo
    r = await client.get("/clients?client_type=customer", headers=HEADERS)
    if r.status_code == 200:
        ok("Filtrar clientes por tipo=customer", f"{len(r.json())} encontrados")

    # Crear proveedor
    r = await client.post("/clients", headers=HEADERS, json={
        "nif": "B98765432", "name": "Suministros Global SA",
        "email": "pedidos@suministros.test", "city": "Barcelona",
        "client_type": "supplier",
    })
    if r.status_code == 201:
        supplier_id = r.json()["id"]
        ok("Crear proveedor", f"id={supplier_id[:8]}…")
    else:
        fail("Crear proveedor", r.text[:100])

    # Filtrar proveedores
    r = await client.get("/clients?client_type=supplier", headers=HEADERS)
    if r.status_code == 200:
        ok("Filtrar proveedores", f"{len(r.json())} encontrados")

    # Editar cliente
    if client_id:
        r = await client.patch(f"/clients/{client_id}", headers=HEADERS, json={"city": "Valencia"})
        if r.status_code == 200 and r.json()["city"] == "Valencia":
            ok("Editar cliente (PATCH)", "ciudad actualizada")
        else:
            fail("Editar cliente", r.text[:80])

    return client_id, supplier_id


# ─── 3. ERP — Catálogo de Productos con Stock ─────────────────────────────────

async def test_productos(client: httpx.AsyncClient) -> tuple[str, str]:
    section("3. ERP — CATÁLOGO & STOCK")
    prod_id = svc_id = ""

    # Crear producto físico con stock
    r = await client.post("/products", headers=HEADERS, json={
        "item_type": "product", "sku": "TEST-001",
        "name": "Servidor NAS 8TB", "description": "NAS de alta capacidad",
        "price": 1200.0, "tax_percentage": 21.0,
        "stock_quantity": 10, "stock_min_alert": 2,
    })
    if r.status_code == 201:
        prod_id = r.json()["id"]
        ok("Crear producto con stock=10", f"id={prod_id[:8]}…")
    else:
        fail("Crear producto", r.text[:100])

    # Crear servicio
    r = await client.post("/products", headers=HEADERS, json={
        "item_type": "service", "sku": "SRV-001",
        "name": "Consultoría IT mensual", "price": 800.0, "tax_percentage": 21.0,
    })
    if r.status_code == 201:
        svc_id = r.json()["id"]
        ok("Crear servicio", f"id={svc_id[:8]}…")
    else:
        fail("Crear servicio", r.text[:100])

    # Listar
    r = await client.get("/products", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar productos", f"{len(r.json())} registros")

    # Movimiento entrada de stock
    if prod_id:
        r = await client.post(f"/products/{prod_id}/stock-movements", headers=HEADERS, json={
            "movement_type": "entrada", "quantity": 5,
            "reference": "ALB-2026-001", "notes": "Recepción proveedor global",
        })
        if r.status_code == 201:
            mv = r.json()
            ok("Movimiento stock: ENTRADA +5", f"stock_after={mv['stock_after']}")
        else:
            fail("Movimiento entrada stock", r.text[:100])

        # Movimiento salida de stock
        r = await client.post(f"/products/{prod_id}/stock-movements", headers=HEADERS, json={
            "movement_type": "salida", "quantity": 3, "reference": "PED-001",
        })
        if r.status_code == 201:
            mv = r.json()
            ok("Movimiento stock: SALIDA -3", f"stock_after={mv['stock_after']}")
        else:
            fail("Movimiento salida stock", r.text[:100])

        # Ajuste de stock
        r = await client.post(f"/products/{prod_id}/stock-movements", headers=HEADERS, json={
            "movement_type": "ajuste", "quantity": 20, "notes": "Inventario anual",
        })
        if r.status_code == 201:
            mv = r.json()
            ok("Movimiento stock: AJUSTE → 20", f"stock_after={mv['stock_after']}")
        else:
            fail("Movimiento ajuste stock", r.text[:100])

        # Listar movimientos
        r = await client.get(f"/products/{prod_id}/stock-movements", headers=HEADERS)
        if r.status_code == 200:
            ok("Listar movimientos de stock", f"{len(r.json())} movimientos")

    return prod_id, svc_id


# ─── 4. ERP — Facturas ────────────────────────────────────────────────────────

async def test_facturas(client: httpx.AsyncClient, client_id: str, prod_id: str) -> str:
    section("4. ERP — FACTURAS")
    invoice_id = ""

    if not client_id or not prod_id:
        fail("Facturas (sin client_id o prod_id)")
        return invoice_id

    # Crear factura con líneas
    r = await client.post(f"/clients/{client_id}/invoices", headers=HEADERS, json={
        "invoice_number": "FAC-TEST-001",
        "date": datetime.now().isoformat(),
        "due_date": (datetime.now() + timedelta(days=30)).isoformat(),
        "status": "draft", "invoice_type": "issued",
        "notes": "Factura de prueba integral",
        "lines": [
            {"description": "Servidor NAS 8TB", "product_id": prod_id, "quantity": 2, "unit_price": 1200.0, "tax_percentage": 21.0, "discount_percentage": 5.0},
            {"description": "Consultoría IT — Marzo 2026", "quantity": 1, "unit_price": 800.0, "tax_percentage": 21.0, "discount_percentage": 0.0},
        ]
    })
    if r.status_code == 201:
        inv = r.json()
        invoice_id = inv["id"]
        ok("Crear factura con 2 líneas", f"total={inv['amount_total']}€ id={invoice_id[:8]}…")
    else:
        fail("Crear factura", r.text[:100])
        return invoice_id

    # Listar facturas
    r = await client.get("/invoices", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar facturas", f"{len(r.json())} registros")

    # Ver detalle
    r = await client.get(f"/invoices/{invoice_id}", headers=HEADERS)
    if r.status_code == 200:
        inv = r.json()
        ok("Detalle factura", f"líneas={len(inv['lines'])} base={inv['amount_base']}€")

    # Cambiar estado draft → pending
    r = await client.patch(f"/invoices/{invoice_id}/status", headers=HEADERS, json={"status": "pending"})
    if r.status_code == 200 and r.json()["status"] == "pending":
        ok("Cambio estado factura: draft → pending")
    else:
        fail("Cambio estado factura", r.text[:80])

    # Marcar como pagada
    r = await client.patch(f"/invoices/{invoice_id}/status", headers=HEADERS, json={"status": "paid"})
    if r.status_code == 200 and r.json()["status"] == "paid":
        ok("Cambio estado factura: pending → paid")

    # Descargar PDF
    r = await client.get(f"/invoices/{invoice_id}/pdf", headers=HEADERS)
    if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf"):
        ok("Descargar PDF de factura", f"size={len(r.content)} bytes")
    else:
        fail("Descargar PDF", f"status={r.status_code}")

    return invoice_id


# ─── 5. ERP — Presupuestos ────────────────────────────────────────────────────

async def test_presupuestos(client: httpx.AsyncClient, client_id: str) -> str:
    section("5. ERP — PRESUPUESTOS")
    quote_id = ""

    if not client_id:
        fail("Presupuestos (sin client_id)")
        return quote_id

    r = await client.post("/quotes", headers=HEADERS, json={
        "client_id": client_id,
        "date": datetime.now().isoformat(),
        "valid_until": (datetime.now() + timedelta(days=15)).isoformat(),
        "status": "draft",
        "notes": "Oferta para proyecto de digitalización",
        "lines": [
            {"description": "Análisis inicial", "quantity": 1, "unit_price": 500.0, "tax_percentage": 21.0},
            {"description": "Desarrollo plataforma", "quantity": 40, "unit_price": 75.0, "tax_percentage": 21.0},
        ]
    })
    if r.status_code == 201:
        quote_id = r.json()["id"]
        ok("Crear presupuesto con 2 líneas", f"total={r.json()['amount_total']}€")
    else:
        fail("Crear presupuesto", r.text[:100])
        return quote_id

    # Convertir a factura
    r = await client.post(f"/quotes/{quote_id}/convert-to-invoice", headers=HEADERS)
    if r.status_code == 200:
        ok("Convertir presupuesto → factura", f"invoice_id={r.json().get('invoice_id', '?')[:8]}…")
    else:
        fail("Convertir presupuesto a factura", r.text[:100])

    return quote_id


# ─── 6. ERP — Pedidos de Venta ────────────────────────────────────────────────

async def test_pedidos_venta(client: httpx.AsyncClient, client_id: str, prod_id: str) -> str:
    section("6. ERP — PEDIDOS DE VENTA")
    order_id = ""

    if not client_id:
        fail("Pedidos venta (sin client_id)")
        return order_id

    r = await client.post("/orders", headers=HEADERS, json={
        "client_id": client_id,
        "expected_delivery": (datetime.now() + timedelta(days=7)).isoformat(),
        "notes": "Urgente — entrega en almacén central",
        "lines": [
            {"description": "Servidor NAS 8TB", "product_id": prod_id, "quantity": 2, "unit_price": 1200.0, "tax_percentage": 21.0, "discount_percentage": 0.0},
        ]
    })
    if r.status_code == 201:
        order = r.json()
        order_id = order["id"]
        ok("Crear pedido de venta", f"num={order['order_number']} total={order['amount_total']}€")
    else:
        fail("Crear pedido de venta", r.text[:100])
        return order_id

    # Avanzar estado: draft → confirmed → processing → shipped
    for next_status in ["confirmed", "processing", "shipped", "delivered"]:
        r = await client.patch(f"/orders/{order_id}", headers=HEADERS, json={"status": next_status})
        if r.status_code == 200:
            ok(f"Pedido venta: → {next_status}")
        else:
            fail(f"Pedido venta estado {next_status}", r.text[:80])
            break

    return order_id


# ─── 7. ERP — Pedidos de Compra ───────────────────────────────────────────────

async def test_pedidos_compra(client: httpx.AsyncClient, supplier_id: str, prod_id: str) -> str:
    section("7. ERP — PEDIDOS DE COMPRA")
    po_id = ""

    if not supplier_id:
        fail("Pedidos compra (sin supplier_id)")
        return po_id

    r = await client.post("/purchase-orders", headers=HEADERS, json={
        "supplier_id": supplier_id,
        "expected_delivery": (datetime.now() + timedelta(days=5)).isoformat(),
        "notes": "Reposición urgente de stock",
        "lines": [
            {"description": "Servidor NAS 8TB", "product_id": prod_id, "quantity": 10, "unit_price": 950.0, "tax_percentage": 21.0},
            {"description": "Cables y accesorios", "quantity": 20, "unit_price": 15.0, "tax_percentage": 21.0},
        ]
    })
    if r.status_code == 201:
        po = r.json()
        po_id = po["id"]
        ok("Crear pedido de compra", f"num={po['order_number']} total={po['amount_total']}€")
    else:
        fail("Crear pedido de compra", r.text[:100])
        return po_id

    # Flujo: draft → sent → confirmed → received
    for next_status in ["sent", "confirmed", "received"]:
        r = await client.patch(f"/purchase-orders/{po_id}", headers=HEADERS, json={"status": next_status})
        if r.status_code == 200:
            ok(f"Pedido compra: → {next_status}")
        else:
            fail(f"Pedido compra estado {next_status}", r.text[:80])
            break

    return po_id


# ─── 8. ERP — Facturación Recurrente ─────────────────────────────────────────

async def test_recurrentes(client: httpx.AsyncClient, client_id: str) -> str:
    section("8. ERP — FACTURACIÓN RECURRENTE")
    rec_id = ""

    if not client_id:
        fail("Recurrentes (sin client_id)")
        return rec_id

    r = await client.post("/recurring-invoices", headers=HEADERS, json={
        "client_id": client_id,
        "name": "Mantenimiento mensual IT",
        "interval_type": "monthly",
        "next_run_date": date.today().isoformat(),  # Hoy → vencida desde ya
        "notes": "Cuota mensual de mantenimiento y soporte técnico",
        "lines": [
            {"description": "Soporte técnico mensual", "quantity": 1, "unit_price": 350.0, "tax_percentage": 21.0},
            {"description": "Licencias software", "quantity": 5, "unit_price": 45.0, "tax_percentage": 21.0},
        ]
    })
    if r.status_code == 201:
        rec = r.json()
        rec_id = rec["id"]
        ok("Crear plantilla recurrente mensual", f"importe={350 + 5*45}€ base")
    else:
        fail("Crear plantilla recurrente", r.text[:100])
        return rec_id

    # Listar
    r = await client.get("/recurring-invoices", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar plantillas recurrentes", f"{len(r.json())} plantillas")

    # Ejecutar manualmente ahora
    r = await client.post(f"/recurring-invoices/{rec_id}/run", headers=HEADERS)
    if r.status_code == 200 or r.status_code == 201:
        inv = r.json()
        ok("Ejecutar plantilla → factura generada", f"num={inv.get('invoice_number')} total={inv.get('amount_total')}€")
    else:
        fail("Ejecutar plantilla recurrente", r.text[:100])

    # Pausar
    r = await client.patch(f"/recurring-invoices/{rec_id}", headers=HEADERS, json={"is_active": False})
    if r.status_code == 200 and not r.json()["is_active"]:
        ok("Pausar plantilla recurrente")

    return rec_id


# ─── 9. Contabilidad ──────────────────────────────────────────────────────────

async def test_contabilidad(client: httpx.AsyncClient) -> None:
    section("9. CONTABILIDAD — LIBRO DIARIO & ACTIVOS")

    # Asiento contable cuadrado
    r = await client.post("/accounting/journal", headers=HEADERS, json={
        "date": datetime.now().isoformat(),
        "description": "Venta servicios IT — FAC-TEST-001",
        "reference_id": "FAC-TEST-001",
        "lines": [
            {"account_code": "430", "account_name": "Clientes", "debit": 3025.0, "credit": 0.0},
            {"account_code": "705", "account_name": "Prestaciones de servicios", "debit": 0.0, "credit": 2500.0},
            {"account_code": "477", "account_name": "HP, IVA repercutido", "debit": 0.0, "credit": 525.0},
        ]
    })
    if r.status_code == 201:
        ok("Asiento contable equilibrado (Debe=Haber=3025€)")
    else:
        fail("Asiento contable", r.text[:100])

    # Asiento descuadrado (debe fallar)
    r = await client.post("/accounting/journal", headers=HEADERS, json={
        "date": datetime.now().isoformat(),
        "description": "Asiento descuadrado — debe dar error",
        "lines": [
            {"account_code": "430", "account_name": "Clientes", "debit": 1000.0, "credit": 0.0},
            {"account_code": "705", "account_name": "Ventas", "debit": 0.0, "credit": 500.0},
        ]
    })
    if r.status_code == 400:
        ok("Validación asiento descuadrado (correctamente rechazado)", "400 Bad Request")
    else:
        fail("Validación asiento descuadrado", f"esperado 400, recibido {r.status_code}")

    # Listar asientos
    r = await client.get("/accounting/journal", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar libro diario", f"{len(r.json())} asientos")

    # Activo fijo
    r = await client.post("/accounting/assets", headers=HEADERS, json={
        "name": "Servidor HP ProLiant DL380",
        "category": "equipment",
        "purchase_date": "2025-01-15",
        "purchase_value": 8500.0,
        "useful_life_years": 5.0,
        "residual_value": 500.0,
        "depreciation_method": "linear",
        "account_code": "213",
        "notes": "Servidor principal para servicios cloud",
    })
    if r.status_code == 201:
        asset = r.json()
        ok("Crear activo fijo", f"id={asset['id'][:8]}… valor={asset['purchase_value']}€")

        # Editar activo
        r2 = await client.patch(f"/accounting/assets/{asset['id']}", headers=HEADERS, json={"notes": "Ampliado a 12TB RAM"})
        if r2.status_code == 200:
            ok("Editar activo fijo")

    # Listar activos
    r = await client.get("/accounting/assets", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar activos fijos", f"{len(r.json())} activos")


# ─── 10. CRM ──────────────────────────────────────────────────────────────────

async def test_crm(client: httpx.AsyncClient, client_id: str) -> None:
    section("10. CRM — OPORTUNIDADES, ACTIVIDADES, EVENTOS, RESERVAS")

    # Oportunidades
    r = await client.post("/crm/opportunities", headers=HEADERS, json={
        "name": "Proyecto digitalización planta",
        "client_id": client_id or None,
        "stage": "qualified",
        "amount": 45000.0,
        "probability": 65,
        "expected_close_date": (datetime.now() + timedelta(days=45)).isoformat(),
        "description": "Modernización línea de producción con IoT y ERP integrado",
    })
    opp_id = ""
    if r.status_code == 201:
        opp_id = r.json()["id"]
        ok("Crear oportunidad CRM", f"valor=45000€ prob=65% id={opp_id[:8]}…")
    else:
        fail("Crear oportunidad", r.text[:100])

    if opp_id:
        # Mover a propuesta
        r = await client.patch(f"/crm/opportunities/{opp_id}", headers=HEADERS, json={"stage": "proposal", "probability": 80})
        if r.status_code == 200:
            ok("Avanzar oportunidad: qualified → proposal (80%)")

        # Cerrar ganada
        r = await client.patch(f"/crm/opportunities/{opp_id}", headers=HEADERS, json={"stage": "won"})
        if r.status_code == 200:
            ok("Cerrar oportunidad: WON 🏆")

    # Actividades
    r = await client.post("/crm/activities", headers=HEADERS, json={
        "client_id": client_id or None,
        "opportunity_id": opp_id or None,
        "type": "call",
        "description": "Llamada inicial con director de operaciones. Interés alto en el proyecto.",
        "metadata_json": {"duration_min": 45, "outcome": "follow_up_meeting"},
    })
    if r.status_code == 201:
        ok("Crear actividad CRM (llamada)", f"id={r.json()['id'][:8]}…")
    else:
        fail("Crear actividad", r.text[:100])

    r = await client.post("/crm/activities", headers=HEADERS, json={
        "client_id": client_id or None,
        "type": "note",
        "description": "Cliente solicita propuesta detallada con desglose de ROI para presentar al consejo.",
    })
    if r.status_code == 201:
        ok("Crear nota CRM")

    # Listar actividades
    r = await client.get("/crm/activities", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar actividades CRM", f"{len(r.json())} registros")

    # Eventos / Calendario
    now = datetime.now()
    r = await client.post("/crm/events", headers=HEADERS, json={
        "title": "Reunión kick-off proyecto digitalización",
        "description": "Primera reunión con el equipo del cliente para definir alcance",
        "start_time": (now + timedelta(days=3, hours=10)).isoformat(),
        "end_time": (now + timedelta(days=3, hours=12)).isoformat(),
        "type": "meeting",
        "location_or_link": "https://meet.google.com/xyz-abc-123",
        "client_id": client_id or None,
    })
    event_id = ""
    if r.status_code == 201:
        event_id = r.json()["id"]
        ok("Crear evento calendario", f"id={event_id[:8]}…")
    else:
        fail("Crear evento", r.text[:100])

    r = await client.get("/crm/events", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar eventos", f"{len(r.json())} eventos")

    # Reservas
    r = await client.post("/crm/reservations", headers=HEADERS, json={
        "client_id": client_id,
        "start_time": (now + timedelta(days=5, hours=9)).isoformat(),
        "end_time": (now + timedelta(days=5, hours=10)).isoformat(),
        "notes": "Sala de reuniones A — 8 personas",
        "status": "pending",
    })
    res_id = ""
    if r.status_code == 201:
        res_id = r.json()["id"]
        ok("Crear reserva", f"id={res_id[:8]}…")
    else:
        fail("Crear reserva", r.text[:100])

    if res_id:
        r = await client.patch(f"/crm/reservations/{res_id}", headers=HEADERS, json={"status": "confirmed"})
        if r.status_code == 200 and r.json()["status"] == "confirmed":
            ok("Confirmar reserva")

    # Reuniones
    r = await client.post("/crm/meetings", headers=HEADERS, json={
        "title": "Demo plataforma AutomatizaPyme",
        "client_id": client_id or None,
        "start_time": (now + timedelta(days=10, hours=11)).isoformat(),
        "end_time": (now + timedelta(days=10, hours=12, minutes=30)).isoformat(),
        "location_or_link": "Oficinas cliente — C/ Mayor 1, Madrid",
        "notes": "Presentar módulos: ERP, CRM, RRHH, Automatizaciones IA",
    })
    if r.status_code == 201:
        ok("Crear reunión", f"id={r.json()['id'][:8]}…")
    else:
        fail("Crear reunión", r.text[:100])

    r = await client.get("/crm/meetings", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar reuniones", f"{len(r.json())} reuniones")


# ─── 11. RRHH ─────────────────────────────────────────────────────────────────

async def test_rrhh(client: httpx.AsyncClient) -> str:
    section("11. RRHH — EMPLEADOS & NÓMINAS")
    emp_id = ""

    r = await client.post("/hr/employees", headers=HEADERS, json={
        "nif": "12345678A",
        "name": "Ana García López",
        "department": "Tecnología",
        "role": "Desarrolladora Senior",
        "base_salary": 3800.0,
        "status": "active",
    })
    if r.status_code == 201:
        emp_id = r.json()["id"]
        ok("Crear empleado", f"id={emp_id[:8]}… salario=3800€/mes")
    else:
        fail("Crear empleado", r.text[:100])

    r = await client.post("/hr/employees", headers=HEADERS, json={
        "nif": "87654321B", "name": "Carlos Martínez Ruiz",
        "department": "Ventas", "role": "Account Manager",
        "base_salary": 2800.0, "status": "active",
    })
    if r.status_code == 201:
        ok("Crear empleado 2", "Ventas — 2800€/mes")

    # Listar
    r = await client.get("/hr/employees", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar empleados", f"{len(r.json())} empleados")

    # Editar
    if emp_id:
        r = await client.patch(f"/hr/employees/{emp_id}", headers=HEADERS, json={"base_salary": 4000.0, "role": "Tech Lead"})
        if r.status_code == 200 and r.json()["base_salary"] == 4000.0:
            ok("Editar empleado (promoción + aumento)", "4000€/mes → Tech Lead")

    # Nómina
    if emp_id:
        now = datetime.now()
        r = await client.post(f"/hr/employees/{emp_id}/payrolls", headers=HEADERS, json={
            "period_start": (now.replace(day=1)).isoformat(),
            "period_end": now.isoformat(),
            "issue_date": now.isoformat(),
            "base_salary": 4000.0,
            "deductions": 900.0,
            "net_salary": 3100.0,
            "status": "paid",
        })
        if r.status_code == 201:
            ok("Crear nómina", f"bruto=4000€ deducción=900€ neto=3100€")
        else:
            fail("Crear nómina", r.text[:100])

    return emp_id


# ─── 12. TAREAS IA — Multi-agente ─────────────────────────────────────────────

async def test_tareas_ia(client: httpx.AsyncClient) -> None:
    section("12. TAREAS IA — AGENTES ESPECIALIZADOS")

    tasks_to_run = [
        {
            "domain": "billing",
            "label": "Billing: factura automática IA",
            "intent": (
                "Crea una factura de 5.800 euros a la empresa 'Energía Renovable SL' "
                "con NIF B55443322 por instalación de paneles solares en nave industrial, "
                "con IVA del 21%. Marca la fecha de voy vencimiento a 30 días."
            ),
        },
        {
            "domain": "hr",
            "label": "HR: análisis coste salarial",
            "intent": (
                "Genera un resumen del coste salarial mensual total de la empresa "
                "incluyendo todos los empleados activos, agrupados por departamento. "
                "Calcula el coste empresa estimado con 30% de Seguridad Social."
            ),
        },
        {
            "domain": "crm",
            "label": "CRM: análisis pipeline de ventas",
            "intent": (
                "Analiza el pipeline de ventas actual. Dame el valor total de oportunidades "
                "abiertas ponderado por probabilidad, cuántas están en cada etapa, "
                "y recomienda las 3 acciones más urgentes para cerrar ventas este mes."
            ),
        },
        {
            "domain": "advisory",
            "label": "Advisory: alerta fiscal trimestral",
            "intent": (
                "Revisa las facturas emitidas y calcula el IVA repercutido total del trimestre. "
                "Estima la cuota de IVA a ingresar en Hacienda y avisa si hay algún riesgo "
                "de no tener liquidez suficiente para afrontarlo."
            ),
        },
    ]

    launched = []
    for task_def in tasks_to_run:
        r = await client.post("/tasks", headers=HEADERS, json={
            "domain": task_def["domain"],
            "user_intent": task_def["intent"],
        })
        if r.status_code in (200, 201):
            task_id = r.json()["id"]
            launched.append((task_def["label"], task_id))
            ok(f"Lanzar tarea: {task_def['label']}", f"id={task_id[:8]}…")
        else:
            fail(f"Lanzar tarea: {task_def['label']}", r.text[:80])

    # Esperar resultados
    info("Esperando que los agentes IA procesen las tareas (máx 90s)…")
    for label, task_id in launched:
        result = await poll_task(client, task_id, max_wait=90)
        if result:
            status = result["status"]
            if status == "done":
                results_list = result.get("agent_results", [])
                last_output = results_list[-1].get("output", {}) if results_list else {}
                summary = (
                    str(last_output.get("respuesta_consulta", ""))[:80]
                    or str(last_output.get("summary", ""))[:80]
                    or str(last_output)[:80]
                )
                ok(f"Tarea completada: {label}", f"output: {summary}…")
            else:
                fail(f"Tarea fallida: {label}", result.get("error_message", "")[:80])
        else:
            fail(f"Tarea timeout: {label}", "no terminó en 90s")


# ─── 13. TAREA MULTI-AGENTE compleja ─────────────────────────────────────────

async def test_tarea_compleja(client: httpx.AsyncClient) -> None:
    section("13. TAREA COMPLEJA MULTI-AGENTE (cruce de información)")

    intent = (
        "Necesito un informe completo de situación de la empresa para el consejo de administración. "
        "Incluye: (1) Resumen financiero: facturación total del mes, pendiente de cobro y cash flow estimado. "
        "(2) Estado del equipo: número de empleados activos, coste salarial mensual y próximas nóminas. "
        "(3) Pipeline comercial: oportunidades abiertas valoradas y probabilidad de cierre. "
        "(4) Alertas: cualquier factura vencida sin cobrar, stock por debajo del mínimo, o empleado sin nómina este mes. "
        "Genera el informe en formato estructurado y guárdalo como documento interno."
    )

    r = await client.post("/tasks", headers=HEADERS, json={
        "domain": "coordinator",
        "user_intent": intent,
    })
    if r.status_code in (200, 201):
        task_id = r.json()["id"]
        ok("Lanzar tarea compleja multi-agente", f"id={task_id[:8]}…")
        info("Esperando resultado (máx 120s)…")
        result = await poll_task(client, task_id, max_wait=120)
        if result:
            if result["status"] == "done":
                ok("Tarea multi-agente completada", f"{len(result.get('agent_results', []))} pasos ejecutados")
                # Mostrar resumen
                for i, ar in enumerate(result.get("agent_results", [])[:3]):
                    agent = ar.get("agent", "?")
                    out = str(ar.get("output", ""))[:100]
                    info(f"  Paso {i+1} [{agent}]: {out}…")
            else:
                fail("Tarea multi-agente", result.get("error_message", "")[:100])
        else:
            fail("Tarea multi-agente timeout")
    else:
        fail("Lanzar tarea multi-agente", r.text[:100])


# ─── 14. AUTOMATIZACIONES / WORKFLOWS ────────────────────────────────────────

async def poll_workflow_execution(
    client: httpx.AsyncClient, wf_id: str, exec_id: str, max_wait: int = 60
) -> dict | None:
    """Espera a que una WorkflowExecution termine (success/failed)."""
    for _ in range(max_wait):
        r = await client.get(f"/workflows/{wf_id}/executions", headers=HEADERS)
        if r.status_code == 200:
            for ex in r.json():
                if ex["id"] == exec_id and ex["status"] in ("success", "failed"):
                    return ex
        await asyncio.sleep(2)
    return None


async def test_automatizaciones(client: httpx.AsyncClient) -> None:
    section("14. AUTOMATIZACIONES — MOTOR DE WORKFLOWS")

    # ── 14.1 Parsear lenguaje natural → workflow ──────────────────────────────
    r = await client.post("/workflows/parse-nl", headers=HEADERS, json={
        "text": "Cada lunes a las 9 de la mañana genera un informe de ventas de la semana anterior y guárdalo como documento"
    })
    if r.status_code == 200:
        parsed = r.json()
        ok(
            "Parse NL → workflow config",
            f"trigger={parsed.get('trigger_type')} name='{parsed.get('name', '')[:40]}'"
        )
    else:
        fail("Parse NL → workflow", r.text[:100])

    # ── 14.2 Crear workflow event-based (se dispara cuando se crea una factura) ─
    r = await client.post("/workflows", headers=HEADERS, json={
        "name": "Alerta factura creada",
        "description": "Cuando se crea una factura, revisar si el cliente tiene deudas pendientes",
        "is_active": True,
        "trigger_type": "event_based",
        "trigger_config": {"events": ["invoice_created"]},
        "action_type": "ai_task",
        "action_config": {
            "instruction": "Revisa si el cliente de la factura tiene facturas anteriores sin pagar. Si las hay, genera un resumen de deuda.",
        },
    })
    wf_event_id = ""
    if r.status_code == 201:
        wf_event_id = r.json()["id"]
        ok("Crear workflow event-based (invoice_created)", f"id={wf_event_id[:8]}…")
    else:
        fail("Crear workflow event-based", r.text[:100])

    # ── 14.3 Crear workflow schedule-based ────────────────────────────────────
    r = await client.post("/workflows", headers=HEADERS, json={
        "name": "Informe semanal de ventas",
        "description": "Cada lunes a las 8:00 genera resumen de ventas de la semana anterior",
        "is_active": True,
        "trigger_type": "schedule_based",
        "trigger_config": {"cron": "0 8 * * 1"},
        "action_type": "ai_task",
        "action_config": {
            "instruction": "Genera un informe de ventas de la última semana: facturas emitidas, total facturado, cobrado y pendiente. Guárdalo como documento.",
        },
    })
    wf_sched_id = ""
    if r.status_code == 201:
        wf_sched_id = r.json()["id"]
        ok("Crear workflow schedule-based (lunes 8:00)", f"id={wf_sched_id[:8]}…")
    else:
        fail("Crear workflow schedule-based", r.text[:100])

    # ── 14.4 Listar workflows ─────────────────────────────────────────────────
    r = await client.get("/workflows", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar workflows", f"{len(r.json())} automatizaciones")
    else:
        fail("Listar workflows")

    # ── 14.5 Ver detalle de un workflow ───────────────────────────────────────
    if wf_event_id:
        r = await client.get(f"/workflows/{wf_event_id}", headers=HEADERS)
        if r.status_code == 200:
            ok("Detalle workflow", f"name='{r.json()['name']}'")

    # ── 14.6 Ejecutar workflow manualmente → lanza Task IA + WorkflowExecution ─
    exec_id = ""
    if wf_event_id:
        r = await client.post(f"/workflows/{wf_event_id}/run", headers=HEADERS)
        if r.status_code in (200, 201):
            exec_data = r.json()
            exec_id = exec_data.get("id", "")
            task_id_linked = exec_data.get("task_id", "")
            ok(
                "Ejecutar workflow manualmente → WorkflowExecution creada",
                f"exec_id={exec_id[:8]}… task_id={str(task_id_linked)[:8]}…"
            )
        else:
            fail("Ejecutar workflow manualmente", r.text[:100])

    # ── 14.7 Esperar que la tarea vinculada termine ───────────────────────────
    if exec_id and wf_event_id:
        info("Esperando que el workflow ejecute su tarea IA (máx 90s)…")

        # Obtener task_id de la ejecución
        r = await client.get(f"/workflows/{wf_event_id}/executions", headers=HEADERS)
        task_id_wf = None
        if r.status_code == 200:
            for ex in r.json():
                if ex["id"] == exec_id:
                    task_id_wf = ex.get("task_id")
                    break

        if task_id_wf:
            task_result = await poll_task(client, str(task_id_wf), max_wait=90)
            if task_result:
                status = task_result["status"]
                if status == "done":
                    ok("Tarea IA del workflow completada", f"status={status}")
                else:
                    fail("Tarea IA del workflow", f"status={status} error={task_result.get('error_message', '')[:60]}")
            else:
                fail("Tarea IA del workflow timeout (>90s)")
        else:
            info("No se pudo obtener task_id de la ejecución para polling")

    # ── 14.8 Consultar historial de ejecuciones del workflow ──────────────────
    if wf_event_id:
        r = await client.get(f"/workflows/{wf_event_id}/executions", headers=HEADERS)
        if r.status_code == 200:
            execs = r.json()
            statuses = [ex["status"] for ex in execs]
            ok("Historial de ejecuciones", f"{len(execs)} ejecuciones — estados: {statuses}")
        else:
            fail("Historial de ejecuciones", r.text[:80])

    # ── 14.9 Disparar evento ERP → activa workflows event-based ──────────────
    r = await client.post("/workflows/fire-event", headers=HEADERS, json={
        "event": "invoice_created",
        "context": {
            "invoice_number": "FAC-TEST-EVENTO",
            "client_name": "Industrias Prueba SL",
            "amount_total": 5800.0,
        }
    })
    if r.status_code == 200:
        fired = r.json()
        ok(
            "Disparar evento 'invoice_created' → workflows activados",
            f"{fired.get('count', 0)} workflow(s) disparados"
        )
    else:
        fail("Disparar evento ERP", r.text[:100])

    # ── 14.10 Pausar workflow (is_active=False) ───────────────────────────────
    if wf_event_id:
        r = await client.patch(f"/workflows/{wf_event_id}", headers=HEADERS, json={"is_active": False})
        if r.status_code == 200 and not r.json()["is_active"]:
            ok("Pausar workflow (is_active=False)")

        # Verificar que un workflow pausado no se puede ejecutar
        r2 = await client.post(f"/workflows/{wf_event_id}/run", headers=HEADERS)
        if r2.status_code == 400:
            ok("Workflow pausado rechaza ejecución manual (400 correcto)")
        else:
            fail("Workflow pausado debería rechazar ejecución", f"status={r2.status_code}")

        # Reactivar
        r = await client.patch(f"/workflows/{wf_event_id}", headers=HEADERS, json={"is_active": True})
        if r.status_code == 200 and r.json()["is_active"]:
            ok("Reactivar workflow")

    # ── 14.11 Editar nombre y descripción de un workflow ──────────────────────
    if wf_sched_id:
        r = await client.patch(f"/workflows/{wf_sched_id}", headers=HEADERS, json={
            "name": "Informe semanal ventas v2",
            "description": "Actualizado: también incluye estado de stock bajo mínimo"
        })
        if r.status_code == 200 and "v2" in r.json()["name"]:
            ok("Editar workflow (nombre + descripción)")

    # ── 14.12 Eliminar workflow schedule (limpieza) ───────────────────────────
    if wf_sched_id:
        r = await client.delete(f"/workflows/{wf_sched_id}", headers=HEADERS)
        if r.status_code == 200:
            ok("Eliminar workflow schedule-based")

        # Verificar que ya no existe
        r2 = await client.get(f"/workflows/{wf_sched_id}", headers=HEADERS)
        if r2.status_code == 404:
            ok("Workflow eliminado confirmado (404)")

    # ── 14.13 Celery Beat — verificar que check_scheduled_workflows existe ────
    info("El Celery Beat evalúa workflows cada minuto vía 'check_scheduled_workflows'")
    info("El Beat 'process_recurring_invoices' se ejecuta diariamente a las 8:00")


# ─── 15. DOCUMENTOS ───────────────────────────────────────────────────────────

async def test_documentos(client: httpx.AsyncClient) -> None:
    section("15. DOCUMENTOS — UPLOAD & LISTADO")

    # Crear un archivo de prueba en memoria
    fake_pdf = b"%PDF-1.4 FAKE TEST DOCUMENT " + b"0" * 100

    r = await client.post(
        "/documents/upload",
        headers=HEADERS,
        files={"file": ("contrato_prueba.pdf", fake_pdf, "application/pdf")},
        data={"category": "contract"},
    )
    if r.status_code in (200, 201):
        doc_id = r.json().get("id", "?")
        ok("Subir documento (PDF)", f"id={str(doc_id)[:8]}… cat=contract")
    else:
        # Puede estar deshabilitado o requerir configuración especial
        info(f"Upload documento: status={r.status_code} (puede requerir configuración)")

    r = await client.get("/documents", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar documentos", f"{len(r.json())} documentos")
    else:
        info(f"Listar documentos: status={r.status_code}")


# ─── 16. BANCA / TESORERÍA ────────────────────────────────────────────────────

async def test_banca(client: httpx.AsyncClient) -> None:
    section("16. BANCA & TESORERÍA")

    r = await client.get("/banking/summary", headers=HEADERS)
    if r.status_code == 200:
        s = r.json()
        ok("Resumen bancario", f"ingresos={s.get('ingresos', 0)}€ gastos={s.get('gastos', 0)}€")
    else:
        fail("Resumen bancario", r.text[:80])

    r = await client.get("/banking/analytics", headers=HEADERS)
    if r.status_code == 200:
        a = r.json()
        ok("Analytics bancario", f"cashflow={len(a.get('cashflow', []))} meses")
    else:
        info(f"Analytics bancario: status={r.status_code}")

    r = await client.get("/banking/transactions", headers=HEADERS)
    if r.status_code == 200:
        ok("Listar transacciones bancarias", f"{len(r.json())} transacciones")

    # Sync
    r = await client.post("/banking/transactions/sync", headers=HEADERS)
    if r.status_code == 200:
        ok("Sincronizar transacciones bancarias")
    else:
        info(f"Sync bancario: status={r.status_code}")


# ─── 17. IMPUESTOS & COMPLIANCE ───────────────────────────────────────────────

async def test_impuestos(client: httpx.AsyncClient) -> None:
    section("17. IMPUESTOS & COMPLIANCE")

    r = await client.get("/compliance/status", headers=HEADERS)
    if r.status_code == 200:
        ok("Estado compliance", str(r.json())[:80])
    else:
        info(f"Compliance: status={r.status_code}")

    r = await client.get("/advisory/boe/fiscal", headers=HEADERS)
    if r.status_code == 200:
        items = r.json()
        ok("BOE fiscal — alertas normativas", f"{len(items)} alertas")
    else:
        info(f"BOE Advisory: status={r.status_code}")


# ─── RESUMEN FINAL ────────────────────────────────────────────────────────────

def print_summary():
    section("RESUMEN FINAL DE PRUEBAS")

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print(f"\n  Total pruebas ejecutadas: {total}")
    print(f"  {PASS} Pasadas: {passed}")
    print(f"  {FAIL} Fallidas: {failed}")
    print(f"  Ratio de éxito: {(passed/total*100):.1f}%\n")

    if failed > 0:
        print(f"  {'─'*50}")
        print(f"  PRUEBAS FALLIDAS:")
        for r in results:
            if r["status"] == "FAIL":
                print(f"    {FAIL} [{r['section']}] {r['detail']}")

    print(f"\n{'═'*60}")
    print("  OUTPUTS A VERIFICAR EN LA UI:")
    print("─" * 60)
    checks = [
        ("Contactos",         "1 cliente 'Industrias Prueba SL' visible"),
        ("Proveedores",       "1 proveedor 'Suministros Global SA'"),
        ("Catálogo",          "Producto 'Servidor NAS 8TB' con stock=20 (ajuste)"),
        ("Stock",             "3 movimientos: +5 entrada, -3 salida, =20 ajuste"),
        ("Facturas",          "FAC-TEST-001 estado=PAGADA, PDF descargable"),
        ("Facturas",          "Factura convertida de presupuesto"),
        ("Facturas",          "Factura recurrente REC-* generada como borrador"),
        ("Presupuestos",      "1 presupuesto convertido a factura"),
        ("Pedidos Venta",     "1 pedido ENTREGADO con flujo completo"),
        ("Pedidos Compra",    "1 pedido RECIBIDO de Suministros Global SA"),
        ("Recurrentes",       "Plantilla 'Mantenimiento mensual IT' PAUSADA"),
        ("Libro diario",      "1 asiento 430/705/477 equilibrado 3025€"),
        ("Activos fijos",     "Servidor HP ProLiant DL380 — amortización calculada"),
        ("CRM — Embudo",      "Oportunidad 'Digitalización planta' cerrada WON"),
        ("CRM — Actividades", "Llamada + nota registradas"),
        ("CRM — Calendario",  "Reunión kick-off en 3 días"),
        ("CRM — Reservas",    "Reserva CONFIRMADA"),
        ("CRM — Reuniones",   "Demo AutomatizaPyme programada"),
        ("RRHH — Empleados",  "Ana García (Tech Lead 4000€) + Carlos Martínez"),
        ("RRHH — Nóminas",    "Nómina de Ana: bruto 4000€ neto 3100€"),
        ("Automatizaciones",  "Parse NL → workflow config generado"),
        ("Automatizaciones",  "workflow event-based activo, ejecutado manualmente"),
        ("Automatizaciones",  "WorkflowExecution en historial con status=success"),
        ("Automatizaciones",  "fire-event 'invoice_created' disparó 1+ workflows"),
        ("Automatizaciones",  "workflow pausado rechaza ejecución → reactivado"),
        ("Tareas IA",         "4 tareas en estado done en /tareas"),
        ("Historial cliente", "/clientes/<id> muestra timeline con facturas"),
    ]
    for section_name, check in checks:
        print(f"  [{section_name:<20}] → {check}")

    print(f"\n{'═'*60}")
    print("  Script finalizado.\n")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    print(f"\n{'═'*60}")
    print("  AUTOMATIZAPYME — TEST INTEGRAL DEL SISTEMA")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'═'*60}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # Auth
        ok_auth = await test_auth(client)
        if not ok_auth:
            print(f"\n{FAIL} No se pudo autenticar. Abortando.")
            return

        # ERP
        client_id, supplier_id = await test_clientes(client)
        prod_id, svc_id = await test_productos(client)
        invoice_id = await test_facturas(client, client_id, prod_id)
        quote_id = await test_presupuestos(client, client_id)
        await test_pedidos_venta(client, client_id, prod_id)
        await test_pedidos_compra(client, supplier_id, prod_id)
        await test_recurrentes(client, client_id)

        # Contabilidad
        await test_contabilidad(client)

        # CRM
        await test_crm(client, client_id)

        # RRHH
        await test_rrhh(client)

        # Tareas IA
        await test_tareas_ia(client)
        await test_tarea_compleja(client)

        # Automatizaciones
        await test_automatizaciones(client)

        # Extras
        await test_documentos(client)
        await test_banca(client)
        await test_impuestos(client)

    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
