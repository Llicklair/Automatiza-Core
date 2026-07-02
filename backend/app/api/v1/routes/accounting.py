from datetime import date as date_type
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from pydantic import BaseModel
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
from app.services.accounting import (
    PeriodClosedError,
    close_period,
    generate_balance_pyg_pdf,
    generate_libro_diario_pdf,
    generate_libro_mayor_pdf,
    is_date_locked,
    list_periods,
    reopen_period,
)
from app.services.billing import accounting as svc

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
            lines=[line.model_dump() for line in payload.lines],
        )
    except PeriodClosedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
    except PeriodClosedError as exc:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ─── Cierre de periodo + libros oficiales ─────────────────────────────────────


class _ClosePeriodIn(BaseModel):
    year: int
    kind: str  # 'month' | 'quarter' | 'year'
    period_index: int
    notes: str | None = None


class _ReopenIn(BaseModel):
    reason: str


def _period_to_dict(p) -> dict:
    return {
        "id": str(p.id),
        "year": p.year,
        "kind": p.kind,
        "period_index": p.period_index,
        "status": p.status,
        "closed_at": p.closed_at.isoformat() if p.closed_at else None,
        "reopened_at": p.reopened_at.isoformat() if p.reopened_at else None,
        "reopen_reason": p.reopen_reason,
        "notes": p.notes,
    }


@router.get("/periods")
@limiter.limit("30/minute")
async def list_accounting_periods(
    request: Request,
    year: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista de periodos cerrados/reabiertos del tenant."""
    periods = await list_periods(db, current_user.tenant_id, year)
    return {"items": [_period_to_dict(p) for p in periods]}


@router.post("/periods/close", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def close_accounting_period(
    request: Request,
    payload: _ClosePeriodIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cierra un periodo contable. A partir de aquí los asientos del rango quedan bloqueados."""
    try:
        period = await close_period(
            db,
            current_user.tenant_id,
            current_user.id,
            payload.year,
            payload.kind,
            payload.period_index,
            payload.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return _period_to_dict(period)


@router.post("/periods/{period_id}/reopen")
@limiter.limit("5/minute")
async def reopen_accounting_period(
    request: Request,
    period_id: UUID,
    payload: _ReopenIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reabre un periodo cerrado. Requiere motivo y queda auditado."""
    try:
        period = await reopen_period(db, current_user.tenant_id, current_user.id, period_id, payload.reason)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _period_to_dict(period)


@router.get("/check-locked")
@limiter.limit("60/minute")
async def check_date_locked(
    request: Request,
    target: date_type = Query(..., description="Fecha a comprobar (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Indica si una fecha cae en un periodo cerrado."""
    locked, label = await is_date_locked(db, current_user.tenant_id, target)
    return {"locked": locked, "period_label": label}


def _parse_range(start: date_type, end: date_type) -> tuple[date_type, date_type]:
    if end < start:
        raise HTTPException(status_code=400, detail="La fecha 'end' debe ser >= 'start'")
    return start, end


@router.get("/libro-diario.pdf")
@limiter.limit("10/minute")
async def libro_diario_pdf(
    request: Request,
    start: date_type = Query(...),
    end: date_type = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Libro Diario oficial en PDF del periodo solicitado."""
    s, e = _parse_range(start, end)
    pdf = await generate_libro_diario_pdf(db, current_user.tenant_id, s, e)
    fname = f"LibroDiario_{s.isoformat()}_{e.isoformat()}.pdf"
    return Response(
        content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@router.get("/libro-mayor.pdf")
@limiter.limit("10/minute")
async def libro_mayor_pdf(
    request: Request,
    start: date_type = Query(...),
    end: date_type = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Libro Mayor oficial en PDF (apuntes agrupados por cuenta con saldo acumulado)."""
    s, e = _parse_range(start, end)
    pdf = await generate_libro_mayor_pdf(db, current_user.tenant_id, s, e)
    fname = f"LibroMayor_{s.isoformat()}_{e.isoformat()}.pdf"
    return Response(
        content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )


@router.get("/cuentas-anuales.pdf")
@limiter.limit("10/minute")
async def cuentas_anuales_pdf(
    request: Request,
    start: date_type = Query(...),
    end: date_type = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cuentas Anuales Abreviadas (Balance + P&G) en PDF."""
    s, e = _parse_range(start, end)
    pdf = await generate_balance_pyg_pdf(db, current_user.tenant_id, s, e)
    fname = f"CuentasAnuales_{s.isoformat()}_{e.isoformat()}.pdf"
    return Response(
        content=pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'}
    )
