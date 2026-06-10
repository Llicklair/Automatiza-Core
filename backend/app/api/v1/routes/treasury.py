"""Rutas de tesorería (F2.7) — proyección cashflow + remesas SEPA."""

from __future__ import annotations

import uuid
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
    Pain008Error,
    RemittanceError,
    create_direct_debit_remittance,
    create_transfer_remittance,
    get_remittance,
    list_remittances,
    project_cashflow,
    update_remittance_status,
)
from app.services.treasury.sepa import (
    CreditorParty,
    DebtorParty,
    DirectDebitOrder,
    TransferOrder,
)

router = APIRouter(prefix="/treasury", tags=["treasury"])


def _remittance_to_dict(r, *, include_orders: bool = False) -> dict:
    out = {
        "id": str(r.id),
        "remittance_type": r.remittance_type,
        "msg_id": r.msg_id,
        "status": r.status,
        "execution_date": r.execution_date.isoformat(),
        "party_iban": r.party_iban,
        "nb_of_txs": r.nb_of_txs,
        "total_amount": float(r.total_amount),
        "sha256": r.sha256,
        "executed_at": r.executed_at.isoformat() if r.executed_at else None,
        "bank_transaction_id": (
            str(r.bank_transaction_id) if r.bank_transaction_id else None
        ),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
    if include_orders:
        out["orders"] = [
            {
                "id": str(o.id),
                "counterparty_name": o.counterparty_name,
                "counterparty_iban": o.counterparty_iban,
                "amount": float(o.amount),
                "concept": o.concept,
                "end_to_end_id": o.end_to_end_id,
                "mandate_id": o.mandate_id,
                "sequence_type": o.sequence_type,
                "invoice_id": str(o.invoice_id) if o.invoice_id else None,
                "payroll_id": str(o.payroll_id) if o.payroll_id else None,
            }
            for o in r.orders
        ]
    return out


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Identificador inválido.")


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

    links = [
        {
            "invoice_id": _parse_uuid(o["invoice_id"]) if o.get("invoice_id") else None,
            "payroll_id": _parse_uuid(o["payroll_id"]) if o.get("payroll_id") else None,
        }
        for o in raw_orders
    ]

    try:
        remittance = await create_transfer_remittance(
            db, current_user.tenant_id, debtor, execution_date, orders, links=links
        )
    except Pain001Error as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()

    return {
        "xml": remittance.xml,
        "summary": {
            "msg_id": remittance.msg_id,
            "nb_of_txs": remittance.nb_of_txs,
            "control_sum_eur": float(remittance.total_amount),
            "debtor_iban": remittance.party_iban,
            "execution_date": remittance.execution_date.isoformat(),
            "sha256": remittance.sha256,
        },
        "remittance_id": str(remittance.id),
    }


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


@router.post("/sepa/pain008", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def generate_pain008(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Genera y persiste una remesa de adeudos SEPA Core (pain.008.001.02).

    Body:
        {
          "collection_date": "YYYY-MM-DD",
          "creditor_iban": "ES..."|null (default: IBAN del tenant),
          "creditor_id": "ES12000B...",   ← identificador de acreedor SEPA
          "creditor_bic": "BIC..."|null,
          "orders": [
            {"debtor_name": str, "debtor_iban": str, "amount_eur": number,
             "concept": str, "mandate_id": str, "mandate_date": "YYYY-MM-DD",
             "sequence_type": "FRST|RCUR|OOFF|FNAL", "invoice_id": uuid|null}
          ]
        }
    """
    raw_orders = (payload or {}).get("orders") or []
    if not raw_orders:
        raise HTTPException(status_code=422, detail="Se requiere al menos 1 adeudo.")

    try:
        collection_date = date.fromisoformat(str((payload or {}).get("collection_date")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="collection_date inválida (YYYY-MM-DD).")

    creditor_id = (payload or {}).get("creditor_id")
    if not creditor_id:
        raise HTTPException(
            status_code=422,
            detail="Falta creditor_id (identificador de acreedor SEPA).",
        )

    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    ).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tenant no encontrado.")

    creditor_iban = (payload or {}).get("creditor_iban") or getattr(tenant, "iban", None)
    if not creditor_iban:
        raise HTTPException(
            status_code=422,
            detail="No hay IBAN del acreedor. Configura el IBAN del tenant o pásalo en creditor_iban.",
        )

    creditor = CreditorParty(
        name=tenant.name,
        iban=creditor_iban,
        creditor_id=str(creditor_id),
        bic=(payload or {}).get("creditor_bic") or getattr(tenant, "bic", None),
    )

    try:
        orders = [
            DirectDebitOrder(
                debtor_name=str(o["debtor_name"]),
                debtor_iban=str(o["debtor_iban"]),
                amount_eur=Decimal(str(o["amount_eur"])),
                concept=str(o.get("concept", "")),
                mandate_id=str(o["mandate_id"]),
                mandate_date=date.fromisoformat(str(o["mandate_date"])),
                sequence_type=str(o.get("sequence_type", "RCUR")),
                end_to_end_id=o.get("end_to_end_id"),
            )
            for o in raw_orders
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Estructura de 'orders' inválida: {e}")

    links = [
        {
            "invoice_id": _parse_uuid(o["invoice_id"]) if o.get("invoice_id") else None,
            "payroll_id": _parse_uuid(o["payroll_id"]) if o.get("payroll_id") else None,
        }
        for o in raw_orders
    ]

    try:
        remittance = await create_direct_debit_remittance(
            db, current_user.tenant_id, creditor, collection_date, orders, links=links
        )
    except Pain008Error as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()

    return {
        "xml": remittance.xml,
        "summary": {
            "msg_id": remittance.msg_id,
            "nb_of_txs": remittance.nb_of_txs,
            "control_sum_eur": float(remittance.total_amount),
            "creditor_iban": remittance.party_iban,
            "collection_date": remittance.execution_date.isoformat(),
            "sha256": remittance.sha256,
        },
        "remittance_id": str(remittance.id),
    }


# ── Historial y ciclo de vida de remesas ─────────────────────────────


@router.get("/remittances")
@limiter.limit("30/minute")
async def get_remittances(
    request: Request,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historial de remesas SEPA del tenant (más recientes primero)."""
    rows, total = await list_remittances(
        db, current_user.tenant_id, status=status_filter, limit=limit, offset=offset
    )
    return {"items": [_remittance_to_dict(r) for r in rows], "total": total}


@router.get("/remittances/{remittance_id}")
@limiter.limit("30/minute")
async def get_remittance_detail(
    request: Request,
    remittance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Detalle de una remesa con sus órdenes."""
    remittance = await get_remittance(
        db, current_user.tenant_id, _parse_uuid(remittance_id)
    )
    if remittance is None:
        raise HTTPException(status_code=404, detail="Remesa no encontrada.")
    return _remittance_to_dict(remittance, include_orders=True)


@router.get("/remittances/{remittance_id}/xml")
@limiter.limit("30/minute")
async def download_remittance_xml(
    request: Request,
    remittance_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Descarga del XML persistido de la remesa."""
    remittance = await get_remittance(
        db, current_user.tenant_id, _parse_uuid(remittance_id)
    )
    if remittance is None:
        raise HTTPException(status_code=404, detail="Remesa no encontrada.")
    return Response(
        content=remittance.xml,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{remittance.msg_id}.xml"'
        },
    )


@router.post("/remittances/{remittance_id}/status")
@limiter.limit("30/minute")
async def change_remittance_status(
    request: Request,
    remittance_id: str,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Avanza el estado de la remesa: generated → sent → executed → reconciled.

    Body: {"status": str, "bank_transaction_id": uuid|null}
    """
    new_status = (payload or {}).get("status")
    if not new_status:
        raise HTTPException(status_code=422, detail="Falta 'status'.")
    btx_raw = (payload or {}).get("bank_transaction_id")
    try:
        remittance = await update_remittance_status(
            db,
            current_user.tenant_id,
            _parse_uuid(remittance_id),
            str(new_status),
            bank_transaction_id=_parse_uuid(btx_raw) if btx_raw else None,
        )
    except RemittanceError as e:
        raise HTTPException(status_code=422, detail=str(e))
    await db.commit()
    return _remittance_to_dict(remittance)
