from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.hr import Employee

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    results: list[dict] = []

    # Employees
    rows = await db.execute(
        select(Employee)
        .where(
            Employee.tenant_id == tenant_id,
            or_(
                Employee.name.ilike(f"%{q}%"),
                Employee.email.ilike(f"%{q}%"),
                Employee.nif.ilike(f"%{q}%"),
            ),
        )
        .limit(5)
    )
    for emp in rows.scalars():
        results.append(
            {
                "type": "employee",
                "id": str(emp.id),
                "label": emp.name,
                "sublabel": " · ".join(filter(None, [emp.role, emp.department])),
                "href": "/rrhh/empleados",
            }
        )

    # Clients
    rows = await db.execute(
        select(Client)
        .where(
            Client.tenant_id == tenant_id,
            or_(
                Client.name.ilike(f"%{q}%"),
                Client.email.ilike(f"%{q}%"),
            ),
        )
        .limit(5)
    )
    for c in rows.scalars():
        results.append(
            {
                "type": "client",
                "id": str(c.id),
                "label": c.name,
                "sublabel": c.email or "",
                "href": "/clientes",
            }
        )

    # Invoices
    rows = await db.execute(
        select(Invoice)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number.ilike(f"%{q}%"),
        )
        .limit(5)
    )
    for inv in rows.scalars():
        results.append(
            {
                "type": "invoice",
                "id": str(inv.id),
                "label": f"Factura {inv.invoice_number}",
                "sublabel": inv.status or "",
                "href": "/ventas/facturas",
            }
        )

    return results
