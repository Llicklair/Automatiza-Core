from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.schemas.accounting import (
    FixedAssetCreate, FixedAssetResponse, FixedAssetUpdate,
    JournalEntryCreate, JournalEntryResponse,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import FixedAsset, JournalEntry, JournalLine, User
from app.middleware.rate_limit import limiter

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
    query = select(JournalEntry).where(JournalEntry.tenant_id == current_user.tenant_id).options(
        selectinload(JournalEntry.lines)
    ).order_by(desc(JournalEntry.date))
    result = await db.execute(query)
    return result.scalars().all()

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
    total_debit = sum(line.debit for line in payload.lines)
    total_credit = sum(line.credit for line in payload.lines)

    # Tolerancia por errores de coma flotante
    if abs(total_debit - total_credit) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El asiento está descuadrado: Debe ({total_debit}) != Haber ({total_credit})"
        )

    new_entry = JournalEntry(
        tenant_id=current_user.tenant_id,
        date=payload.date,
        description=payload.description,
        reference_id=payload.reference_id
    )
    db.add(new_entry)
    await db.flush() # Para obtener el ID del entry

    for line_data in payload.lines:
        new_line = JournalLine(
            tenant_id=current_user.tenant_id,
            entry_id=new_entry.id,
            account_code=line_data.account_code,
            account_name=line_data.account_name,
            debit=line_data.debit,
            credit=line_data.credit
        )
        db.add(new_line)

    await db.commit()
    await db.refresh(new_entry)

    # Recargar con relaciones
    stmt = select(JournalEntry).where(JournalEntry.id == new_entry.id).options(selectinload(JournalEntry.lines))
    res = await db.execute(stmt)

    return res.scalar_one()


# ─── Fixed Assets ─────────────────────────────────────────────────────────────

@router.get("/assets", response_model=list[FixedAssetResponse])
@limiter.limit("30/minute")
async def list_fixed_assets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FixedAsset)
        .where(FixedAsset.tenant_id == current_user.tenant_id)
        .order_by(desc(FixedAsset.created_at))
    )
    return result.scalars().all()


@router.post("/assets", response_model=FixedAssetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_fixed_asset(
    request: Request,
    payload: FixedAssetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = FixedAsset(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.patch("/assets/{asset_id}", response_model=FixedAssetResponse)
@limiter.limit("30/minute")
async def update_fixed_asset(
    request: Request,
    asset_id: UUID,
    payload: FixedAssetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FixedAsset).where(FixedAsset.id == asset_id, FixedAsset.tenant_id == current_user.tenant_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.delete("/journal/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_journal_entry(
    request: Request,
    entry_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.id == entry_id, JournalEntry.tenant_id == current_user.tenant_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Asiento no encontrado")
    await db.delete(entry)
    await db.commit()


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_fixed_asset(
    request: Request,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(FixedAsset).where(FixedAsset.id == asset_id, FixedAsset.tenant_id == current_user.tenant_id)
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    await db.delete(asset)
    await db.commit()
