"""
DB fetchers for the Excel agent.
Each fetcher returns a pandas DataFrame from the ERP database.
"""

import uuid

import pandas as pd
from sqlalchemy.future import select

from app.db.base import AsyncSessionLocal
from app.db.models.accounting import BankTransaction
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.hr import Employee, Payroll
from app.db.models.inventory import Product


async def _fetch_invoices(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Invoice, Client.name.label("client_name"))
            .join(Client, Invoice.client_id == Client.id)
            .where(Invoice.tenant_id == uuid.UUID(tenant_id))
            .order_by(Invoice.date.desc())
            .limit(500)
        )
        rows = result.all()
    if not rows:
        return pd.DataFrame(
            columns=["Número", "Cliente", "Fecha", "Base (€)", "IVA (€)", "Total (€)", "Estado"]
        )
    return pd.DataFrame(
        [
            {
                "Número": inv.invoice_number or "",
                "Cliente": cn or "",
                "Fecha": inv.date.strftime("%d/%m/%Y") if inv.date else "",
                "Base (€)": float(inv.amount_base or 0),
                "IVA (€)": float(inv.tax_amount or 0),
                "Total (€)": float(inv.amount_total or 0),
                "Estado": inv.status or "",
            }
            for inv, cn in rows
        ]
    )


async def _fetch_clients(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Client)
            .where(Client.tenant_id == uuid.UUID(tenant_id))
            .order_by(Client.name)
            .limit(500)
        )
        clients = result.scalars().all()
    if not clients:
        return pd.DataFrame(columns=["Nombre", "NIF/CIF", "Email", "Tipo"])
    return pd.DataFrame(
        [
            {
                "Nombre": c.name or "",
                "NIF/CIF": c.nif or "",
                "Email": c.email or "",
                "Tipo": c.client_type or "",
            }
            for c in clients
        ]
    )


async def _fetch_employees(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Employee)
            .where(Employee.tenant_id == uuid.UUID(tenant_id))
            .order_by(Employee.name)
        )
        employees = result.scalars().all()
    if not employees:
        return pd.DataFrame(
            columns=["Nombre", "NIF", "Departamento", "Puesto", "Salario Base (€)", "IRPF (%)", "Estado"]
        )
    return pd.DataFrame(
        [
            {
                "Nombre": e.name or "",
                "NIF": e.nif or "",
                "Departamento": e.department or "",
                "Puesto": e.role or "",
                "Salario Base (€)": float(e.base_salary or 0),
                "IRPF (%)": float(e.irpf_rate or 0),
                "Estado": e.status or "",
            }
            for e in employees
        ]
    )


async def _fetch_payrolls(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Payroll, Employee.name.label("emp_name"))
            .join(Employee, Payroll.employee_id == Employee.id)
            .where(Payroll.tenant_id == uuid.UUID(tenant_id))
            .order_by(Payroll.issue_date.desc())
            .limit(500)
        )
        rows = result.all()
    if not rows:
        return pd.DataFrame(
            columns=["Empleado", "Período", "Salario Base (€)", "SS (€)", "IRPF (€)", "Neto (€)", "Estado"]
        )
    return pd.DataFrame(
        [
            {
                "Empleado": en or "",
                "Período": f"{p.period_start.strftime('%d/%m/%Y')} - {p.period_end.strftime('%d/%m/%Y')}"
                if p.period_start
                else "",
                "Salario Base (€)": float(p.base_salary or 0),
                "SS (€)": float(
                    (p.ss_contingencias_comunes or 0)
                    + (p.ss_desempleo or 0)
                    + (p.ss_formacion_profesional or 0)
                    + (p.ss_mei or 0)
                ),
                "IRPF (€)": float(p.irpf or 0),
                "Neto (€)": float(p.net_salary or 0),
                "Estado": p.status or "",
            }
            for p, en in rows
        ]
    )


async def _fetch_products(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product)
            .where(Product.tenant_id == uuid.UUID(tenant_id))
            .order_by(Product.name)
            .limit(500)
        )
        products = result.scalars().all()
    if not products:
        return pd.DataFrame(columns=["Nombre", "SKU", "Tipo", "Precio (€)", "Stock"])
    return pd.DataFrame(
        [
            {
                "Nombre": p.name or "",
                "SKU": p.sku or "",
                "Tipo": p.item_type or "",
                "Precio (€)": float(p.price or 0),
                "Stock": int(p.stock_quantity or 0),
            }
            for p in products
        ]
    )


async def _fetch_bank(tenant_id: str) -> pd.DataFrame:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BankTransaction)
            .where(BankTransaction.tenant_id == uuid.UUID(tenant_id))
            .order_by(BankTransaction.date.desc())
            .limit(500)
        )
        txs = result.scalars().all()
    if not txs:
        return pd.DataFrame(columns=["Fecha", "Concepto", "Importe (€)", "Saldo (€)", "Estado"])
    return pd.DataFrame(
        [
            {
                "Fecha": t.date.strftime("%d/%m/%Y") if t.date else "",
                "Concepto": t.description or "",
                "Importe (€)": float(t.amount or 0),
                "Saldo (€)": float(t.balance or 0),
                "Estado": t.status or "",
            }
            for t in txs
        ]
    )


_FETCHER_MAP = {
    "facturas": _fetch_invoices,
    "clientes": _fetch_clients,
    "empleados": _fetch_employees,
    "nominas": _fetch_payrolls,
    "productos": _fetch_products,
    "banco": _fetch_bank,
}

_INTENT_MAP = [
    (["factura", "invoice", "venta", "cobro", "ingreso"], "facturas"),
    (["empleado", "trabajador", "plantilla", "rrhh", "personal"], "empleados"),
    (["nómina", "nomina", "salario", "sueldo"], "nominas"),
    (["cliente", "client", "cuenta", "crm"], "clientes"),
    (["producto", "catalogo", "catálogo", "inventario", "stock"], "productos"),
    (["banco", "bank", "movimiento", "transaccion"], "banco"),
]


def _detect_datasets(intent: str) -> list[str]:
    intent_lower = intent.lower()
    matched = []
    for keywords, key in _INTENT_MAP:
        if any(kw in intent_lower for kw in keywords):
            if key not in matched:
                matched.append(key)
    return matched or ["facturas"]
