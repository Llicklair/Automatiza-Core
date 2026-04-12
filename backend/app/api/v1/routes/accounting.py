from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.accounting import (
    FixedAssetCreate,
    FixedAssetResponse,
    FixedAssetUpdate,
    JournalEntryCreate,
    JournalEntryResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services import accounting_service as svc

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("/journal", response_model=list[JournalEntryResponse])
@limiter.limit("30/minute")
async def list_journal_entries(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Devuelve los asientos del libro diario en orden cronológico inverso,
    incluyendo sus respectivas líneas (debe/haber).
    """
    return await svc.list_journal_entries(db, current_user.tenant_id)


@router.post("/journal", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_journal_entry(
    request: Request,
    payload: JournalEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Crea un asiento contable. Valida que el Debe y el Haber cuadren.
    """
    try:
        return await svc.create_journal_entry(
            db,
            current_user.tenant_id,
            date=payload.date,
            description=payload.description,
            reference_id=payload.reference_id,
            lines=[l.model_dump() for l in payload.lines],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_journal_entry(
    request: Request,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_journal_entry(db, current_user.tenant_id, entry_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ─── Fixed Assets ─────────────────────────────────────────────────────────────


@router.get("/assets", response_model=list[FixedAssetResponse])
@limiter.limit("30/minute")
async def list_fixed_assets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_fixed_assets(db, current_user.tenant_id)


@router.post("/assets", response_model=FixedAssetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_fixed_asset(
    request: Request,
    payload: FixedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_fixed_asset(db, current_user.tenant_id, payload.model_dump())


@router.patch("/assets/{asset_id}", response_model=FixedAssetResponse)
@limiter.limit("30/minute")
async def update_fixed_asset(
    request: Request,
    asset_id: UUID,
    payload: FixedAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_fixed_asset(
            db, current_user.tenant_id, asset_id, payload.model_dump(exclude_unset=True)
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_fixed_asset(
    request: Request,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_fixed_asset(db, current_user.tenant_id, asset_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
