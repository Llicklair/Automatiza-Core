"""Repro del HALLAZGO A: get_current_client_portal no comprobaba expires_at.

Bug: la validación por-request del ClientPortalToken en
`app.core.dependencies.get_current_client_portal` filtraba solo `is_active=True`
y NO comprobaba `expires_at`. La ruta `/auth` (authenticate_portal) sí comprueba
`expires_at` antes de emitir el JWT, pero las peticiones posteriores que usan el
JWT ya emitido pasaban por `get_current_client_portal`, que no lo comprobaba.

No existe ningún job ni middleware que ponga `is_active=False` al llegar
`expires_at`, así que un token CADUCADO pero NO revocado (is_active sigue True)
superaba el guard mientras el JWT derivado siguiera dentro de su propio TTL.

Estos tests codifican el comportamiento correcto tras el arreglo:
- token activo + expirado  -> 401 (antes pasaba: BUG)
- token activo + futuro    -> OK
- token activo + sin expiry (NULL) -> OK (nunca caduca)

Replica el patrón de tests/test_security_hardening_medium.py (M1).
"""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_client_portal
from app.core.security import create_client_portal_access_token
from app.db.models.auth import ClientPortalToken
from app.db.models.crm import Client


async def _seed_client_with_token(
    db,
    tenant_id,
    *,
    active: bool,
    expires_at: datetime | None,
    token_hash: str,
) -> Client:
    cli = Client(tenant_id=tenant_id, name="Cliente Portal", nif="B99999999")
    db.add(cli)
    await db.flush()
    db.add(
        ClientPortalToken(
            tenant_id=tenant_id,
            client_id=cli.id,
            token_hash=token_hash,
            is_active=active,
            expires_at=expires_at,
        )
    )
    await db.commit()
    return cli


async def test_portal_jwt_rechazado_si_token_activo_pero_caducado(db, seed_tenant_and_user):
    """BUG A: token con is_active=True pero expires_at en el pasado -> debe ser 401."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client_with_token(
        db,
        tenant.id,
        active=True,
        expires_at=datetime(2000, 1, 1, tzinfo=UTC),  # caducado hace años
        token_hash="c" * 64,
    )
    jwt_tok = create_client_portal_access_token(str(cli.id), str(tenant.id))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_tok)

    with pytest.raises(HTTPException) as ei:
        await get_current_client_portal(credentials=creds, db=db)
    assert ei.value.status_code == 401


async def test_portal_jwt_ok_si_token_activo_y_no_caducado(db, seed_tenant_and_user):
    """Token activo con expires_at en el futuro -> sigue siendo válido."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client_with_token(
        db,
        tenant.id,
        active=True,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        token_hash="d" * 64,
    )
    jwt_tok = create_client_portal_access_token(str(cli.id), str(tenant.id))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_tok)

    result = await get_current_client_portal(credentials=creds, db=db)
    assert result.id == cli.id


async def test_portal_jwt_ok_si_token_activo_y_sin_expiry(db, seed_tenant_and_user):
    """expires_at NULL = sin caducidad: el guard de expiry no debe bloquearlo."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client_with_token(
        db,
        tenant.id,
        active=True,
        expires_at=None,
        token_hash="e" * 64,
    )
    jwt_tok = create_client_portal_access_token(str(cli.id), str(tenant.id))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_tok)

    result = await get_current_client_portal(credentials=creds, db=db)
    assert result.id == cli.id
