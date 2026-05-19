"""Emisión y hashing de tokens del portal de clientes.

Centraliza la lógica criptográfica que antes vivía en la ruta
`POST /client-portal/admin/tokens/{client_id}`. Cualquier otro emisor
(CLI, scheduler de renovación, workflow) DEBE pasar por aquí para
garantizar un solo algoritmo de hash y un solo formato de secreto.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import ClientPortalToken


def hash_token(raw: str) -> str:
    """SHA-256 del secreto en claro. Determinista para lookup en DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


async def issue_token(
    client_id: UUID,
    tenant_id: UUID,
    days_valid: int,
    db: AsyncSession,
) -> tuple[str, ClientPortalToken]:
    """Genera un nuevo token para `client_id` y revoca los activos previos.

    Devuelve `(raw_secret, persisted_obj)`. El llamador (ruta HTTP) usa
    `raw_secret` para construir la URL pública del portal; el secreto NO
    se persiste en claro (solo su hash).
    """
    # Revocar tokens activos previos del mismo cliente/tenant
    existing = await db.execute(
        select(ClientPortalToken).where(
            ClientPortalToken.client_id == client_id,
            ClientPortalToken.tenant_id == tenant_id,
        )
    )
    for old in existing.scalars():
        old.is_active = False

    raw_token = secrets.token_urlsafe(32)
    new_token = ClientPortalToken(
        client_id=client_id,
        tenant_id=tenant_id,
        token_hash=hash_token(raw_token),
        is_active=True,
        expires_at=datetime.now(UTC) + timedelta(days=days_valid),
    )
    db.add(new_token)
    await db.commit()
    await db.refresh(new_token)
    return raw_token, new_token
