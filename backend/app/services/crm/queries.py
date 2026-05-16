"""CRM queries — read-only operations (CQRS-lite).

No side effects: no INSERT/UPDATE/DELETE, no file writes, no commits.
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Activity, Event, Opportunity, Reservation

# ---- Opportunities ----


async def list_opportunities(db: AsyncSession, tenant_id: UUID) -> list[Opportunity]:
    query = (
        select(Opportunity)
        .where(Opportunity.tenant_id == tenant_id)
        .order_by(desc(Opportunity.created_at))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ---- Activities ----


async def list_activities(
    db: AsyncSession,
    tenant_id: UUID,
    client_id: UUID | None = None,
    opportunity_id: UUID | None = None,
) -> list[Activity]:
    query = select(Activity).where(Activity.tenant_id == tenant_id)
    if client_id:
        query = query.where(Activity.client_id == client_id)
    if opportunity_id:
        query = query.where(Activity.opportunity_id == opportunity_id)
    query = query.order_by(desc(Activity.created_at))
    result = await db.execute(query)
    return list(result.scalars().all())


# ---- Events ----


async def list_events(db: AsyncSession, tenant_id: UUID) -> list[Event]:
    query = select(Event).where(Event.tenant_id == tenant_id).order_by(Event.start_time)
    result = await db.execute(query)
    return list(result.scalars().all())


# ---- Reservations ----


async def list_reservations(db: AsyncSession, tenant_id: UUID) -> list[Reservation]:
    query = (
        select(Reservation)
        .where(Reservation.tenant_id == tenant_id)
        .order_by(desc(Reservation.created_at))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


# ---- Contract builder helpers (pure, no side effects) ----


def build_context_for_client(client, tenant) -> dict:
    import uuid
    from datetime import date

    today = date.today()
    ctx = {
        "nombre_cliente": client.name or "",
        "nif_cliente": client.nif or "",
        "direccion_cliente": client.address or "",
        "email_cliente": client.email or "",
        "telefono_cliente": client.phone or "",
        "fecha": today.strftime("%d/%m/%Y"),
        "numero_contrato": f"CT-{today.year}-{uuid.uuid4().hex[:6].upper()}",
    }
    ctx.update(_tenant_context(tenant))
    return ctx


def build_context_for_employee(employee, tenant) -> dict:
    import uuid
    from datetime import date

    today = date.today()
    ctx = {
        "nombre_empleado": employee.name or "",
        "nif_empleado": employee.nif or "",
        "email_empleado": employee.email or "",
        "departamento": employee.department or "",
        "puesto": employee.role or "",
        "salario_base": str(employee.base_salary or ""),
        "fecha_inicio": _fmt_date(employee.join_date),
        "fecha_fin_contrato": _fmt_date(employee.contract_end_date),
        # Aliases que también puede usar la plantilla
        "nombre_cliente": employee.name or "",
        "nif_cliente": employee.nif or "",
        "fecha": today.strftime("%d/%m/%Y"),
        "numero_contrato": f"CT-{today.year}-{uuid.uuid4().hex[:6].upper()}",
    }
    ctx.update(_tenant_context(tenant))
    return ctx


# ---- Private helpers ----


def _fmt_date(dt) -> str:
    if dt is None:
        return ""
    return dt.strftime("%d/%m/%Y")


def _tenant_context(tenant) -> dict:
    return {
        "nombre_empresa": tenant.name or "",
        "nif_empresa": tenant.nif or "",
        "direccion_empresa": tenant.address or "",
        "email_empresa": tenant.contact_email or "",
        "telefono_empresa": tenant.phone or "",
    }
