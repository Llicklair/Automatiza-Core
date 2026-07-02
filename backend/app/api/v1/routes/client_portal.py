"""Portal externo de clientes — autenticación por token + vista de facturas."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_client_portal, get_current_user
from app.core.security import create_client_portal_access_token
from app.db.base import get_db
from app.db.models.crm import Client
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.billing import invoice as invoice_svc
from app.services.client_portal import (
    PortalAuthError,
    authenticate_and_stamp,
    get_invoice_for_client,
    get_portal_me,
    get_portal_token_status,
    hash_token,
    issue_token,
    revoke_portal_tokens,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/client-portal", tags=["client-portal"])


class PortalAuthRequest(BaseModel):
    """Body del intercambio token bruto → JWT del portal."""

    token: str = Field(min_length=1, max_length=256)


# ── Admin: generar / revocar token para un cliente ───────────────────────────


@router.get("/admin/tokens/{client_id}", tags=["client-portal"])
@limiter.limit("30/minute")
async def get_portal_token_status_route(
    request: Request,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await get_portal_token_status(
        client_id=client_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )


@router.post("/admin/tokens/{client_id}", tags=["client-portal"])
@limiter.limit("10/minute")
async def generate_portal_token(
    request: Request,
    client_id: UUID,
    days_valid: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify client belongs to tenant (validación de transporte)
    cl_res = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.tenant_id == current_user.tenant_id,
        )
    )
    client = cl_res.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    raw_token, new_token = await issue_token(
        client_id=client_id,
        tenant_id=current_user.tenant_id,
        days_valid=days_valid,
        db=db,
    )

    # Construir la URL pública del portal si está configurada. Si no, devolver None
    # y dejar que el frontend caiga al fallback con advertencia.
    public_base = (settings.PORTAL_PUBLIC_URL or "").rstrip("/")
    portal_url = f"{public_base}/portal-cliente?token={raw_token}" if public_base else None

    return {
        "raw_token": raw_token,
        "portal_url": portal_url,
        "expires_at": new_token.expires_at.isoformat(),
        "message": f"Enlace de portal válido {days_valid} días",
    }


@router.delete("/admin/tokens/{client_id}", status_code=204, tags=["client-portal"])
@limiter.limit("10/minute")
async def revoke_portal_token(
    request: Request,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await revoke_portal_tokens(
        client_id=client_id,
        tenant_id=current_user.tenant_id,
        db=db,
    )


# ── Público: intercambiar token → JWT ────────────────────────────────────────


@router.post("/auth", tags=["client-portal"])
@limiter.limit("10/minute")
async def authenticate_portal(
    request: Request,
    payload: PortalAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_token(payload.token)
    try:
        portal_token = await authenticate_and_stamp(token_hash=token_hash, db=db)
    except PortalAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    access_token = create_client_portal_access_token(str(portal_token.client_id), str(portal_token.tenant_id))
    return {"access_token": access_token, "token_type": "bearer"}


# ── Autenticado (client_portal JWT) ─────────────────────────────────────────


@router.get("/me", tags=["client-portal"])
@limiter.limit("60/minute")
async def portal_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client_portal),
):
    return await get_portal_me(client=client, db=db)


@router.get("/invoices/{invoice_id}/pdf", tags=["client-portal"])
@limiter.limit("20/minute")
async def portal_download_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client_portal),
):
    # Verify invoice belongs to this client (ownership guard — stays in route layer)
    if not await get_invoice_for_client(invoice_id=invoice_id, client=client, db=db):
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    try:
        pdf_bytes, file_name = await invoice_svc.build_invoice_pdf(invoice_id, client.tenant_id, db)
    except ValueError as e:
        logger.warning("[PORTAL] Error generando PDF factura %s: %s", invoice_id, e)
        raise HTTPException(status_code=404, detail="No se pudo generar el PDF de la factura") from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
