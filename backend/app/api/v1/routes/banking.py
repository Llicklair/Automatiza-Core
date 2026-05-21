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
    """Genera movimientos DEMO simulando PSD2 (Plaid/Nordigen no integrado).

    Las transacciones quedan prefijadas con [DEMO] para que las analíticas
    reales puedan filtrarlas. Usa DELETE /transactions/demo para borrarlas.
    """
    return await svc.sync_transactions(db, current_user.tenant_id, current_user.id)


@router.delete("/transactions/demo")
@limiter.limit("10/minute")
async def purge_demo_transactions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Borra todas las transacciones demo del tenant."""
    deleted = await svc.purge_demo_transactions(db, current_user.tenant_id)
    return {"status": "ok", "deleted": deleted}


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


@router.post("/transactions/{tx_id}/ignore")
@limiter.limit("20/minute")
async def ignore_transaction(
    request: Request,
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.ignore_transaction(db, current_user.tenant_id, tx_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/transactions/{tx_id}/unreconcile")
@limiter.limit("20/minute")
async def unreconcile_transaction(
    request: Request,
    tx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.unreconcile_transaction(db, current_user.tenant_id, tx_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/reconciliation/suggestions")
@limiter.limit("20/minute")
async def get_reconciliation_suggestions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_reconciliation_suggestions(db, current_user.tenant_id)


@router.post("/reconciliation/reject")
@limiter.limit("30/minute")
async def reject_reconciliation_suggestion(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rechaza una sugerencia tx↔factura. El par no volverá a aparecer (F2.6).

    Body: {"transaction_id": str, "invoice_id": str, "reason": str|null}
    """
    try:
        tx_id = uuid.UUID(str(payload.get("transaction_id")))
        inv_id = uuid.UUID(str(payload.get("invoice_id")))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=422, detail="transaction_id e invoice_id deben ser UUIDs."
        )
    return await svc.reject_reconciliation_suggestion(
        db,
        current_user.tenant_id,
        tx_id,
        inv_id,
        reason=(payload.get("reason") or None),
    )


@router.post("/reconciliation/auto-match")
@limiter.limit("10/minute")
async def auto_reconcile(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.auto_reconcile(db, current_user.tenant_id, current_user.id)


@router.get("/analytics")
@limiter.limit("20/minute")
async def get_banking_analytics(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve datos preprocesados de cashflow y consejos IA para la Home Page."""
    return await svc.get_analytics(db, current_user.tenant_id)
