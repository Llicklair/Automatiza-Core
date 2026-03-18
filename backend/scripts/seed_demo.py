"""
Seed de datos demo para AutomatizaPyme.
Pobla la cuenta demo@automatizapyme.com con datos realistas de una PYME española.

Uso:
    python scripts/seed_demo.py
    python scripts/seed_demo.py --reset  (borra todo primero)
"""
import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

# ── Setup path ────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.models import (
    Activity, BankTransaction, Client, Employee, Invoice, InvoiceLine,
    Opportunity, Payroll, Product, Tenant, User,
)

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

DEMO_EMAIL = "demo@automatizapyme.com"

def d(days_ago: int) -> datetime:
    """Fecha relativa a hoy."""
    return datetime.now(UTC) - timedelta(days=days_ago)

def inv_total(base: float, tax: float = 21.0):
    tax_amount = round(base * tax / 100, 2)
    return base, tax_amount, round(base + tax_amount, 2)


# ─── Datos demo ───────────────────────────────────────────────────────────────

CLIENTES = [
    {"name": "Construcciones Valdemar S.L.", "nif": "B12345678", "email": "admin@valdemar.es",
     "city": "Madrid", "postal_code": "28001", "address": "Calle Gran Vía 45", "client_type": "customer"},
    {"name": "Distribuciones Hnos. Pérez", "nif": "B87654321", "email": "compras@hnosperez.com",
     "city": "Barcelona", "postal_code": "08001", "address": "Paseo de Gracia 12", "client_type": "customer"},
    {"name": "Clínica Dental Montserrat", "nif": "B11223344", "email": "facturacion@clinicamontserrat.es",
     "city": "Valencia", "postal_code": "46001", "address": "Avenida del Puerto 8", "client_type": "customer"},
    {"name": "Hotel Rural Las Encinas", "nif": "B44556677", "email": "gestion@lasencinas.es",
     "city": "Segovia", "postal_code": "40001", "address": "Camino de Ronda 3", "client_type": "customer"},
    {"name": "Suministros Técnicos Norte S.A.", "nif": "A99887766", "email": "pedidos@stecnicos.es",
     "city": "Bilbao", "postal_code": "48001", "address": "Gran Vía 67", "client_type": "customer"},
    # Proveedores
    {"name": "Papelería Oficenter", "nif": "B55667788", "email": "ventas@oficenter.es",
     "city": "Madrid", "postal_code": "28010", "address": "Calle Fuencarral 88", "client_type": "supplier"},
    {"name": "Telefonía Empresarial Vodafone", "nif": "A28648817", "email": "empresas@vodafone.es",
     "city": "Madrid", "postal_code": "28050", "address": "Avenida de América 115", "client_type": "supplier"},
]

PRODUCTOS = [
    {"name": "Consultoría Estratégica", "item_type": "service", "sku": "SRV-001",
     "price": 1200.00, "tax_percentage": 21.0, "description": "Sesión de consultoría estratégica (4h)"},
    {"name": "Gestión Contable Mensual", "item_type": "service", "sku": "SRV-002",
     "price": 450.00, "tax_percentage": 21.0, "description": "Servicio mensual de contabilidad y cierres"},
    {"name": "Mantenimiento Informático", "item_type": "service", "sku": "SRV-003",
     "price": 280.00, "tax_percentage": 21.0, "description": "Mantenimiento preventivo y correctivo (8h)"},
    {"name": "Licencia Software ERP", "item_type": "product", "sku": "PRD-001",
     "price": 2400.00, "tax_percentage": 21.0, "description": "Licencia anual software de gestión",
     "stock_quantity": 50, "stock_min_alert": 5},
    {"name": "Formación Online", "item_type": "service", "sku": "SRV-004",
     "price": 350.00, "tax_percentage": 21.0, "description": "Curso online personalizado (8h)"},
    {"name": "Auditoría Fiscal", "item_type": "service", "sku": "SRV-005",
     "price": 1800.00, "tax_percentage": 21.0, "description": "Auditoría completa ejercicio fiscal"},
    {"name": "Hardware Servidor", "item_type": "product", "sku": "PRD-002",
     "price": 3200.00, "tax_percentage": 21.0, "description": "Servidor Dell PowerEdge R350",
     "stock_quantity": 8, "stock_min_alert": 2},
    {"name": "Pack Material Oficina", "item_type": "product", "sku": "PRD-003",
     "price": 85.00, "tax_percentage": 21.0, "description": "Pack mensual material de oficina",
     "stock_quantity": 120, "stock_min_alert": 20},
]

EMPLEADOS = [
    {"name": "Carlos Martínez López", "nif": "12345678A", "department": "Administración",
     "role": "Director Financiero", "base_salary": 3800.00, "status": "active",
     "join_date": d(730)},
    {"name": "María García Sánchez", "nif": "87654321B", "department": "Contabilidad",
     "role": "Contable Senior", "base_salary": 2600.00, "status": "active",
     "join_date": d(540)},
    {"name": "Javier Rodríguez Pérez", "nif": "11223344C", "department": "Tecnología",
     "role": "Desarrollador Backend", "base_salary": 3200.00, "status": "active",
     "join_date": d(365)},
    {"name": "Ana Fernández Torres", "nif": "44556677D", "department": "Comercial",
     "role": "Responsable de Ventas", "base_salary": 2900.00, "status": "active",
     "join_date": d(180)},
    {"name": "Pedro Gómez Ruiz", "nif": "77889900E", "department": "Administración",
     "role": "Asistente Administrativo", "base_salary": 1950.00, "status": "leave",
     "join_date": d(820)},
]


async def reset_tenant_data(db: AsyncSession, tenant_id: uuid.UUID):
    """Borra todos los datos demo del tenant."""
    print("  Borrando datos existentes...")
    for model in [Activity, Opportunity, InvoiceLine, Invoice, Payroll, Employee,
                  Product, Client]:
        await db.execute(delete(model).where(model.tenant_id == tenant_id))
    # BankTransaction tiene campo diferente
    try:
        await db.execute(delete(BankTransaction).where(BankTransaction.tenant_id == tenant_id))
    except Exception:
        pass
    await db.commit()


async def seed(reset: bool = False):
    async with AsyncSessionLocal() as db:
        # Buscar usuario demo
        result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = result.scalar_one_or_none()
        if not user:
            print(f"✗ Usuario demo '{DEMO_EMAIL}' no encontrado.")
            print("  Levanta el stack primero: levantar.bat")
            return

        tenant_id = user.tenant_id
        print(f"✓ Tenant encontrado: {tenant_id}")

        if reset:
            await reset_tenant_data(db, tenant_id)

        # ── Clientes ──────────────────────────────────────────────────────────
        print("  Creando clientes...")
        clientes = []
        for c in CLIENTES:
            obj = Client(tenant_id=tenant_id, **c)
            db.add(obj)
            clientes.append(obj)
        await db.flush()

        customers = [c for c in clientes if c.client_type == "customer"]
        suppliers = [c for c in clientes if c.client_type == "supplier"]

        # ── Productos ─────────────────────────────────────────────────────────
        print("  Creando catálogo de productos/servicios...")
        productos = []
        for p in PRODUCTOS:
            sq = p.pop("stock_quantity", 0)
            sm = p.pop("stock_min_alert", 0)
            obj = Product(tenant_id=tenant_id, stock_quantity=sq, stock_min_alert=sm, **p)
            db.add(obj)
            productos.append(obj)
        await db.flush()

        # ── Facturas emitidas ─────────────────────────────────────────────────
        print("  Creando facturas emitidas...")
        facturas_emitidas = [
            # Pagadas — historial sólido
            (customers[0], 1200.00, "paid",    d(85), d(55),  "2026-001", [("Consultoría Estratégica", 1, 1200)]),
            (customers[1], 450.00,  "paid",    d(75), d(45),  "2026-002", [("Gestión Contable Mensual", 1, 450)]),
            (customers[2], 2400.00, "paid",    d(65), d(35),  "2026-003", [("Licencia Software ERP", 1, 2400)]),
            (customers[3], 560.00,  "paid",    d(60), d(30),  "2026-004", [("Mantenimiento Informático", 2, 280)]),
            (customers[0], 1800.00, "paid",    d(55), d(25),  "2026-005", [("Auditoría Fiscal", 1, 1800)]),
            (customers[4], 3200.00, "paid",    d(45), d(15),  "2026-006", [("Hardware Servidor", 1, 3200)]),
            (customers[1], 450.00,  "paid",    d(40), d(10),  "2026-007", [("Gestión Contable Mensual", 1, 450)]),
            (customers[2], 700.00,  "paid",    d(35), d(5),   "2026-008", [("Formación Online", 2, 350)]),
            # Pendientes de cobro
            (customers[3], 1200.00, "pending", d(20), d(10),  "2026-009", [("Consultoría Estratégica", 1, 1200)]),
            (customers[4], 450.00,  "pending", d(15), d(15),  "2026-010", [("Gestión Contable Mensual", 1, 450)]),
            (customers[0], 3200.00, "pending", d(10), d(20),  "2026-011", [("Hardware Servidor", 1, 3200)]),
            # Borradores
            (customers[1], 1800.00, "draft",   d(5),  d(25),  "2026-012", [("Auditoría Fiscal", 1, 1800)]),
            (customers[2], 280.00,  "draft",   d(2),  d(28),  "2026-013", [("Mantenimiento Informático", 1, 280)]),
        ]

        for client, amount_base, status, date, due_date, number, lines_data in facturas_emitidas:
            _, tax, total = inv_total(amount_base)
            inv = Invoice(
                tenant_id=tenant_id, client_id=client.id,
                invoice_number=number, date=date, due_date=due_date,
                amount_base=amount_base, tax_amount=tax, amount_total=total,
                status=status, invoice_type="issued",
            )
            db.add(inv)
            await db.flush()
            for desc, qty, price in lines_data:
                line_base = qty * price
                _, line_tax, line_total = inv_total(line_base)
                db.add(InvoiceLine(
                    invoice_id=inv.id, description=desc,
                    quantity=qty, unit_price=price,
                    tax_percentage=21.0, total=line_total,
                ))

        # ── Facturas recibidas (compras) ──────────────────────────────────────
        print("  Creando facturas recibidas...")
        facturas_recibidas = [
            (suppliers[0], 320.00,  "paid",    d(80), d(50),  "R-2026-001", [("Material oficina Q1", 1, 320)]),
            (suppliers[1], 180.00,  "paid",    d(70), d(40),  "R-2026-002", [("Plan empresas móvil", 1, 180)]),
            (suppliers[0], 85.00,   "paid",    d(50), d(20),  "R-2026-003", [("Pack Material Oficina", 1, 85)]),
            (suppliers[1], 180.00,  "paid",    d(40), d(10),  "R-2026-004", [("Plan empresas móvil", 1, 180)]),
            (suppliers[0], 85.00,   "pending", d(10), d(20),  "R-2026-005", [("Pack Material Oficina", 1, 85)]),
            (suppliers[1], 180.00,  "pending", d(5),  d(25),  "R-2026-006", [("Plan empresas móvil", 1, 180)]),
        ]

        for client, amount_base, status, date, due_date, number, lines_data in facturas_recibidas:
            _, tax, total = inv_total(amount_base)
            inv = Invoice(
                tenant_id=tenant_id, client_id=client.id,
                invoice_number=number, date=date, due_date=due_date,
                amount_base=amount_base, tax_amount=tax, amount_total=total,
                status=status, invoice_type="received",
            )
            db.add(inv)
            await db.flush()
            for desc, qty, price in lines_data:
                line_base = qty * price
                _, line_tax, line_total = inv_total(line_base)
                db.add(InvoiceLine(
                    invoice_id=inv.id, description=desc,
                    quantity=qty, unit_price=price,
                    tax_percentage=21.0, total=line_total,
                ))

        # ── Empleados ─────────────────────────────────────────────────────────
        print("  Creando empleados...")
        empleados = []
        for e in EMPLEADOS:
            obj = Employee(tenant_id=tenant_id, **e)
            db.add(obj)
            empleados.append(obj)
        await db.flush()

        # ── Nóminas (últimos 3 meses) ─────────────────────────────────────────
        print("  Creando nóminas...")
        for emp in empleados[:4]:  # Solo activos
            for months_ago in [3, 2, 1]:
                start = d(months_ago * 30 + 15)
                end = d(months_ago * 30 - 15)
                sal = float(emp.base_salary)
                deductions = round(sal * 0.065, 2)  # SS trabajador ~6.5%
                net = round(sal - deductions, 2)
                db.add(Payroll(
                    tenant_id=tenant_id,
                    employee_id=emp.id,
                    period_start=start,
                    period_end=end,
                    issue_date=end + timedelta(days=2),
                    base_salary=sal,
                    deductions=deductions,
                    net_salary=net,
                    status="paid",
                ))

        # ── Oportunidades CRM ─────────────────────────────────────────────────
        print("  Creando oportunidades CRM...")
        oportunidades = [
            (customers[0], "Renovación contrato anual consultoría", 14400.00, "proposal"),
            (customers[3], "Implantación sistema de reservas web",  8500.00,  "qualified"),
            (customers[4], "Infraestructura cloud — migración",     22000.00, "new"),
            (customers[1], "Auditoría completa ejercicio 2026",     3600.00,  "won"),
            (customers[2], "Formación equipo dental — 5 personas",  1750.00,  "proposal"),
        ]
        opps = []
        for client, title, value, stage in oportunidades:
            opp = Opportunity(
                tenant_id=tenant_id, client_id=client.id,
                title=title, expected_value=value, stage=stage,
            )
            db.add(opp)
            opps.append(opp)
        await db.flush()

        # ── Actividades CRM ───────────────────────────────────────────────────
        print("  Creando actividades CRM...")
        actividades = [
            (customers[0], opps[0], "call",    "Llamada de seguimiento presupuesto renovación. Interesados.", d(12)),
            (customers[0], opps[0], "email",   "Enviado PDF con propuesta detallada y condiciones.", d(8)),
            (customers[3], opps[1], "meeting_log", "Reunión presencial — detectadas necesidades técnicas adicionales.", d(20)),
            (customers[4], opps[2], "call",    "Primera toma de contacto. Solicitan demo del sistema.", d(5)),
            (customers[1], opps[3], "note",    "Contrato firmado. Inicio previsto el 15 del mes que viene.", d(3)),
            (customers[2], opps[4], "email",   "Enviado calendario de formación propuesto.", d(1)),
        ]
        for client, opp, atype, desc, _date in actividades:
            act = Activity(
                tenant_id=tenant_id,
                client_id=client.id,
                opportunity_id=opp.id,
                type=atype,
                description=desc,
            )
            act.created_at = _date  # Sobreescribir después de construir
            db.add(act)

        # ── Transacciones bancarias ───────────────────────────────────────────
        print("  Creando movimientos bancarios...")
        try:
            movimientos = [
                # Cobros
                ("Transferencia Construcciones Valdemar S.L.",  1452.00,  "reconciled", d(84)),
                ("Pago Distribuciones Hnos. Pérez",             544.50,   "reconciled", d(74)),
                ("Ingreso Clínica Dental Montserrat",           2904.00,  "reconciled", d(64)),
                ("Cobro Hotel Rural Las Encinas",               677.60,   "reconciled", d(58)),
                ("Transferencia Valdemar — Auditoría",          2178.00,  "reconciled", d(54)),
                ("Cobro Suministros Técnicos Norte",            3872.00,  "reconciled", d(44)),
                ("Ingreso Hnos. Pérez — Contable",              544.50,   "reconciled", d(38)),
                ("Cobro Clínica Dental — Formación",            847.00,   "reconciled", d(34)),
                # Pagos
                ("Papelería Oficenter — Material",             -387.20,   "reconciled", d(78)),
                ("Vodafone Empresas — Cuota móvil",            -217.80,   "reconciled", d(68)),
                ("Seguridad Social — Cuota empresarial",       -3240.00,  "reconciled", d(60)),
                ("Nóminas Febrero — transferencia múltiple",   -11830.00, "reconciled", d(59)),
                ("Oficenter — Material trimestral",            -102.85,   "reconciled", d(48)),
                ("Vodafone Empresas — Cuota móvil",            -217.80,   "reconciled", d(38)),
                ("Hacienda — Pago fraccionado IRPF",           -1850.00,  "reconciled", d(30)),
                ("Nóminas Marzo — transferencia múltiple",     -11830.00, "reconciled", d(29)),
                # Recientes sin conciliar
                ("Transferencia pendiente identificar",         1200.00,  "unreconciled", d(7)),
                ("Cargo domiciliado Seguridad Social",         -3240.00,  "unreconciled", d(5)),
                ("Vodafone — cuota corriente",                 -217.80,   "unreconciled", d(3)),
                ("Nóminas Abril — transferencia",              -11830.00, "unreconciled", d(1)),
            ]

            balance = 28_450.00  # Saldo inicial
            for desc, amount, status, date in movimientos:
                balance += amount
                db.add(BankTransaction(
                    tenant_id=tenant_id,
                    date=date.date(),  # BankTransaction.date es Date, no DateTime
                    description=desc,
                    amount=amount,
                    balance=round(balance, 2),
                    status=status,
                ))
        except Exception as e:
            print(f"  ⚠ Transacciones bancarias omitidas ({e.__class__.__name__})")

        await db.commit()
        print("")
        print("✓ Seed completado:")
        print(f"  • {len(CLIENTES)} contactos ({len([c for c in CLIENTES if c['client_type']=='customer'])} clientes, {len([c for c in CLIENTES if c['client_type']=='supplier'])} proveedores)")
        print(f"  • {len(PRODUCTOS)} productos/servicios")
        print(f"  • {len(facturas_emitidas)} facturas emitidas + {len(facturas_recibidas)} recibidas")
        print(f"  • {len(EMPLEADOS)} empleados + {len(EMPLEADOS[:4]) * 3} nóminas")
        print(f"  • {len(oportunidades)} oportunidades CRM + {len(actividades)} actividades")
        print(f"  • 20 movimientos bancarios")
        print("")
        print("  Dashboard: http://localhost:3000")
        print("  Usuario:   demo@automatizapyme.com / Demo1234!")


async def clear_only():
    """Borra todos los datos del tenant demo sin repoblar."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == DEMO_EMAIL))
        user = result.scalar_one_or_none()
        if not user:
            print(f"✗ Usuario demo '{DEMO_EMAIL}' no encontrado.")
            return
        await reset_tenant_data(db, user.tenant_id)
        print("✓ Datos demo eliminados. La cuenta queda vacía.")


if __name__ == "__main__":
    if "--clear" in sys.argv:
        print("⚠ Modo clear: se borran todos los datos sin repoblar.")
        asyncio.run(clear_only())
    elif "--reset" in sys.argv:
        print("⚠ Modo reset: se borran los datos y se repueblan con demo.")
        asyncio.run(seed(reset=True))
    else:
        print("Generando datos demo...")
        asyncio.run(seed(reset=False))
