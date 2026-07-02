from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

import app.api.v1.schemas.crm as schemas
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.crm import service as svc

router = APIRouter(prefix="/crm", tags=["crm"])


# ---- Opportunities ----


@router.get("/opportunities", response_model=list[schemas.OpportunityResponse])
@limiter.limit("30/minute")
async def list_opportunities(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_opportunities(db, current_user.tenant_id)


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
    return await svc.create_opportunity(db, current_user.tenant_id, payload.model_dump())


@router.patch("/opportunities/{opp_id}", response_model=schemas.OpportunityResponse)
@limiter.limit("30/minute")
async def update_opportunity(
    request: Request,
    opp_id: UUID,
    payload: schemas.OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_opportunity(db, current_user.tenant_id, opp_id, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/opportunities/{opp_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_opportunity(
    request: Request,
    opp_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_opportunity(db, current_user.tenant_id, opp_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---- Activities ----


@router.get("/activities", response_model=list[schemas.ActivityResponse])
@limiter.limit("30/minute")
async def list_activities(
    request: Request,
    client_id: UUID | None = None,
    opportunity_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_activities(db, current_user.tenant_id, client_id=client_id, opportunity_id=opportunity_id)


@router.post("/activities", response_model=schemas.ActivityResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_activity(
    request: Request,
    payload: schemas.ActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_activity(db, current_user.tenant_id, payload.model_dump())


@router.delete("/activities/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_activity(
    request: Request,
    activity_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_activity(db, current_user.tenant_id, activity_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---- Events / Calendar ----


@router.get("/events", response_model=list[schemas.EventResponse])
@limiter.limit("30/minute")
async def list_events(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_events(db, current_user.tenant_id)


@router.post("/events", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_event(
    request: Request,
    payload: schemas.EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_event(db, current_user.tenant_id, payload.model_dump())


@router.patch("/events/{event_id}", response_model=schemas.EventResponse)
@limiter.limit("30/minute")
async def update_event(
    request: Request,
    event_id: UUID,
    payload: schemas.EventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_event(db, current_user.tenant_id, event_id, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_event(
    request: Request,
    event_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_event(db, current_user.tenant_id, event_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---- Reservations ----


@router.get("/reservations", response_model=list[schemas.ReservationResponse])
@limiter.limit("30/minute")
async def list_reservations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_reservations(db, current_user.tenant_id)


@router.post("/reservations", response_model=schemas.ReservationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_reservation(
    request: Request,
    payload: schemas.ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_reservation(db, current_user.tenant_id, payload.model_dump())


@router.patch("/reservations/{res_id}", response_model=schemas.ReservationResponse)
@limiter.limit("30/minute")
async def update_reservation(
    request: Request,
    res_id: UUID,
    payload: schemas.ReservationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_reservation(db, current_user.tenant_id, res_id, payload.model_dump(exclude_unset=True))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/reservations/{res_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_reservation(
    request: Request,
    res_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_reservation(db, current_user.tenant_id, res_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
