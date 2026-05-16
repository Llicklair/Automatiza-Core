"""
Seed script — populates ALL sections with realistic demo data via HTTP API.
Usage:
    python scripts/seed_user_data.py --email USER --password PASS [--base http://localhost:8080]
"""
import argparse
import sys
import time
from datetime import datetime, timedelta

import httpx

BASE = "http://localhost:8080"
API = "/api/v1"
TOKEN = ""


def url(path: str) -> str:
    return f"{BASE}{API}{path}"


def headers():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


def post(path: str, data: dict, label: str = ""):
    r = httpx.post(url(path), json=data, headers=headers(), timeout=30, follow_redirects=True)
    tag = label or path
    if r.status_code in (200, 201):
        j = r.json()
        print(f"  + {tag}: {j.get('id', 'ok')}")
        return j
    else:
        print(f"  ! {tag}: {r.status_code} — {r.text[:200]}")
        return None


def login(email: str, password: str):
    global TOKEN
    r = httpx.post(url("/auth/login"), json={"email": email, "password": password}, timeout=10)
    if r.status_code != 200:
        print(f"ERROR login: {r.status_code} — {r.text[:300]}")
        sys.exit(1)
    TOKEN = r.json()["access_token"]
    print("Login OK — token obtained\n")


def iso(dt: datetime) -> str:
    return dt.isoformat()


def date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


# ─── Data ───────────────────────────────────────────────────────────────────

NOW = datetime.now()
TODAY = NOW.replace(hour=0, minute=0, second=0, microsecond=0)


def seed_clients():
    print("== Clientes ==")
    customers = [
        {"name": "Construcciones Valdemar S.L.", "nif": "B12345678", "email": "admin@valdemar.es",
         "phone": "912345678", "address": "C/ Gran Vía 42", "city": "Madrid", "postal_code": "28013",
         "client_type": "customer"},
        {"name": "Distribuciones Hnos. Pérez", "nif": "B87654321", "email": "info@hnosperez.com",
         "phone": "934567890", "address": "Av. Diagonal 155", "city": "Barcelona", "postal_code": "08018",
         "client_type": "customer"},
        {"name": "Clínica Dental Montserrat", "nif": "B11223344", "email": "recepcion@clinicamontserrat.es",
         "phone": "961234567", "address": "C/ Colón 28", "city": "Valencia", "postal_code": "46004",
         "client_type": "customer"},
    ]
    suppliers = [
        {"name": "Suministros Industriales López", "nif": "B99887766", "email": "ventas@silop.es",
         "phone": "955678901", "address": "Pol. Ind. Sur, Nave 14", "city": "Sevilla", "postal_code": "41015",
         "client_type": "supplier"},
        {"name": "TechProviders Europe S.A.", "nif": "A55443322", "email": "orders@techproviders.eu",
         "phone": "916789012", "address": "C/ Tecnología 5", "city": "Madrid", "postal_code": "28050",
         "client_type": "supplier"},
    ]
    ids = []
    for c in customers + suppliers:
        res = post("/clients", c, c["name"])
        ids.append(res["id"] if res else None)
    return ids


def seed_products():
    print("\n== Productos ==")
    products = [
        {"name": "Consultoría estratégica mensual", "item_type": "service", "sku": "SRV-001",
         "description": "Pack 20h de consultoría empresarial", "price": 1200.0, "tax_percentage": 21.0},
        {"name": "Hosting web profesional", "item_type": "service", "sku": "SRV-002",
         "description": "Hosting cloud con SSL, backups diarios", "price": 49.90, "tax_percentage": 21.0},
        {"name": "Auditoría fiscal anual", "item_type": "service", "sku": "SRV-003",
         "description": "Revisión completa contable y fiscal", "price": 2500.0, "tax_percentage": 21.0},
        {"name": "Formación in-company (jornada)", "item_type": "service", "sku": "SRV-004",
         "description": "Jornada de formación a medida, 8h", "price": 800.0, "tax_percentage": 21.0},
        {"name": "Licencia software ERP", "item_type": "product", "sku": "PRD-001",
         "description": "Licencia anual ERP cloud", "price": 3600.0, "tax_percentage": 21.0,
         "stock_quantity": 50, "stock_min_alert": 5},
        {"name": "Portátil empresarial Dell", "item_type": "product", "sku": "PRD-002",
         "description": "Dell Latitude 5540, i7, 16GB", "price": 1150.0, "tax_percentage": 21.0,
         "stock_quantity": 12, "stock_min_alert": 3},
        {"name": "Monitor 27\" 4K", "item_type": "product", "sku": "PRD-003",
         "description": "Monitor IPS 27 pulgadas UHD", "price": 389.0, "tax_percentage": 21.0,
         "stock_quantity": 20, "stock_min_alert": 5},
        {"name": "Pack material oficina", "item_type": "product", "sku": "PRD-004",
         "description": "Papel, bolígrafos, carpetas, tóner", "price": 85.0, "tax_percentage": 21.0,
         "stock_quantity": 100, "stock_min_alert": 15},
    ]
    ids = []
    for p in products:
        res = post("/products", p, p["name"])
        ids.append(res["id"] if res else None)
    return ids


def seed_invoices(client_ids, product_ids):
    print("\n== Facturas emitidas ==")
    cust = [c for c in client_ids[:3] if c]
    [p for p in product_ids if p]

    issued = [
        {"client_id": cust[0], "date": iso(TODAY - timedelta(days=60)),
         "due_date": iso(TODAY - timedelta(days=30)), "status": "paid", "invoice_type": "issued",
         "notes": "Proyecto web Q1",
         "lines": [
             {"description": "Consultoría estratégica — enero", "quantity": 1, "unit_price": 1200, "tax_percentage": 21},
             {"description": "Hosting web profesional", "quantity": 3, "unit_price": 49.90, "tax_percentage": 21},
         ]},
        {"client_id": cust[0], "date": iso(TODAY - timedelta(days=30)),
         "due_date": iso(TODAY), "status": "sent", "invoice_type": "issued",
         "notes": "Mantenimiento febrero",
         "lines": [
             {"description": "Consultoría estratégica — febrero", "quantity": 1, "unit_price": 1200, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "date": iso(TODAY - timedelta(days=45)),
         "due_date": iso(TODAY - timedelta(days=15)), "status": "paid", "invoice_type": "issued",
         "lines": [
             {"description": "Licencia software ERP", "quantity": 2, "unit_price": 3600, "tax_percentage": 21},
             {"description": "Formación in-company", "quantity": 1, "unit_price": 800, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "date": iso(TODAY - timedelta(days=10)),
         "due_date": iso(TODAY + timedelta(days=20)), "status": "draft", "invoice_type": "issued",
         "lines": [
             {"description": "Portátil empresarial Dell", "quantity": 3, "unit_price": 1150, "tax_percentage": 21},
             {"description": "Monitor 27\" 4K", "quantity": 3, "unit_price": 389, "tax_percentage": 21},
         ]},
        {"client_id": cust[2], "date": iso(TODAY - timedelta(days=20)),
         "due_date": iso(TODAY + timedelta(days=10)), "status": "sent", "invoice_type": "issued",
         "notes": "Clínica — auditoría",
         "lines": [
             {"description": "Auditoría fiscal anual", "quantity": 1, "unit_price": 2500, "tax_percentage": 21},
         ]},
        {"client_id": cust[2], "date": iso(TODAY - timedelta(days=5)),
         "due_date": iso(TODAY + timedelta(days=25)), "status": "draft", "invoice_type": "issued",
         "lines": [
             {"description": "Pack material oficina", "quantity": 5, "unit_price": 85, "tax_percentage": 21},
         ]},
    ]
    inv_ids = []
    for inv in issued:
        cid = inv.pop("client_id")
        res = post(f"/clients/{cid}/invoices", inv, f"Factura emitida → {cid[:8]}")
        inv_ids.append(res["id"] if res else None)

    print("\n== Facturas recibidas ==")
    supps = [c for c in client_ids[3:] if c]
    received = [
        {"client_id": supps[0], "date": iso(TODAY - timedelta(days=40)),
         "status": "paid", "invoice_type": "received",
         "lines": [{"description": "Material industrial — lote marzo", "quantity": 1, "unit_price": 4200, "tax_percentage": 21}]},
        {"client_id": supps[0], "date": iso(TODAY - timedelta(days=15)),
         "status": "draft", "invoice_type": "received",
         "lines": [{"description": "Repuestos maquinaria", "quantity": 10, "unit_price": 75, "tax_percentage": 21}]},
        {"client_id": supps[1], "date": iso(TODAY - timedelta(days=25)),
         "status": "paid", "invoice_type": "received",
         "lines": [
             {"description": "Servidores cloud — trimestre", "quantity": 1, "unit_price": 2800, "tax_percentage": 21},
             {"description": "Soporte técnico premium", "quantity": 1, "unit_price": 600, "tax_percentage": 21},
         ]},
        {"client_id": supps[1], "date": iso(TODAY - timedelta(days=5)),
         "status": "sent", "invoice_type": "received",
         "lines": [{"description": "Licencias Microsoft 365", "quantity": 15, "unit_price": 12.50, "tax_percentage": 21}]},
    ]
    for inv in received:
        cid = inv.pop("client_id")
        post(f"/clients/{cid}/invoices", inv, f"Factura recibida → {cid[:8]}")

    return inv_ids


def seed_quotes(client_ids, product_ids):
    print("\n== Presupuestos ==")
    cust = [c for c in client_ids[:3] if c]
    quotes = [
        {"client_id": cust[0], "date": iso(TODAY - timedelta(days=15)),
         "valid_until": iso(TODAY + timedelta(days=15)), "status": "draft",
         "notes": "Propuesta de mantenimiento anual",
         "lines": [
             {"description": "Consultoría estratégica mensual", "quantity": 12, "unit_price": 1200, "tax_percentage": 21},
             {"description": "Hosting web profesional", "quantity": 12, "unit_price": 49.90, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "date": iso(TODAY - timedelta(days=30)),
         "valid_until": iso(TODAY), "status": "accepted",
         "notes": "Equipamiento oficina nueva",
         "lines": [
             {"description": "Portátil empresarial Dell", "quantity": 10, "unit_price": 1150, "tax_percentage": 21},
             {"description": "Monitor 27\" 4K", "quantity": 10, "unit_price": 389, "tax_percentage": 21},
         ]},
        {"client_id": cust[2], "date": iso(TODAY - timedelta(days=5)),
         "valid_until": iso(TODAY + timedelta(days=25)), "status": "draft",
         "notes": "Digitalización clínica",
         "lines": [
             {"description": "Licencia software ERP", "quantity": 1, "unit_price": 3600, "tax_percentage": 21},
             {"description": "Formación in-company (2 jornadas)", "quantity": 2, "unit_price": 800, "tax_percentage": 21},
         ]},
    ]
    ids = []
    for q in quotes:
        res = post("/quotes/", q, f"Presupuesto → {q['client_id'][:8]}")
        ids.append(res["id"] if res else None)
    return ids


def seed_purchase_orders(client_ids):
    print("\n== Pedidos de compra ==")
    supps = [c for c in client_ids[3:] if c]
    orders = [
        {"supplier_id": supps[0], "date": iso(TODAY - timedelta(days=20)),
         "expected_delivery": iso(TODAY + timedelta(days=5)), "notes": "Pedido urgente material",
         "lines": [
             {"description": "Tornillería inoxidable M8", "quantity": 500, "unit_price": 0.35, "tax_percentage": 21},
             {"description": "Tubo acero galvanizado 2m", "quantity": 50, "unit_price": 18.50, "tax_percentage": 21},
         ]},
        {"supplier_id": supps[0], "date": iso(TODAY - timedelta(days=10)),
         "expected_delivery": iso(TODAY + timedelta(days=15)),
         "lines": [{"description": "EPIs — lote guantes y cascos", "quantity": 30, "unit_price": 22.0, "tax_percentage": 21}]},
        {"supplier_id": supps[1], "date": iso(TODAY - timedelta(days=5)),
         "expected_delivery": iso(TODAY + timedelta(days=10)), "notes": "Renovación equipos",
         "lines": [
             {"description": "Switch Cisco 24 puertos", "quantity": 2, "unit_price": 450, "tax_percentage": 21},
             {"description": "Cable Cat6 (bobina 305m)", "quantity": 3, "unit_price": 89, "tax_percentage": 21},
         ]},
    ]
    for o in orders:
        post("/purchase-orders", o, f"PO → {o['supplier_id'][:8]}")


def seed_sales_orders(client_ids):
    print("\n== Pedidos de venta ==")
    cust = [c for c in client_ids[:3] if c]
    orders = [
        {"client_id": cust[0], "date": iso(TODAY - timedelta(days=12)),
         "expected_delivery": iso(TODAY + timedelta(days=3)),
         "lines": [
             {"description": "Licencia software ERP", "quantity": 1, "unit_price": 3600, "tax_percentage": 21},
             {"description": "Formación in-company", "quantity": 1, "unit_price": 800, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "date": iso(TODAY - timedelta(days=7)),
         "expected_delivery": iso(TODAY + timedelta(days=14)),
         "lines": [{"description": "Portátil empresarial Dell", "quantity": 5, "unit_price": 1150, "tax_percentage": 21}]},
        {"client_id": cust[2], "date": iso(TODAY - timedelta(days=3)),
         "expected_delivery": iso(TODAY + timedelta(days=20)),
         "lines": [
             {"description": "Pack material oficina", "quantity": 10, "unit_price": 85, "tax_percentage": 21},
             {"description": "Monitor 27\" 4K", "quantity": 2, "unit_price": 389, "tax_percentage": 21},
         ]},
    ]
    for o in orders:
        post("/orders", o, f"SO → {o['client_id'][:8]}")


def seed_albaranes(client_ids):
    print("\n== Albaranes ==")
    cust = [c for c in client_ids[:3] if c]
    notes = [
        {"client_id": cust[0], "date": date_str(TODAY - timedelta(days=8)),
         "notes": "Entrega parcial proyecto web",
         "lines": [
             {"description": "Portátil empresarial Dell", "quantity": 2, "unit_price": 1150, "tax_percentage": 21},
             {"description": "Monitor 27\" 4K", "quantity": 2, "unit_price": 389, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "date": date_str(TODAY - timedelta(days=3)),
         "notes": "Entrega material oficina",
         "lines": [{"description": "Pack material oficina", "quantity": 5, "unit_price": 85, "tax_percentage": 21}]},
        {"client_id": cust[2], "date": date_str(TODAY - timedelta(days=1)),
         "lines": [{"description": "Licencia software ERP — activación", "quantity": 1, "unit_price": 3600, "tax_percentage": 21}]},
    ]
    for n in notes:
        post("/albaranes", n, f"Albarán → {n['client_id'][:8]}")


def seed_recurring_invoices(client_ids):
    print("\n== Facturas recurrentes ==")
    cust = [c for c in client_ids[:3] if c]
    recs = [
        {"client_id": cust[0], "name": "Mantenimiento web mensual",
         "interval_type": "monthly", "next_run_date": date_str(TODAY + timedelta(days=5)),
         "lines": [
             {"description": "Hosting web profesional", "quantity": 1, "unit_price": 49.90, "tax_percentage": 21},
             {"description": "Soporte técnico 5h", "quantity": 1, "unit_price": 250, "tax_percentage": 21},
         ]},
        {"client_id": cust[1], "name": "Licencia ERP trimestral",
         "interval_type": "quarterly", "next_run_date": date_str(TODAY + timedelta(days=30)),
         "lines": [{"description": "Licencia software ERP — trimestre", "quantity": 1, "unit_price": 900, "tax_percentage": 21}]},
    ]
    for r in recs:
        post("/recurring-invoices", r, r["name"])


def seed_employees():
    print("\n== Empleados ==")
    employees = [
        {"name": "María García López", "nif": "12345678Z", "email": "maria.garcia@empresa.es",
         "department": "Administración", "role": "Directora financiera", "base_salary": 3200.0,
         "irpf_rate": 19.0, "join_date": iso(TODAY - timedelta(days=730))},
        {"name": "Carlos Rodríguez Martín", "nif": "87654321X", "email": "carlos.rodriguez@empresa.es",
         "department": "Tecnología", "role": "Desarrollador senior", "base_salary": 2800.0,
         "irpf_rate": 17.0, "join_date": iso(TODAY - timedelta(days=500))},
        {"name": "Ana Fernández Ruiz", "nif": "11223344W", "email": "ana.fernandez@empresa.es",
         "department": "Comercial", "role": "Responsable de ventas", "base_salary": 2600.0,
         "irpf_rate": 15.0, "join_date": iso(TODAY - timedelta(days=365))},
        {"name": "Pedro Sánchez Gómez", "nif": "55667788V", "email": "pedro.sanchez@empresa.es",
         "department": "Operaciones", "role": "Jefe de almacén", "base_salary": 2200.0,
         "irpf_rate": 13.0, "join_date": iso(TODAY - timedelta(days=900))},
        {"name": "Laura Martínez Díaz", "nif": "99887766T", "email": "laura.martinez@empresa.es",
         "department": "RRHH", "role": "Técnico de selección", "base_salary": 2400.0,
         "irpf_rate": 14.0, "join_date": iso(TODAY - timedelta(days=200)), "status": "active"},
    ]
    ids = []
    for e in employees:
        res = post("/hr/employees", e, e["name"])
        ids.append(res["id"] if res else None)
    return ids


def seed_payrolls(employee_ids):
    print("\n== Nóminas ==")
    active = [eid for eid in employee_ids if eid]
    for month_offset in [2, 1, 0]:
        period_start = (TODAY.replace(day=1) - timedelta(days=30 * month_offset)).replace(day=1)
        if period_start.month == 12:
            period_end = period_start.replace(year=period_start.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            period_end = period_start.replace(month=period_start.month + 1, day=1) - timedelta(days=1)

        for eid in active:
            post("/hr/payrolls/auto", {
                "employee_id": eid,
                "period_start": iso(period_start),
                "period_end": iso(period_end),
            }, f"Nómina {period_start.strftime('%m/%Y')} → {eid[:8]}")
            time.sleep(0.3)


def seed_crm(client_ids):
    print("\n== CRM: Oportunidades ==")
    cust = [c for c in client_ids[:3] if c]
    opportunities = [
        {"client_id": cust[0], "title": "Migración ERP completa", "expected_value": 45000, "stage": "proposal"},
        {"client_id": cust[0], "title": "Formación equipo directivo", "expected_value": 4800, "stage": "won"},
        {"client_id": cust[1], "title": "Renovación infraestructura IT", "expected_value": 28000, "stage": "qualified"},
        {"client_id": cust[1], "title": "Consultoría procesos logísticos", "expected_value": 12000, "stage": "new"},
        {"client_id": cust[2], "title": "Digitalización historiales clínicos", "expected_value": 18000, "stage": "new"},
    ]
    opp_ids = []
    for o in opportunities:
        res = post("/crm/opportunities", o, o["title"])
        opp_ids.append(res["id"] if res else None)

    print("\n== CRM: Actividades ==")
    activities = [
        {"client_id": cust[0], "opportunity_id": opp_ids[0], "type": "call",
         "description": "Llamada inicial para presentar propuesta de migración ERP"},
        {"client_id": cust[0], "opportunity_id": opp_ids[0], "type": "email",
         "description": "Envío de presupuesto detallado con desglose de fases"},
        {"client_id": cust[0], "opportunity_id": opp_ids[1], "type": "meeting",
         "description": "Reunión de cierre — formación confirmada para mayo"},
        {"client_id": cust[1], "opportunity_id": opp_ids[2], "type": "call",
         "description": "Cualificación de necesidades: 15 puestos, backup cloud"},
        {"client_id": cust[1], "opportunity_id": opp_ids[3], "type": "email",
         "description": "Primer contacto — solicitan info sobre consultoría logística"},
        {"client_id": cust[2], "opportunity_id": opp_ids[4], "type": "meeting",
         "description": "Visita a la clínica para evaluar sistemas actuales"},
    ]
    for a in activities:
        post("/crm/activities", a, a["type"])

    print("\n== CRM: Eventos ==")
    events = [
        {"title": "Demo ERP para Valdemar", "description": "Demostración funcionalidades módulo contable",
         "start_time": iso(TODAY + timedelta(days=3, hours=10)),
         "end_time": iso(TODAY + timedelta(days=3, hours=11, minutes=30)),
         "type": "meeting", "location_or_link": "Oficina cliente — Gran Vía 42", "client_id": cust[0]},
        {"title": "Revisión propuesta Hnos. Pérez", "description": "Revisar contraoferta equipamiento",
         "start_time": iso(TODAY + timedelta(days=5, hours=16)),
         "end_time": iso(TODAY + timedelta(days=5, hours=17)),
         "type": "meeting", "location_or_link": "https://meet.google.com/abc-defg-hij", "client_id": cust[1]},
        {"title": "Seguimiento digitalización clínica",
         "start_time": iso(TODAY + timedelta(days=7, hours=9)),
         "end_time": iso(TODAY + timedelta(days=7, hours=10)),
         "type": "call", "client_id": cust[2]},
    ]
    for ev in events:
        post("/crm/events", ev, ev["title"])


def seed_projects(client_ids, employee_ids):
    print("\n== Proyectos ==")
    cust = [c for c in client_ids[:3] if c]
    [e for e in employee_ids if e]

    projects = [
        {"name": "Migración ERP Valdemar", "description": "Implantación completa del ERP para Construcciones Valdemar",
         "budget": 45000, "status": "active", "client_id": cust[0],
         "start_date": iso(TODAY - timedelta(days=30)), "due_date": iso(TODAY + timedelta(days=90))},
        {"name": "Renovación IT Hnos. Pérez", "description": "Upgrade de infraestructura: servidores, red y puestos",
         "budget": 28000, "status": "active", "client_id": cust[1],
         "start_date": iso(TODAY - timedelta(days=15)), "due_date": iso(TODAY + timedelta(days=60))},
        {"name": "Web corporativa interna", "description": "Rediseño de la web corporativa de la empresa",
         "budget": 8000, "status": "completed", "client_id": None,
         "start_date": iso(TODAY - timedelta(days=120)), "due_date": iso(TODAY - timedelta(days=30))},
    ]
    proj_ids = []
    for p in projects:
        if p["client_id"] is None:
            del p["client_id"]
        res = post("/projects", p, p["name"])
        proj_ids.append(res["id"] if res else None)

    print("\n== Tareas ==")
    tasks = [
        {"project_id": proj_ids[0], "title": "Análisis de requisitos", "status": "done",
         "description": "Entrevistas con departamentos y documentación", "priority": "high"},
        {"project_id": proj_ids[0], "title": "Configuración módulo contable", "status": "in_progress",
         "description": "Parametrización del plan contable y series de facturación", "priority": "high"},
        {"project_id": proj_ids[0], "title": "Migración de datos históricos", "status": "pending",
         "description": "Importar facturas, clientes y productos del sistema anterior", "priority": "medium"},
        {"project_id": proj_ids[0], "title": "Formación usuarios", "status": "pending",
         "description": "2 jornadas de formación presencial", "priority": "medium"},
        {"project_id": proj_ids[1], "title": "Auditoría red actual", "status": "done",
         "description": "Mapeo de toda la infraestructura de red existente", "priority": "high"},
        {"project_id": proj_ids[1], "title": "Instalación switches y cableado", "status": "in_progress",
         "description": "Despliegue de switches Cisco y cableado Cat6", "priority": "high"},
        {"project_id": proj_ids[1], "title": "Configuración VPN y firewall", "status": "pending",
         "description": "Setup de VPN site-to-site y reglas de firewall", "priority": "medium"},
        {"project_id": proj_ids[2], "title": "Diseño y maquetación", "status": "done",
         "description": "Diseño responsive y aprobación", "priority": "high"},
    ]
    for t in tasks:
        pid = t.pop("project_id")
        if pid:
            t["project_id"] = pid
            post("/projects/tasks", t, t["title"])


def seed_accounting():
    print("\n== Contabilidad: Asientos ==")
    entries = [
        {"date": iso(TODAY - timedelta(days=30)), "description": "Compra de material de oficina",
         "lines": [
             {"account_code": "629", "debit": 500, "credit": 0, "description": "Otros gastos"},
             {"account_code": "472", "debit": 105, "credit": 0, "description": "IVA soportado 21%"},
             {"account_code": "410", "debit": 0, "credit": 605, "description": "Acreedores"},
         ]},
        {"date": iso(TODAY - timedelta(days=15)), "description": "Venta de servicios consultoría",
         "lines": [
             {"account_code": "430", "debit": 1452, "credit": 0, "description": "Clientes"},
             {"account_code": "705", "debit": 0, "credit": 1200, "description": "Prestación de servicios"},
             {"account_code": "477", "debit": 0, "credit": 252, "description": "IVA repercutido 21%"},
         ]},
        {"date": iso(TODAY - timedelta(days=5)), "description": "Pago nóminas marzo",
         "lines": [
             {"account_code": "640", "debit": 11200, "credit": 0, "description": "Sueldos y salarios"},
             {"account_code": "476", "debit": 0, "credit": 1904, "description": "Retenciones IRPF"},
             {"account_code": "572", "debit": 0, "credit": 9296, "description": "Bancos"},
         ]},
    ]
    for e in entries:
        post("/accounting/journal", e, e["description"])

    print("\n== Contabilidad: Activos fijos ==")
    assets = [
        {"name": "Servidor Dell PowerEdge R750", "category": "Equipos informáticos",
         "description": "Servidor principal para ERP y backups",
         "purchase_date": date_str(TODAY - timedelta(days=180)),
         "purchase_value": 8500, "useful_life_years": 5, "residual_value": 500,
         "depreciation_method": "linear", "account_code": "217"},
        {"name": "Furgoneta Renault Kangoo", "category": "Elementos de transporte",
         "description": "Vehículo comercial para entregas",
         "purchase_date": date_str(TODAY - timedelta(days=365)),
         "purchase_value": 18500, "useful_life_years": 8, "residual_value": 3000,
         "depreciation_method": "linear", "account_code": "218"},
    ]
    for a in assets:
        post("/accounting/assets", a, a["name"])


# ─── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed demo data via API")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--base", default="http://localhost:8080")
    args = parser.parse_args()

    global BASE
    BASE = args.base

    print(f"Seed data → {BASE} as {args.email}\n")
    login(args.email, args.password)

    client_ids = seed_clients()
    product_ids = seed_products()
    seed_invoices(client_ids, product_ids)
    seed_quotes(client_ids, product_ids)
    seed_purchase_orders(client_ids)
    seed_sales_orders(client_ids)
    seed_albaranes(client_ids)
    seed_recurring_invoices(client_ids)
    employee_ids = seed_employees()
    seed_payrolls(employee_ids)
    seed_crm(client_ids)
    seed_projects(client_ids, employee_ids)
    seed_accounting()

    print("\n✓ Seed completado. Revisa la app para verificar los datos.")


if __name__ == "__main__":
    main()
