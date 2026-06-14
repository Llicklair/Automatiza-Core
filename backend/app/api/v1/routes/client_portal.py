"""Portal externo de clientes — autenticación por token + vista de facturas."""
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.datetime_utils import as_aware
from app.core.dependencies import get_current_client_portal, get_current_user
from app.core.security import create_client_portal_access_token
from app.db.base import get_db
from app.db.models.auth import ClientPortalToken
from app.db.models.billing import Invoice, Quote
from app.db.models.crm import Client
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.billing import invoice as invoice_svc
from app.services.client_portal.tokens import hash_token, issue_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/client-portal", tags=["client-portal"])


class PortalAuthRequest(BaseModel):
    """Body del intercambio token bruto → JWT del portal."""

    token: str = Field(min_length=1, max_length=256)


# ── Admin: generar / revocar token para un cliente ───────────────────────────

@router.get("/admin/tokens/{client_id}", tags=["client-portal"])
@limiter.limit("30/minute")
async def get_portal_token_status(
    request: Request,
    client_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    row = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.client_id == client_id,
            ClientPortalToken.tenant_id == current_user.tenant_id,
            ClientPortalToken.is_active.is_(True),
        )
    )
    token = row.scalar_one_or_none()
    return {
        "has_token": token is not None,
        "expires_at": token.expires_at.isoformat() if token and token.expires_at else None,
        "created_at": token.created_at.isoformat() if token else None,
        "last_used_at": token.last_used_at.isoformat() if token and token.last_used_at else None,
    }


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
        select(Client).where(Client.id == client_id, Client.tenant_id == current_user.tenant_id)
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
    existing = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.client_id == client_id,
            ClientPortalToken.tenant_id == current_user.tenant_id,
        )
    )
    for t in existing.scalars():
        t.is_active = False
    await db.commit()


# ── Público: intercambiar token → JWT ────────────────────────────────────────

@router.post("/auth", tags=["client-portal"])
@limiter.limit("10/minute")
async def authenticate_portal(
    request: Request,
    payload: PortalAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    raw_token = payload.token
    token_hash = hash_token(raw_token)
    now = datetime.now(UTC)

    res = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.token_hash == token_hash,
            ClientPortalToken.is_active.is_(True),
        )
    )
    portal_token = res.scalar_one_or_none()
    if not portal_token:
        raise HTTPException(status_code=401, detail="Token inválido o revocado")
    if portal_token.expires_at and as_aware(portal_token.expires_at) < now:
        raise HTTPException(status_code=401, detail="El enlace de acceso ha expirado")

    portal_token.last_used_at = now
    await db.commit()

    access_token = create_client_portal_access_token(
        str(portal_token.client_id), str(portal_token.tenant_id)
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ── Autenticado (client_portal JWT) ─────────────────────────────────────────

@router.get("/me", tags=["client-portal"])
@limiter.limit("60/minute")
async def portal_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client_portal),
):
    inv_res = await db.execute(
        select(Invoice)
        .where(Invoice.client_id == client.id, Invoice.tenant_id == client.tenant_id)
        .order_by(Invoice.date.desc())
        .limit(50)
    )
    invoices = inv_res.scalars().all()

    quote_res = await db.execute(
        select(Quote)
        .where(Quote.client_id == client.id, Quote.tenant_id == client.tenant_id)
        .order_by(Quote.date.desc())
        .limit(20)
    )
    quotes = quote_res.scalars().all()

    return {
        "client": {
            "id": str(client.id),
            "name": client.name,
            "email": client.email,
            "nif": client.nif,
            "address": client.address,
            "city": client.city,
        },
        "invoices": [
            {
                "id": str(i.id),
                "invoice_number": i.invoice_number,
                "date": i.date.isoformat() if i.date else None,
                "due_date": i.due_date.isoformat() if i.due_date else None,
                "amount_total": float(i.amount_total or 0),
                "status": i.status,
            }
            for i in invoices
        ],
        "quotes": [
            {
                "id": str(q.id),
                "quote_number": q.quote_number,
                "date": q.date.isoformat() if q.date else None,
                "amount_total": float(q.amount_total or 0),
                "status": q.status,
            }
            for q in quotes
        ],
    }


@router.get("/invoices/{invoice_id}/pdf", tags=["client-portal"])
@limiter.limit("20/minute")
async def portal_download_invoice_pdf(
    request: Request,
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    client: Client = Depends(get_current_client_portal),
):
    # Verify invoice belongs to this client
    res = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client.id,
            Invoice.tenant_id == client.tenant_id,
        )
    )
    if not res.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Factura no encontrada")

    try:
        pdf_bytes, file_name = await invoice_svc.build_invoice_pdf(
            invoice_id, client.tenant_id, db
        )
    except ValueError as e:
        logger.warning("[PORTAL] Error generando PDF factura %s: %s", invoice_id, e)
        raise HTTPException(status_code=404, detail="No se pudo generar el PDF de la factura")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
