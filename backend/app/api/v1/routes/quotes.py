import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.sales import QuoteCreate, QuoteResponse, QuoteUpdate
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.sales import quote as svc

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=QuoteResponse, status_code=201)
@limiter.limit("30/minute")
async def create_quote(
    request: Request,
    quote_in: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = quote_in.model_dump()
    return await svc.create_quote(db, current_user.tenant_id, data)


@router.get("/", response_model=list[QuoteResponse])
@limiter.limit("30/minute")
async def list_quotes(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = Query(default=100, le=100),
):
    return await svc.list_quotes(db, current_user.tenant_id, skip=skip, limit=limit)


@router.get("/{quote_id}", response_model=QuoteResponse)
@limiter.limit("30/minute")
async def get_quote(
    request: Request,
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.get_quote(db, quote_id, current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{quote_id}", response_model=QuoteResponse)
@limiter.limit("30/minute")
async def update_quote(
    request: Request,
    quote_id: UUID,
    quote_update: QuoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        update_data = quote_update.model_dump(exclude_unset=True)
        return await svc.update_quote(db, quote_id, current_user.tenant_id, update_data)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{quote_id}/convert-to-invoice")
@limiter.limit("30/minute")
async def convert_quote_to_invoice(
    request: Request,
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Convierte un presupuesto en una factura real.
    """
    try:
        return await svc.convert_to_invoice(db, quote_id, current_user.tenant_id, current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_quote(
    request: Request,
    quote_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_quote(db, quote_id, current_user.tenant_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
