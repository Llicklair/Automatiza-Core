from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.schemas.crm as schemas
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Activity, Event, Opportunity, Reservation, User
from app.middleware.rate_limit import limiter

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/opportunities", response_model=list[schemas.OpportunityResponse])
@limiter.limit("30/minute")
async def list_opportunities(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Opportunity)
        .where(Opportunity.tenant_id == current_user.tenant_id)
        .order_by(desc(Opportunity.created_at))
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/opportunities",
    response_model=schemas.OpportunityResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_opportunity(
    request: Request,
    payload: schemas.OpportunityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_opp = Opportunity(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_opp)
    await db.commit()
    await db.refresh(new_opp)
    return new_opp


@router.patch("/opportunities/{opp_id}", response_model=schemas.OpportunityResponse)
@limiter.limit("30/minute")
async def update_opportunity(
    request: Request,
    opp_id: UUID,
    payload: schemas.OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.tenant_id == current_user.tenant_id
        )
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(opp, key, value)

    await db.commit()
    await db.refresh(opp)
    return opp


# --- Activities ---


@router.get("/activities", response_model=list[schemas.ActivityResponse])
@limiter.limit("30/minute")
async def list_activities(
    request: Request,
    client_id: UUID = None,
    opportunity_id: UUID = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Activity).where(Activity.tenant_id == current_user.tenant_id)
    if client_id:
        query = query.where(Activity.client_id == client_id)
    if opportunity_id:
        query = query.where(Activity.opportunity_id == opportunity_id)

    query = query.order_by(desc(Activity.created_at))
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/activities", response_model=schemas.ActivityResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_activity(
    request: Request,
    payload: schemas.ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_act = Activity(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_act)
    await db.commit()
    await db.refresh(new_act)
    return new_act


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_activity(
    request: Request,
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Activity).where(
            Activity.id == activity_id, Activity.tenant_id == current_user.tenant_id
        )
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    await db.delete(activity)
    await db.commit()


# --- Events / Calendar ---


@router.get("/events", response_model=list[schemas.EventResponse])
@limiter.limit("30/minute")
async def list_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Event).where(Event.tenant_id == current_user.tenant_id).order_by(Event.start_time)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/events", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_event(
    request: Request,
    payload: schemas.EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_evt = Event(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_evt)
    await db.commit()
    await db.refresh(new_evt)
    return new_evt


# --- Reservations ---


@router.get("/reservations", response_model=list[schemas.ReservationResponse])
@limiter.limit("30/minute")
async def list_reservations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(Reservation)
        .where(Reservation.tenant_id == current_user.tenant_id)
        .order_by(desc(Reservation.created_at))
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/reservations", response_model=schemas.ReservationResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_reservation(
    request: Request,
    payload: schemas.ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_res = Reservation(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(new_res)
    await db.commit()
    await db.refresh(new_res)
    return new_res


@router.patch("/reservations/{res_id}", response_model=schemas.ReservationResponse)
@limiter.limit("30/minute")
async def update_reservation(
    request: Request,
    res_id: UUID,
    payload: schemas.ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == res_id, Reservation.tenant_id == current_user.tenant_id
        )
    )
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(res, key, value)
    await db.commit()
    await db.refresh(res)
    return res


@router.delete("/reservations/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_reservation(
    request: Request,
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Reservation).where(
            Reservation.id == res_id, Reservation.tenant_id == current_user.tenant_id
        )
    )
    res = result.scalar_one_or_none()
    if not res:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    await db.delete(res)
    await db.commit()


# --- Events PATCH / DELETE ---


@router.patch("/events/{event_id}", response_model=schemas.EventResponse)
@limiter.limit("30/minute")
async def update_event(
    request: Request,
    event_id: UUID,
    payload: schemas.EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.tenant_id == current_user.tenant_id)
    )
    evt = result.scalar_one_or_none()
    if not evt:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(evt, key, value)
    await db.commit()
    await db.refresh(evt)
    return evt


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_event(
    request: Request,
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Event).where(Event.id == event_id, Event.tenant_id == current_user.tenant_id)
    )
    evt = result.scalar_one_or_none()
    if not evt:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    await db.delete(evt)
    await db.commit()


# --- Opportunities DELETE ---


@router.delete("/opportunities/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_opportunity(
    request: Request,
    opp_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Opportunity).where(
            Opportunity.id == opp_id, Opportunity.tenant_id == current_user.tenant_id
        )
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise HTTPException(status_code=404, detail="Oportunidad no encontrada")
    await db.delete(opp)
    await db.commit()
