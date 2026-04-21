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


async def create_opportunity(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> Opportunity:
    opp = Opportunity(tenant_id=tenant_id, **data)
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


async def update_opportunity(
    db: AsyncSession, tenant_id: UUID, opp_id: UUID, data: dict
) -> Opportunity:
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id
        )
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise LookupError("Oportunidad no encontrada")
    for key, value in data.items():
        setattr(opp, key, value)
    await db.commit()
    await db.refresh(opp)
    return opp


async def delete_opportunity(
    db: AsyncSession, tenant_id: UUID, opp_id: UUID
) -> None:
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.tenant_id == tenant_id
        )
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise LookupError("Oportunidad no encontrada")
    await db.delete(opp)
    await db.commit()


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


async def create_activity(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> Activity:
    act = Activity(tenant_id=tenant_id, **data)
    db.add(act)
    await db.commit()
    await db.refresh(act)
    return act


async def delete_activity(
    db: AsyncSession, tenant_id: UUID, activity_id: UUID
) -> None:
    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id, Activity.tenant_id == tenant_id
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise LookupError("Activity not found")
    await db.delete(activity)
    await db.commit()


# ---- Events ----


async def list_events(db: AsyncSession, tenant_id: UUID) -> list[Event]:
    query = (
        select(Event)
        .where(Event.tenant_id == tenant_id)
        .order_by(Event.start_time)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_event(db: AsyncSession, tenant_id: UUID, data: dict) -> Event:
    evt = Event(tenant_id=tenant_id, **data)
    db.add(evt)
    await db.commit()
    await db.refresh(evt)
    return evt


async def update_event(
    db: AsyncSession, tenant_id: UUID, event_id: UUID, data: dict
) -> Event:
    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.tenant_id == tenant_id
        )
    )
    evt = result.scalar_one_or_none()
    if not evt:
        raise LookupError("Evento no encontrado")
    for key, value in data.items():
        setattr(evt, key, value)
    await db.commit()
    await db.refresh(evt)
    return evt


async def delete_event(
    db: AsyncSession, tenant_id: UUID, event_id: UUID
) -> None:
    result = await db.execute(
        select(Event).where(
            Event.id == event_id, Event.tenant_id == tenant_id
        )
    )
    evt = result.scalar_one_or_none()
    if not evt:
        raise LookupError("Evento no encontrado")
    await db.delete(evt)
    await db.commit()


# ---- Reservations ----


async def list_reservations(
    db: AsyncSession, tenant_id: UUID
) -> list[Reservation]:
    query = (
        select(Reservation)
        .where(Reservation.tenant_id == tenant_id)
        .order_by(desc(Reservation.created_at))
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_reservation(
    db: AsyncSession, tenant_id: UUID, data: dict
) -> Reservation:
    res = Reservation(tenant_id=tenant_id, **data)
    db.add(res)
    await db.commit()
    await db.refresh(res)
    return res


async def update_reservation(
    db: AsyncSession, tenant_id: UUID, res_id: UUID, data: dict
) -> Reservation:
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == res_id, Reservation.tenant_id == tenant_id
        )
    )
    res = result.scalar_one_or_none()
    if not res:
        raise LookupError("Reserva no encontrada")
    for key, value in data.items():
        setattr(res, key, value)
    await db.commit()
    await db.refresh(res)
    return res


async def delete_reservation(
    db: AsyncSession, tenant_id: UUID, res_id: UUID
) -> None:
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == res_id, Reservation.tenant_id == tenant_id
        )
    )
    res = result.scalar_one_or_none()
    if not res:
        raise LookupError("Reserva no encontrada")
    await db.delete(res)
    await db.commit()
