"""Rutas de tesorería (F2.7) — proyección cashflow + remesas SEPA."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import Tenant, User
from app.middleware.rate_limit import limiter
from app.services.treasury import (
    Pain001Error,
    build_pain001,
    project_cashflow,
)
from app.services.treasury.sepa import DebtorParty, TransferOrder

router = APIRouter(prefix="/treasury", tags=["treasury"])


@router.get("/cashflow/projection")
@limiter.limit("30/minute")
async def get_cashflow_projection(
    request: Request,
    days_ahead: int = Query(default=90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Proyección de cashflow a N días con detección de tensión de liquidez."""
    try:
        return await project_cashflow(db, current_user.tenant_id, days_ahead)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/sepa/pain001", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def generate_pain001(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera un fichero SEPA pain.001.001.03 para remesa de transferencias.

    Body:
        {
          "execution_date": "YYYY-MM-DD",
          "debtor_iban": "ES...",
          "debtor_bic": "BIC..."|null,
          "orders": [
            {"creditor_name": str, "creditor_iban": str, "amount_eur": number, "concept": str}
          ]
        }

    Devuelve `{xml, summary}`. El frontend descarga el XML con
    `application/xml`.
    """
    raw_orders = (payload or {}).get("orders") or []
    if not raw_orders:
        raise HTTPException(status_code=422, detail="Se requiere al menos 1 transferencia.")

    exec_date_raw = (payload or {}).get("execution_date")
    try:
        execution_date = date.fromisoformat(str(exec_date_raw))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="execution_date inválida (YYYY-MM-DD).")

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    debtor_iban = (payload or {}).get("debtor_iban") or getattr(tenant, "iban", None)
    if not debtor_iban:
        raise HTTPException(
            status_code=422,
            detail="No hay IBAN del ordenante. Configura el IBAN del tenant o pásalo en debtor_iban.",
        )

    debtor = DebtorParty(
        name=tenant.name,
        iban=debtor_iban,
        bic=(payload or {}).get("debtor_bic") or getattr(tenant, "bic", None),
    )

    try:
        orders = [
            TransferOrder(
                creditor_name=str(o["creditor_name"]),
                creditor_iban=str(o["creditor_iban"]),
                amount_eur=Decimal(str(o["amount_eur"])),
                concept=str(o.get("concept", "")),
                end_to_end_id=o.get("end_to_end_id"),
            )
            for o in raw_orders
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Estructura de 'orders' inválida: {e}")

    try:
        xml_str, summary = build_pain001(debtor, execution_date, orders)
    except Pain001Error as e:
        raise HTTPException(status_code=422, detail=str(e))

    return {"xml": xml_str, "summary": summary}


@router.post("/sepa/pain001.xml")
@limiter.limit("10/minute")
async def download_pain001(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Variante de descarga directa del XML (Content-Disposition attachment)."""
    result = await generate_pain001(request, payload, db, current_user)
    msg_id = result["summary"]["msg_id"]
    return Response(
        content=result["xml"],
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{msg_id}.xml"'},
    )
