"""Regresión de la tanda de seguridad MEDIUM (auditoría 2026-06-25): M1 / M2 / M3.

- M1: el JWT del portal de clientes solo vale si el ClientPortalToken sigue ACTIVO
  (revocar en BD invalida los JWT ya emitidos); TTL reducido a 24 h.
- M2: `frontend_origin()` deriva el origen exacto para usar como targetOrigin de
  postMessage (en vez de '*').
- M3: el import tabular (/documents/import-db) rechaza ficheros que superan el
  límite de tamaño (anti-DoS) sin abortar el resto del lote.
"""

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core import config
from app.core.dependencies import get_current_client_portal
from app.core.security import create_client_portal_access_token
from app.db.models.auth import ClientPortalToken
from app.db.models.crm import Client

# ─── M1: revocación efectiva del JWT del portal ───────────────────────────────


async def _seed_client_with_token(db, tenant_id, *, active: bool) -> Client:
    cli = Client(tenant_id=tenant_id, name="Cliente Portal", nif="B99999999")
    db.add(cli)
    await db.flush()
    db.add(ClientPortalToken(
        tenant_id=tenant_id,
        client_id=cli.id,
        token_hash=("a" if active else "b") * 64,
        is_active=active,
    ))
    await db.commit()
    return cli


async def test_portal_jwt_rechazado_si_token_revocado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client_with_token(db, tenant.id, active=False)
    jwt_tok = create_client_portal_access_token(str(cli.id), str(tenant.id))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_tok)

    with pytest.raises(HTTPException) as ei:
        await get_current_client_portal(credentials=creds, db=db)
    assert ei.value.status_code == 401


async def test_portal_jwt_ok_si_token_activo(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client_with_token(db, tenant.id, active=True)
    jwt_tok = create_client_portal_access_token(str(cli.id), str(tenant.id))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=jwt_tok)

    result = await get_current_client_portal(credentials=creds, db=db)
    assert result.id == cli.id


# ─── M2: origen exacto para postMessage ───────────────────────────────────────


def test_frontend_origin_extrae_origen_del_primero(monkeypatch):
    monkeypatch.setattr(config.settings, "FRONTEND_URL", "https://app.example.com/x,http://otro", raising=False)
    assert config.frontend_origin() == "https://app.example.com"


def test_frontend_origin_localhost(monkeypatch):
    monkeypatch.setattr(config.settings, "FRONTEND_URL", "http://localhost:3000", raising=False)
    assert config.frontend_origin() == "http://localhost:3000"


# ─── M3: límite de tamaño en el import tabular ────────────────────────────────


@pytest.mark.asyncio
async def test_import_db_rechaza_fichero_demasiado_grande(auth_client, monkeypatch):
    from app.api.v1.routes import documents

    monkeypatch.setattr(documents, "_MAX_IMPORT_BYTES", 10, raising=False)
    big = b"col1,col2\n" + b"x" * 200  # supera el límite (10 B) parcheado

    resp = await auth_client.post(
        "/api/v1/documents/import-db",
        files={"files": ("grande.csv", big, "text/csv")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data and "50 MB" in (data[0]["message"] or "")
    assert data[0]["rows_detected"] == 0
