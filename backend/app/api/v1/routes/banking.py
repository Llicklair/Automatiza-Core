import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.banking import BankTransactionResponse, TransactionReconcile
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services import banking as svc

router = APIRouter(tags=["banking"])


@router.get("/summary")
@limiter.limit("20/minute")
async def get_banking_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Obtiene el resumen financiero del tenant basado en las facturas registradas localmente."""
    return await svc.get_summary(db, current_user.tenant_id)


@router.get("/transactions", response_model=list[BankTransactionResponse])
@limiter.limit("20/minute")
async def list_transactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_transactions(db, current_user.tenant_id)


@router.post("/transactions/sync")
@limiter.limit("20/minute")
async def sync_bank_transactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera movimientos demo simulando conexion PSD2 por Plaid/Nordigen"""
    return await svc.sync_transactions(db, current_user.tenant_id, current_user.id)


@router.post("/transactions/{tx_id}/reconcile")
@limiter.limit("20/minute")
async def reconcile_transaction(
    request: Request,
    tx_id: uuid.UUID,
    payload: TransactionReconcile,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Concilia el movimiento contra una factura"""
    try:
        return await svc.reconcile_transaction(
            db, current_user.tenant_id, current_user.id, tx_id, payload.invoice_id
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/analytics")
@limiter.limit("20/minute")
async def get_banking_analytics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve datos preprocesados de cashflow y consejos IA para la Home Page."""
    return await svc.get_analytics(db, current_user.tenant_id)
