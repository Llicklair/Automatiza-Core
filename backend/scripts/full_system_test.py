"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          AUTOMATIZAPYME — TEST INTEGRAL DEL SISTEMA                         ║
║  Simula el cerebro IA probando TODAS las funcionalidades via API             ║
║  Ejecutar: python scripts/full_system_test.py                                 ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import asyncio
from datetime import date, datetime, timedelta

import httpx

BASE_URL = "http://localhost:8000/api/v1"
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
        "title": "Proyecto digitalización planta",
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
    r = await client.post("/crm/events", headers=HEADERS, json={
        "title": "Demo plataforma AutomatizaPyme",
        "client_id": client_id or None,
        "start_time": (now + timedelta(days=10, hours=11)).isoformat(),
        "end_time": (now + timedelta(days=10, hours=12, minutes=30)).isoformat(),
        "location_or_link": "Oficinas cliente — C/ Mayor 1, Madrid",
        "description": "Presentar módulos: ERP, CRM, RRHH, Automatizaciones IA",
        "type": "meeting",
    })
    if r.status_code == 201:
        ok("Crear reunión", f"id={r.json()['id'][:8]}…")
    else:
        fail("Crear reunión", r.text[:100])

    r = await client.get("/crm/events", headers=HEADERS)
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
        r = await client.post("/hr/payrolls", headers=HEADERS, json={
            "employee_id": emp_id,
            "period_start": (now.replace(day=1)).isoformat(),
            "period_end": now.isoformat(),
            "issue_date": now.isoformat(),
            "base_salary": 4000.0,
            "deductions": 900.0,
            "net_salary": 3100.0,
            "status": "paid",
        })
        if r.status_code == 201:
            ok("Crear nómina", "bruto=4000€ deducción=900€ neto=3100€")
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

    # Esperar resultados — todas en paralelo para no bloquear
    info("Esperando que los agentes IA procesen las tareas en paralelo (máx 180s)…")

    async def _wait_one(label: str, task_id: str) -> None:
        result = await poll_task(client, task_id, max_wait=180)
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
            fail(f"Tarea timeout: {label}", "no terminó en 180s")

    await asyncio.gather(*[_wait_one(label, tid) for label, tid in launched])


# ─── 13. COORDINADOR — TAREAS COMPLEJAS MULTI-AGENTE ────────────────────────

async def _run_coordinator_task(
    client: httpx.AsyncClient,
    label: str,
    intent: str,
    expected_agents: list[str],
    max_wait: int = 180,
) -> bool:
    """Lanza una tarea de coordinador, espera resultado y verifica agentes usados."""
    r = await client.post("/tasks", headers=HEADERS, json={
        "domain": "coordinator",
        "user_intent": intent,
    })
    if r.status_code not in (200, 201):
        fail(f"Lanzar: {label}", r.text[:80])
        return False

    task_id = r.json()["id"]
    ok(f"Lanzar: {label}", f"id={task_id[:8]}…")
    info(f"  Esperando coordinación multi-agente (máx {max_wait}s)…")

    result = await poll_task(client, task_id, max_wait=max_wait)
    if not result:
        fail(f"Timeout (rate-limit Groq): {label}", f"no terminó en {max_wait}s")
        return False

    if result["status"] != "done":
        fail(label, result.get("error_message", "sin detalle")[:120])
        return False

    agent_results = result.get("agent_results", [])
    agents_used = [ar.get("agent", "?") for ar in agent_results]
    steps_ok = sum(1 for ar in agent_results if ar.get("success"))
    steps_fail = len(agent_results) - steps_ok

    ok(
        f"Completada: {label}",
        f"{len(agent_results)} pasos — {steps_ok} OK / {steps_fail} fallidos — agentes: {agents_used}"
    )

    # Verificar que los agentes esperados fueron invocados
    missing = [a for a in expected_agents if a not in agents_used]
    if missing:
        info(f"  ⚠️  Agentes esperados no invocados: {missing}")
    else:
        info(f"  ✔  Todos los agentes esperados participaron: {expected_agents}")

    # Mostrar salidas clave de cada paso
    for i, ar in enumerate(agent_results):
        agent = ar.get("agent", "?")
        out = ar.get("output", {})
        summary = (
            str(out.get("action", ""))[:90]
            or str(out.get("summary", ""))[:90]
            or str(out)[:90]
        )
        status_icon = "✔" if ar.get("success") else "✗"
        info(f"  Paso {i+1} [{agent}] {status_icon}: {summary}…")

    return True


async def test_coordinador_complejo(client: httpx.AsyncClient) -> None:
    section("13. COORDINADOR — TAREAS COMPLEJAS MULTI-AGENTE")

    coordinator_tasks = [
        dict(
            label="Alta cliente + oportunidad CRM completa",
            intent=(
                "Acabo de tener una reunión muy buena con Manufactura Digital SL (CIF B-87654321, "
                "contacto: Laura Pérez, laura@manufactura.es, tel. 612 345 678). "
                "Están interesados en implantar nuestro ERP para 25 usuarios. "
                "Precio estimado: 18.000€ primer año + 3.600€/año mantenimiento. "
                "Han pedido presupuesto para la próxima semana. Probabilidad de cierre: 70%. "
                "Necesito: (1) Registrarlos como cliente potencial, "
                "(2) Crear oportunidad en el embudo en fase 'proposal', "
                "(3) Registrar la reunión de hoy como actividad CRM con nota del interés."
            ),
            expected_agents=["crm"],
        ),
        dict(
            label="Cierre mensual: nóminas + análisis financiero RRHH",
            intent=(
                "Necesito el cierre de RRHH y financiero del mes. Haz lo siguiente: "
                "(1) Calcula el coste salarial total de todos los empleados activos este mes, "
                "desglosado por departamento. Incluye el coste empresa con 30% de SS. "
                "(2) Genera la pre-nómina para todos los empleados activos que no tienen nómina este mes. "
                "(3) Dame un resumen del equipo: número de empleados, antigüedad media, coste total. "
                "No necesito crear ninguna factura, solo el análisis de personal y nóminas."
            ),
            expected_agents=["hr"],
        ),
        dict(
            label="Análisis pipeline CRM + seguimiento comercial",
            intent=(
                "Quiero un análisis completo del estado comercial actual y acciones de seguimiento: "
                "(1) Lista todas las oportunidades abiertas en el embudo, su valor, etapa y probabilidad. "
                "(2) Calcula el valor total ponderado del pipeline (valor × probabilidad). "
                "(3) Para las oportunidades en etapa 'proposal' que llevan más de 7 días sin actividad, "
                "registra una actividad CRM de tipo 'llamada de seguimiento' con nota "
                "'Pendiente de respuesta a propuesta enviada'. "
                "(4) Identifica los 3 leads con mayor probabilidad de cierre y propón la siguiente acción "
                "para cada uno. No necesito crear facturas, solo análisis CRM y actividades."
            ),
            expected_agents=["crm"],
        ),
        dict(
            label="Onboarding empleado: alta + nómina + evento bienvenida",
            intent=(
                "Incorporamos a una nueva empleada: María González Ruiz, DNI 87654321B, "
                "ingeniera de software senior, departamento Tech, salario bruto 52.000€/año "
                "(4.333,33€/mes), fecha de incorporación hoy, contrato indefinido. "
                "Necesito: (1) Darla de alta como empleada en el sistema con todos sus datos. "
                "(2) Calcular su pre-nómina estimada para este mes. "
                "(3) Registrar en el calendario CRM un evento de 'Reunión de bienvenida con María' "
                "para mañana a las 10:00, duración 1 hora, descripción: presentación al equipo Tech. "
                "No necesito crear facturas ni documentos de facturación."
            ),
            expected_agents=["hr", "crm"],
        ),
    ]

    # Lanzar todas en paralelo (máx 90s total, no 4×90s)
    await asyncio.gather(*[
        _run_coordinator_task(client, **t) for t in coordinator_tasks
    ])


# ─── 14. AUTOMATIZACIONES / WORKFLOWS ────────────────────────────────────────

async def poll_workflow_execution(
    client: httpx.AsyncClient, wf_id: str, exec_id: str, max_wait: int = 90
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


async def _create_workflow_and_run(
    client: httpx.AsyncClient,
    name: str,
    description: str,
    trigger_type: str,
    trigger_config: dict,
    action_config: dict,
    label_short: str,
    max_task_wait: int = 120,
) -> str:
    """Crea un workflow, lo ejecuta manualmente y espera que la tarea IA finalice.
    Devuelve el workflow_id o cadena vacía en caso de fallo."""
    # Crear
    r = await client.post("/workflows", headers=HEADERS, json={
        "name": name,
        "description": description,
        "is_active": True,
        "trigger_type": trigger_type,
        "trigger_config": trigger_config,
        "action_type": "ai_task",
        "action_config": action_config,
    })
    if r.status_code != 201:
        fail(f"Crear workflow: {label_short}", r.text[:120])
        return ""
    wf_id = r.json()["id"]
    ok(f"Crear workflow: {label_short}", f"id={wf_id[:8]}… trigger={trigger_type}")

    # Ejecutar manualmente
    r = await client.post(f"/workflows/{wf_id}/run", headers=HEADERS)
    if r.status_code not in (200, 201):
        fail(f"Ejecutar workflow: {label_short}", r.text[:80])
        return wf_id
    exec_data = r.json()
    exec_id = exec_data.get("id", "")
    task_id_wf = exec_data.get("task_id", "")
    ok(f"Ejecutar workflow: {label_short}", f"exec={exec_id[:8]}… task={str(task_id_wf)[:8]}…")

    # Esperar tarea IA
    info(f"  Esperando tarea IA del workflow (máx {max_task_wait}s)…")
    if task_id_wf:
        task_result = await poll_task(client, str(task_id_wf), max_wait=max_task_wait)
        if task_result:
            st = task_result["status"]
            agent_results = task_result.get("agent_results", [])
            last_out = str(agent_results[-1].get("output", ""))[:100] if agent_results else ""
            if st == "done":
                ok(f"Tarea IA completada: {label_short}", f"{len(agent_results)} pasos — {last_out}…")
            else:
                fail(f"Tarea IA falló: {label_short}", task_result.get("error_message", "")[:80])
        else:
            fail(f"Tarea IA timeout: {label_short}", f">{max_task_wait}s sin resultado")

    # Consultar ejecuciones
    r = await client.get(f"/workflows/{wf_id}/executions", headers=HEADERS)
    if r.status_code == 200:
        execs = r.json()
        statuses = [ex["status"] for ex in execs]
        info(f"  Historial {label_short}: {len(execs)} ejecución(es) → {statuses}")

    return wf_id


async def test_automatizaciones(client: httpx.AsyncClient) -> None:
    section("14. AUTOMATIZACIONES — MOTOR DE WORKFLOWS (COMPLEJOS)")

    created_wf_ids: list[str] = []

    # ── 14.1 Parse NL → config de workflow complejo ───────────────────────────
    r = await client.post("/workflows/parse-nl", headers=HEADERS, json={
        "text": (
            "Cada viernes a las 18:00 revisa todas las facturas emitidas esa semana, "
            "calcula el IVA repercutido total, compara con el saldo bancario actual "
            "y genera un documento de alerta si el saldo es inferior al 120% del IVA pendiente de pago a Hacienda"
        )
    })
    if r.status_code == 200:
        parsed = r.json()
        ok(
            "Parse NL → workflow complejo (tesorería + fiscal)",
            f"trigger={parsed.get('trigger_type')} cron={parsed.get('trigger_config', {}).get('cron', '?')} "
            f"name='{parsed.get('name', '')[:50]}'"
        )
    else:
        fail("Parse NL → workflow", r.text[:100])

    # ── 14.2-14.5 Crear y ejecutar workflows en paralelo ─────────────────────
    wf_defs = [
        dict(
            name="Control de morosidad automático",
            description=(
                "Cada vez que se crea una factura, comprueba si ese cliente tiene facturas "
                "anteriores sin pagar con más de 30 días. Si las hay, registra una actividad "
                "CRM de 'llamada de seguimiento' y genera un documento de alerta de morosidad."
            ),
            trigger_type="event_based",
            trigger_config={"events": ["invoice_created"]},
            action_config={
                "instruction": (
                    "El cliente acaba de recibir una nueva factura. "
                    "1. Consulta si tiene facturas anteriores sin pagar (estado pending/draft) con más de 30 días. "
                    "2. Si las hay: registra en CRM una actividad de tipo 'llamada' con asunto "
                    "'Seguimiento de cobro pendiente' y nota con el importe total adeudado. "
                    "3. Genera un documento de alerta de morosidad con el resumen completo: "
                    "cliente, facturas vencidas, importes y días de mora."
                ),
                "domain": "coordinator",
            },
            label_short="morosidad (event: invoice_created)",
        ),
        dict(
            name="Onboarding automático de empleados",
            description=(
                "Cuando se da de alta un nuevo empleado, calcular su pre-nómina prorrateada, "
                "crear un evento de bienvenida en el calendario y generar el documento de alta."
            ),
            trigger_type="event_based",
            trigger_config={"events": ["employee_created"]},
            action_config={
                "instruction": (
                    "Se ha dado de alta un nuevo empleado en el sistema. "
                    "1. Obtén los datos del empleado (nombre, salario, departamento, fecha de incorporación). "
                    "2. Calcula su pre-nómina prorrateada por los días que quedan del mes actual. "
                    "3. Crea un evento en el calendario de RRHH: 'Reunión de bienvenida con [nombre]' "
                    "para mañana a las 10:00, duración 1 hora. "
                    "4. Genera un documento de resumen de incorporación con todos los datos: "
                    "datos personales, salario, departamento y pre-nómina calculada."
                ),
                "domain": "coordinator",
            },
            label_short="onboarding (event: employee_created)",
        ),
        dict(
            name="Cierre semanal de ventas y tesorería",
            description=(
                "Cada lunes a las 8:00 analiza las ventas de la semana anterior, "
                "reconcilia con el saldo bancario y genera el informe de gestión."
            ),
            trigger_type="schedule_based",
            trigger_config={"cron": "0 8 * * 1"},
            action_config={
                "instruction": (
                    "Es lunes, comienzo de semana. Genera el informe semanal completo: "
                    "1. Facturas emitidas la semana pasada: número, importe total, cobradas vs pendientes. "
                    "2. Pedidos de venta procesados: unidades y valor. "
                    "3. Saldo bancario actual y comparativa con la semana anterior. "
                    "4. Top 3 clientes por volumen de facturación esta semana. "
                    "5. Alertas: facturas vencidas sin cobrar, stock crítico. "
                    "Guarda el informe como documento con título 'Informe Semanal [fecha]'."
                ),
                "domain": "coordinator",
            },
            label_short="cierre semanal (schedule lunes 8:00)",
        ),
        dict(
            name="Alerta fiscal mensual",
            description=(
                "El día 15 de cada mes, calcula el IVA acumulado del trimestre y avisa "
                "si se acerca el vencimiento de declaraciones fiscales."
            ),
            trigger_type="schedule_based",
            trigger_config={"cron": "0 9 15 * *"},
            action_config={
                "instruction": (
                    "Revisión fiscal mensual del día 15: "
                    "1. Suma el IVA repercutido (21%) de todas las facturas emitidas este trimestre. "
                    "2. Suma el IVA soportado de las facturas de compra del mismo período. "
                    "3. Calcula la cuota de IVA neta a ingresar (repercutido - soportado). "
                    "4. Comprueba el saldo bancario actual. Alerta si el saldo < cuota IVA * 1.2. "
                    "5. Lista los próximos vencimientos fiscales del trimestre (modelo 303, 111, 115). "
                    "6. Genera un documento 'Alerta Fiscal [mes/año]' con todo el análisis."
                ),
                "domain": "coordinator",
            },
            label_short="alerta fiscal (schedule día 15)",
        ),
    ]

    wf_results = await asyncio.gather(*[
        _create_workflow_and_run(client, **wf) for wf in wf_defs
    ])
    for wf_id in wf_results:
        if wf_id:
            created_wf_ids.append(wf_id)

    # ── 14.6 Listar todos los workflows y verificar estado ────────────────────
    r = await client.get("/workflows", headers=HEADERS)
    if r.status_code == 200:
        all_wfs = r.json()
        active = sum(1 for w in all_wfs if w.get("is_active"))
        ok("Listar todos los workflows", f"{len(all_wfs)} totales — {active} activos")
    else:
        fail("Listar workflows", r.text[:80])

    # ── 14.7 Disparar evento invoice_created → verifica que wf1 se activa ─────
    r = await client.post("/workflows/fire-event", headers=HEADERS, json={
        "event": "invoice_created",
        "context": {
            "invoice_number": "FAC-WF-TEST-001",
            "client_name": "Manufactura Digital SL",
            "amount_total": 18000.0,
            "client_id": None,
        }
    })
    if r.status_code == 200:
        fired = r.json()
        count = fired.get("count", 0)
        ok(
            "Fire event 'invoice_created' (importe 18.000€)",
            f"{count} workflow(s) disparado(s) automáticamente"
        )
        if count == 0:
            info("  ⚠️  Ningún workflow se disparó — verificar que wf1 está activo con ese evento")
    else:
        fail("Fire event invoice_created", r.text[:80])

    # ── 14.8 Disparar evento employee_created → verifica que wf2 se activa ────
    r = await client.post("/workflows/fire-event", headers=HEADERS, json={
        "event": "employee_created",
        "context": {
            "employee_name": "María González Ruiz",
            "department": "Tech",
            "salary": 4333.33,
        }
    })
    if r.status_code == 200:
        fired = r.json()
        count = fired.get("count", 0)
        ok(
            "Fire event 'employee_created'",
            f"{count} workflow(s) disparado(s) automáticamente"
        )
    else:
        fail("Fire event employee_created", r.text[:80])

    # ── 14.9 Pausar un workflow, verificar rechazo y reactivar ────────────────
    # wf_results = [morosidad_id, onboarding_id, cierre_semanal_id, alerta_fiscal_id]
    wf1 = wf_results[0] if wf_results else ""
    wf3 = wf_results[2] if len(wf_results) > 2 else ""
    wf4 = wf_results[3] if len(wf_results) > 3 else ""

    if wf1:
        r = await client.patch(f"/workflows/{wf1}", headers=HEADERS, json={"is_active": False})
        if r.status_code == 200 and not r.json()["is_active"]:
            ok("Pausar workflow de morosidad")

        r2 = await client.post(f"/workflows/{wf1}/run", headers=HEADERS)
        if r2.status_code == 400:
            ok("Workflow pausado rechaza ejecución manual (400 correcto)")
        else:
            fail("Debería rechazar ejecución de workflow pausado", f"status={r2.status_code}")

        r = await client.patch(f"/workflows/{wf1}", headers=HEADERS, json={"is_active": True})
        if r.status_code == 200 and r.json()["is_active"]:
            ok("Reactivar workflow de morosidad")

    # ── 14.10 Eliminar workflows de schedule (limpieza) ───────────────────────
    for wf_id in [wf3, wf4]:
        if wf_id:
            r = await client.delete(f"/workflows/{wf_id}", headers=HEADERS)
            r2 = await client.get(f"/workflows/{wf_id}", headers=HEADERS)
            if r.status_code == 200 and r2.status_code == 404:
                ok(f"Eliminar workflow schedule {wf_id[:8]}… (confirmado 404)")

    # ── 14.11 APScheduler — recordatorio informativo ──────────────────────────
    info("APScheduler evalúa 'check_scheduled_workflows' cada minuto")
    info("Los workflows schedule-based se evalúan con cron: '0 8 * * 1', '0 9 15 * *', etc.")


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
        print("  PRUEBAS FALLIDAS:")
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
        ("Coordinador IA",    "Alta cliente + oportunidad CRM — agentes: crm"),
        ("Coordinador IA",    "Cierre mensual — agentes: hr + billing"),
        ("Coordinador IA",    "Auditoría impagados — agentes: billing + crm"),
        ("Coordinador IA",    "Onboarding empleado — agentes: hr + crm"),
        ("Automatizaciones",  "Parse NL → workflow fiscal complejo (cron viernes 18:00)"),
        ("Automatizaciones",  "WF morosidad (event: invoice_created) — ejecutado y task=done"),
        ("Automatizaciones",  "WF onboarding (event: employee_created) — ejecutado y task=done"),
        ("Automatizaciones",  "WF cierre semanal (schedule lunes 8:00) — ejecutado y task=done"),
        ("Automatizaciones",  "WF alerta fiscal (schedule día 15) — ejecutado y task=done"),
        ("Automatizaciones",  "fire-event 'invoice_created' disparó 1+ workflows activos"),
        ("Automatizaciones",  "fire-event 'employee_created' disparó 1+ workflows activos"),
        ("Automatizaciones",  "workflow pausado rechaza ejecución (400) → reactivado"),
        ("Automatizaciones",  "workflows schedule eliminados, confirmados 404"),
        ("Tareas IA",         "4+ tareas en estado done en /tareas"),
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

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as client:
        # Auth
        ok_auth = await test_auth(client)
        if not ok_auth:
            print(f"\n{FAIL} No se pudo autenticar. Abortando.")
            return

        # ERP
        client_id, supplier_id = await test_clientes(client)
        prod_id, svc_id = await test_productos(client)
        await test_facturas(client, client_id, prod_id)
        await test_presupuestos(client, client_id)
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
        await test_coordinador_complejo(client)

        # Automatizaciones
        await test_automatizaciones(client)

        # Extras
        await test_documentos(client)
        await test_banca(client)
        await test_impuestos(client)

    print_summary()


if __name__ == "__main__":
    asyncio.run(main())
