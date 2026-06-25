"""Rutas para gestionar integraciones de cada tenant — thin controller."""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.integrations import EmailConnectRequest, Psd2ConnectRequest
from app.core.config import frontend_origin
from app.core.dependencies import get_current_user, require_role
from app.core.tenant_context import rls_bypass
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.integration import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations", tags=["integrations"])


# ─── General ────────────────────────────────────────────────────────────────


@limiter.limit("10/minute")
@router.get("/")
async def list_integrations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_integrations(current_user.tenant_id, db)


# ─── PSD2 ───────────────────────────────────────────────────────────────────


# SEC.RBAC — conectar/desconectar e iniciar OAuth de integraciones = admin.
# Un usuario normal no debe enlazar/cortar el banco, el email o Google/Microsoft
# del tenant. Las rutas de solo lectura (status/recent/list) siguen abiertas.
@limiter.limit("10/minute")
@router.post("/psd2/connect", status_code=201, dependencies=[Depends(require_role("admin"))])
async def connect_psd2(
    request: Request,
    payload: Psd2ConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.connect_psd2(payload.secret_id, payload.secret_key, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "conectado", "integration": "psd2"}


@limiter.limit("10/minute")
@router.delete("/psd2/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_psd2(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "psd2", db):
        raise HTTPException(status_code=404, detail="Integración con PSD2 no encontrada")
    return {"status": "desconectado"}


# ─── Email (IMAP / SMTP) ───────────────────────────────────────────────────


@limiter.limit("10/minute")
@router.post("/email/connect", status_code=201, dependencies=[Depends(require_role("admin"))])
async def connect_email(
    request: Request,
    payload: EmailConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await svc.connect_email(
            payload.email_address,
            payload.password,
            payload.provider,
            payload.imap_host,
            payload.imap_port,
            payload.smtp_host,
            payload.smtp_port,
            current_user.tenant_id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "conectado", "integration": "email", **result}


@limiter.limit("10/minute")
@router.delete("/email/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "email", db):
        raise HTTPException(status_code=404, detail="Integración de email no encontrada")
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/email/status")
async def email_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.email_status(current_user.tenant_id, db)


# ─── Google OAuth (Gmail + Google Drive) ────────────────────────────────────


@limiter.limit("10/minute")
@router.get("/google/auth-url", dependencies=[Depends(require_role("admin"))])
async def google_auth_url(request: Request, current_user: User = Depends(get_current_user)):
    from app.integrations.google_oauth import generate_auth_url

    url, state, verifier = generate_auth_url(str(current_user.tenant_id))
    svc.set_oauth_state(state, str(current_user.tenant_id), verifier)
    return {"auth_url": url, "state": state}


@limiter.limit("10/minute")
@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    # SEC.RLS: OAuth callback público sin JWT; el tenant se decodifica del
    # `state` (in-memory) DENTRO de handle_oauth_callback, que además hace
    # upsert de la integración. No disponible antes → bypass pre-tenant.
    with rls_bypass():
        tenant_id = await svc.handle_oauth_callback(code, state, "google", db)
    if not tenant_id:
        return HTMLResponse(
            "<html><body><h2>Error: estado OAuth inválido o tokens fallidos</h2></body></html>",
            status_code=400,
        )
    # M2: targetOrigin explícito (no '*') para que solo el frontend reciba el mensaje.
    target = json.dumps(frontend_origin())
    href = json.dumps(frontend_origin() + "/integraciones?connected=google")
    return HTMLResponse(
        "<html><body><script>"
        "if(window.opener){window.opener.postMessage("
        "{type:'oauth_success',provider:'google'}," + target + ");window.close();}"
        "else{window.location.href=" + href + ";}"
        "</script><p>Conectado con Google. Puedes cerrar esta ventana.</p></body></html>"
    )


@limiter.limit("10/minute")
@router.delete("/gmail/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_gmail(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "gmail", db):
        raise HTTPException(status_code=404, detail="Integración de Gmail no encontrada")
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.delete("/gdrive/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_gdrive(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "gdrive", db):
        raise HTTPException(status_code=404, detail="Integración de Google Drive no encontrada")
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/gmail/status")
async def gmail_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_status(current_user.tenant_id, "gmail", db)


@limiter.limit("10/minute")
@router.get("/gmail/recent")
async def gmail_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_recent_messages(current_user.tenant_id, "gmail", db)


@limiter.limit("10/minute")
@router.get("/gdrive/status")
async def gdrive_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_status(current_user.tenant_id, "gdrive", db)


@limiter.limit("10/minute")
@router.get("/gdrive/recent")
async def gdrive_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_recent_files(current_user.tenant_id, "gdrive", db)


# ─── Microsoft OAuth (Outlook + OneDrive) ──────────────────────────────────


@limiter.limit("10/minute")
@router.get("/microsoft/auth-url", dependencies=[Depends(require_role("admin"))])
async def microsoft_auth_url(request: Request, current_user: User = Depends(get_current_user)):
    from app.integrations.microsoft_oauth import generate_auth_url

    url, state = generate_auth_url(str(current_user.tenant_id))
    svc.set_oauth_state(state, str(current_user.tenant_id))
    return {"auth_url": url, "state": state}


@limiter.limit("10/minute")
@router.get("/microsoft/callback", response_class=HTMLResponse)
async def microsoft_callback(
    request: Request,
    code: str,
    state: str,
    db: AsyncSession = Depends(get_db),
):
    # SEC.RLS: OAuth callback público sin JWT; el tenant se decodifica del
    # `state` (in-memory) DENTRO de handle_oauth_callback, que además hace
    # upsert de la integración. No disponible antes → bypass pre-tenant.
    with rls_bypass():
        tenant_id = await svc.handle_oauth_callback(code, state, "microsoft", db)
    if not tenant_id:
        return HTMLResponse(
            "<html><body><h2>Error: estado OAuth inválido o tokens fallidos</h2></body></html>",
            status_code=400,
        )
    # M2: targetOrigin explícito (no '*') para que solo el frontend reciba el mensaje.
    target = json.dumps(frontend_origin())
    href = json.dumps(frontend_origin() + "/integraciones?connected=microsoft")
    return HTMLResponse(
        "<html><body><script>"
        "if(window.opener){window.opener.postMessage("
        "{type:'oauth_success',provider:'microsoft'}," + target + ");window.close();}"
        "else{window.location.href=" + href + ";}"
        "</script><p>Conectado con Microsoft. Puedes cerrar esta ventana.</p></body></html>"
    )


@limiter.limit("10/minute")
@router.delete("/outlook/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_outlook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "outlook", db):
        raise HTTPException(status_code=404, detail="Integración de Outlook no encontrada")
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.delete("/onedrive/disconnect", dependencies=[Depends(require_role("admin"))])
async def disconnect_onedrive(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.disconnect_integration(current_user.tenant_id, "onedrive", db):
        raise HTTPException(status_code=404, detail="Integración de OneDrive no encontrada")
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/outlook/recent")
async def outlook_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_recent_messages(current_user.tenant_id, "outlook", db)


@limiter.limit("10/minute")
@router.get("/onedrive/recent")
async def onedrive_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_recent_files(current_user.tenant_id, "onedrive", db)


@limiter.limit("10/minute")
@router.get("/outlook/status")
async def outlook_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_status(current_user.tenant_id, "outlook", db)


@limiter.limit("10/minute")
@router.get("/onedrive/status")
async def onedrive_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_status(current_user.tenant_id, "onedrive", db)
