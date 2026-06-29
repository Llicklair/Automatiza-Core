"""Búsqueda global multi-entidad (empleados, clientes, facturas) por tenant."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.hr import Employee


async def global_search(db: AsyncSession, tenant_id: UUID, q: str) -> list[dict]:
    """Busca ``q`` (ILIKE, metacaracteres escapados) en empleados/clientes/facturas
    del tenant; devuelve hasta 5 resultados por tipo, ya formateados para el frontend.
    """
    results: list[dict] = []

    # Escapar metacaracteres LIKE para que %/_/\ del usuario sean literales,
    # no comodines (mismo patrón que services/sales/queries.py).
    q_esc = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    like = f"%{q_esc}%"

    rows = await db.execute(
        select(Employee)
        .where(
            Employee.tenant_id == tenant_id,
            or_(
                Employee.name.ilike(like, escape="\\"),
                Employee.email.ilike(like, escape="\\"),
                Employee.nif.ilike(like, escape="\\"),
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

    rows = await db.execute(
        select(Client)
        .where(
            Client.tenant_id == tenant_id,
            or_(
                Client.name.ilike(like, escape="\\"),
                Client.email.ilike(like, escape="\\"),
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

    rows = await db.execute(
        select(Invoice)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.invoice_number.ilike(like, escape="\\"),
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
