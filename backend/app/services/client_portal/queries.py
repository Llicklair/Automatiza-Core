"""Portal de clientes — consultas y operaciones de negocio.

Centraliza la lógica de DB que antes vivía en las rutas HTTP de
`api/v1/routes/client_portal.py`. La capa HTTP delega aquí y mapea
los valores de retorno a HTTPException / Response.

SEGURIDAD: ninguna función de este módulo debilita ni reordena los
guards de token/ownership — se trasladaron byte-a-byte desde las rutas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import as_aware
from app.db.models.auth import ClientPortalToken
from app.db.models.billing import Invoice, Quote
from app.db.models.crm import Client

# ── Admin: estado / revocación de tokens ─────────────────────────────────────


async def get_portal_token_status(
    client_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> dict:
    """Devuelve metadatos del token activo del cliente, o indicadores de ausencia."""
    row = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.client_id == client_id,
            ClientPortalToken.tenant_id == tenant_id,
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


async def revoke_portal_tokens(
    client_id: UUID,
    tenant_id: UUID,
    db: AsyncSession,
) -> None:
    """Desactiva todos los tokens del cliente en el tenant."""
    existing = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.client_id == client_id,
            ClientPortalToken.tenant_id == tenant_id,
        )
    )
    for t in existing.scalars():
        t.is_active = False
    await db.commit()


# ── Público: autenticación por token ─────────────────────────────────────────


class PortalAuthError(Exception):
    """Error de autenticación del portal con código HTTP y detalle."""

    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


async def authenticate_and_stamp(
    token_hash: str,
    db: AsyncSession,
) -> ClientPortalToken:
    """Verifica el hash, comprueba caducidad, registra last_used_at y hace commit.

    Lanza `PortalAuthError` si el token no es válido o ha expirado.
    El llamador (ruta HTTP) convierte PortalAuthError en HTTPException.

    NOTA DE SEGURIDAD: el orden de las comprobaciones (existencia → expiración →
    stamp) es idéntico al que había en la ruta original.
    """
    now = datetime.now(UTC)

    res = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.token_hash == token_hash,
            ClientPortalToken.is_active.is_(True),
        )
    )
    portal_token = res.scalar_one_or_none()
    if not portal_token:
        raise PortalAuthError(status_code=401, detail="Token inválido o revocado")
    if portal_token.expires_at and as_aware(portal_token.expires_at) < now:
        raise PortalAuthError(status_code=401, detail="El enlace de acceso ha expirado")

    portal_token.last_used_at = now
    await db.commit()

    return portal_token


# ── Autenticado: datos del portal ────────────────────────────────────────────


async def get_portal_me(
    client: Client,
    db: AsyncSession,
) -> dict:
    """Devuelve datos del cliente con sus facturas y presupuestos recientes."""
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


async def get_invoice_for_client(
    invoice_id: UUID,
    client: Client,
    db: AsyncSession,
) -> Invoice | None:
    """Devuelve la factura si pertenece al cliente/tenant, o None.

    El llamador (ruta HTTP) lanza 404 si el resultado es None.
    """
    res = await db.execute(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.client_id == client.id,
            Invoice.tenant_id == client.tenant_id,
        )
    )
    return res.scalar_one_or_none()
