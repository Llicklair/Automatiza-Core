"""Rutas para gestionar integraciones de cada tenant (Gmail, etc.)."""
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import TenantIntegration, User
from app.services.encryption import encrypt_credentials, decrypt_credentials

router = APIRouter(prefix="/integrations", tags=["integrations"])

# OAuth state store en memoria con TTL
import time as _time

_oauth_states: dict[str, tuple[str, float]] = {}  # state -> (tenant_id, expires_at)
_OAUTH_STATE_TTL = 600  # 10 minutes


def _set_oauth_state(state: str, tenant_id: str) -> None:
    """Store OAuth state in-memory with TTL."""
    _oauth_states[state] = (tenant_id, _time.time() + _OAUTH_STATE_TTL)


def _pop_oauth_state(state: str) -> str | None:
    """Retrieve and delete OAuth state. Returns tenant_id or None."""
    entry = _oauth_states.pop(state, None)
    if entry and entry[1] > _time.time():
        return entry[0]
    return None


# ─── Schemas ─────────────────────────────────────────────────────────────────

class IntegrationStatusOut(BaseModel):
    integration_type: str
    is_active: bool
    last_sync_at: str | None = None


# ─── Rutas ───────────────────────────────────────────────────────────────────

@limiter.limit("10/minute")
@router.get("/", response_model=list[IntegrationStatusOut])
async def list_integrations(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista todas las integraciones configuradas del tenant."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id
        )
    )
    integrations = result.scalars().all()
    return [
        IntegrationStatusOut(
            integration_type=i.integration_type,
            is_active=i.is_active,
            last_sync_at=i.last_sync_at.isoformat() if i.last_sync_at else None,
        )
        for i in integrations
    ]


class Psd2ConnectRequest(BaseModel):
    secret_id: str
    secret_key: str

@limiter.limit("10/minute")
@router.post("/psd2/connect", status_code=201)
async def connect_psd2(
    request: Request,
    payload: Psd2ConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conecta la cuenta bancaria vía PSD2 (Nordigen) guardando las credenciales cifradas."""
    if not payload.secret_id.strip() or not payload.secret_key.strip():
        raise HTTPException(status_code=400, detail="El secret_id y secret_key no pueden estar vacíos")

    # Verificar que las credenciales funcionan antes de guardar
    from app.integrations.psd2 import NordigenClient
    client = NordigenClient(secret_id=payload.secret_id, secret_key=payload.secret_key)
    try:
        await client._get_access_token()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Las credenciales de Nordigen/GoCardless no son válidas."
        )
    finally:
        await client.close()

    # Cifrar y guardar (upsert)
    encrypted = encrypt_credentials({"secret_id": payload.secret_id, "secret_key": payload.secret_key})

    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "psd2",
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.encrypted_credentials = encrypted
        existing.is_active = True
    else:
        db.add(TenantIntegration(
            tenant_id=current_user.tenant_id,
            integration_type="psd2",
            encrypted_credentials=encrypted,
            is_active=True,
        ))

    await db.commit()
    return {"status": "conectado", "integration": "psd2"}


@limiter.limit("10/minute")
@router.delete("/psd2/disconnect", status_code=200)
async def disconnect_psd2(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desactiva la integración con PSD2."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "psd2",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración con PSD2 no encontrada")

    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


# ─── Email (IMAP / SMTP) ──────────────────────────────────────────────────────

class EmailConnectRequest(BaseModel):
    email_address: str
    password: str
    provider: str = "gmail"        # gmail | outlook | yahoo | custom
    imap_host: str | None = None   # Opcional: se infiere del provider
    imap_port: int | None = None
    smtp_host: str | None = None
    smtp_port: int | None = None


@limiter.limit("10/minute")
@router.post("/email/connect", status_code=201)
async def connect_email(
    request: Request,
    payload: EmailConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Conecta la cuenta de email del tenant via IMAP/SMTP.
    Valida las credenciales IMAP antes de guardarlas cifradas.

    Para Gmail: activa IMAP en la configuración de tu cuenta y genera una
    'Contraseña de aplicación' en Seguridad > 2FA > App passwords.
    """
    import asyncio
    from app.services.email_service import PROVIDER_PRESETS, EmailCredentials, test_imap_connection

    if not payload.email_address.strip() or not payload.password.strip():
        raise HTTPException(status_code=400, detail="El email y la contraseña no pueden estar vacíos")

    preset = PROVIDER_PRESETS.get(payload.provider, PROVIDER_PRESETS["gmail"])
    creds = EmailCredentials(
        email_address=payload.email_address,
        password=payload.password,
        imap_host=payload.imap_host or preset["imap_host"],
        imap_port=payload.imap_port or preset["imap_port"],
        smtp_host=payload.smtp_host or preset["smtp_host"],
        smtp_port=payload.smtp_port or preset["smtp_port"],
        provider=payload.provider,
    )

    # Verificar conexión IMAP antes de guardar
    is_valid = await asyncio.to_thread(test_imap_connection, creds)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No se pudo conectar con {creds.imap_host}. "
                "Verifica el email, la contraseña de aplicación y que IMAP esté habilitado."
            ),
        )

    encrypted = encrypt_credentials({
        "email_address": creds.email_address,
        "password": creds.password,
        "provider": creds.provider,
        "imap_host": creds.imap_host,
        "imap_port": creds.imap_port,
        "smtp_host": creds.smtp_host,
        "smtp_port": creds.smtp_port,
    })

    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "email",
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.encrypted_credentials = encrypted
        existing.is_active = True
    else:
        db.add(TenantIntegration(
            tenant_id=current_user.tenant_id,
            integration_type="email",
            encrypted_credentials=encrypted,
            is_active=True,
        ))

    await db.commit()
    return {"status": "conectado", "integration": "email", "provider": payload.provider, "email": payload.email_address}


@limiter.limit("10/minute")
@router.delete("/email/disconnect", status_code=200)
async def disconnect_email(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desactiva la integración de email del tenant."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "email",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de email no encontrada")

    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/email/status")
async def email_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el estado de la integración de email y la cuenta configurada."""
    from app.services.encryption import decrypt_credentials

    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "email",
        )
    )
    integration = result.scalar_one_or_none()

    if not integration or not integration.is_active:
        return {"connected": False, "email": None, "provider": None}

    try:
        creds = decrypt_credentials(integration.encrypted_credentials)
        return {
            "connected": True,
            "email": creds.get("email_address"),
            "provider": creds.get("provider", "gmail"),
        }
    except Exception:
        return {"connected": False, "email": None, "provider": None}


# ─── Google OAuth (Gmail + Google Drive) ──────────────────────────────────────

@limiter.limit("10/minute")
@router.get("/google/auth-url")
async def google_auth_url(request: Request, current_user: User = Depends(get_current_user)):
    """Generate Google OAuth consent URL."""
    from app.integrations.google_oauth import generate_auth_url
    url, state = generate_auth_url(str(current_user.tenant_id))
    _set_oauth_state(state, str(current_user.tenant_id))
    return {"auth_url": url, "state": state}


@limiter.limit("10/minute")
@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(request: Request,
                          code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback — exchanges code for tokens and stores them."""
    from app.integrations.google_oauth import exchange_code

    tenant_id = _pop_oauth_state(state)

    if not tenant_id:
        return HTMLResponse("<html><body><h2>Error: estado OAuth inválido</h2></body></html>", status_code=400)

    try:
        tokens = await exchange_code(code)
    except Exception:
        return HTMLResponse("<html><body><h2>Error al obtener tokens de Google</h2></body></html>", status_code=400)

    encrypted = encrypt_credentials({
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_in": tokens.get("expires_in"),
    })

    # Save/update gmail + gdrive integrations
    for itype in ("gmail", "gdrive"):
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == itype,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.encrypted_credentials = encrypted
            existing.is_active = True
        else:
            db.add(TenantIntegration(
                tenant_id=tenant_id,
                integration_type=itype,
                encrypted_credentials=encrypted,
                is_active=True,
            ))

    await db.commit()

    return HTMLResponse("""
    <html><body>
    <script>
        if (window.opener) { window.opener.postMessage({type:'oauth_success',provider:'google'}, '*'); window.close(); }
        else { window.location.href = 'http://localhost:3000/integraciones?connected=google'; }
    </script>
    <p>Conectado con Google. Puedes cerrar esta ventana.</p>
    </body></html>
    """)


@limiter.limit("10/minute")
@router.delete("/gmail/disconnect", status_code=200)
async def disconnect_gmail(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Gmail integration."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "gmail",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de Gmail no encontrada")
    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.delete("/gdrive/disconnect", status_code=200)
async def disconnect_gdrive(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Google Drive integration."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "gdrive",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de Google Drive no encontrada")
    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/gmail/status")
async def gmail_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Gmail connection status."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "gmail",
        )
    )
    integration = result.scalar_one_or_none()
    return {"connected": bool(integration and integration.is_active)}


async def _get_oauth_access_token(
    db: AsyncSession, tenant_id, integration_type: str = "gmail",
) -> str | None:
    """Load and auto-refresh OAuth access token for a tenant (Google or Microsoft)."""
    integration = (
        await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == integration_type,
                TenantIntegration.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not integration:
        logger.warning("No active integration found for type=%s", integration_type)
        return None

    creds = decrypt_credentials(integration.encrypted_credentials)
    access_token = creds.get("access_token")
    refresh_token = creds.get("refresh_token")
    if not access_token:
        logger.warning("No access_token in credentials for type=%s", integration_type)
        return None

    # Test token validity with the appropriate API
    is_microsoft = integration_type in ("outlook", "onedrive")
    test_url = (
        "https://graph.microsoft.com/v1.0/me" if is_microsoft
        else "https://gmail.googleapis.com/gmail/v1/users/me/profile"
    )

    import httpx
    async with httpx.AsyncClient() as client:
        test = await client.get(test_url, headers={"Authorization": f"Bearer {access_token}"})

    logger.info("Token test for %s: status=%d", integration_type, test.status_code)

    if test.status_code == 401 and refresh_token:
        if is_microsoft:
            from app.integrations.microsoft_oauth import refresh_access_token
        else:
            from app.integrations.google_oauth import refresh_access_token
        new_tokens = await refresh_access_token(refresh_token)
        access_token = new_tokens["access_token"]
        creds["access_token"] = access_token
        if "refresh_token" in new_tokens:
            creds["refresh_token"] = new_tokens["refresh_token"]
        integration.encrypted_credentials = encrypt_credentials(creds)
        await db.commit()

    return access_token


@limiter.limit("10/minute")
@router.get("/gmail/recent")
async def gmail_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get last 5 Gmail messages for the dashboard widget."""
    token = await _get_oauth_access_token(db, current_user.tenant_id, "gmail")
    if not token:
        return []
    from app.integrations.gmail_client import GmailClient
    client = GmailClient(token)
    try:
        return await client.list_messages(max_results=5)
    except Exception:
        return []
    finally:
        await client.close()


@limiter.limit("10/minute")
@router.get("/gdrive/recent")
async def gdrive_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get last 5 Google Drive files for the dashboard widget."""
    token = await _get_oauth_access_token(db, current_user.tenant_id, "gdrive")
    if not token:
        return []
    from app.integrations.google_drive_client import GoogleDriveClient
    client = GoogleDriveClient(token)
    try:
        files = await client.list_files(page_size=5)
        logger.info("gdrive/recent returned %d files", len(files))
        return files
    except Exception as e:
        logger.exception("gdrive/recent error: %s", e)
        return []
    finally:
        await client.close()


@limiter.limit("10/minute")
@router.get("/gdrive/status")
async def gdrive_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Google Drive connection status."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "gdrive",
        )
    )
    integration = result.scalar_one_or_none()
    return {"connected": bool(integration and integration.is_active)}


# ─── Microsoft OAuth (Outlook + OneDrive) ────────────────────────────────────

@limiter.limit("10/minute")
@router.get("/microsoft/auth-url")
async def microsoft_auth_url(request: Request, current_user: User = Depends(get_current_user)):
    """Generate Microsoft OAuth consent URL."""
    from app.integrations.microsoft_oauth import generate_auth_url
    url, state = generate_auth_url(str(current_user.tenant_id))
    _set_oauth_state(state, str(current_user.tenant_id))
    return {"auth_url": url, "state": state}


@limiter.limit("10/minute")
@router.get("/microsoft/callback", response_class=HTMLResponse)
async def microsoft_callback(request: Request,
                             code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Microsoft OAuth callback — exchanges code for tokens and stores them."""
    from app.integrations.microsoft_oauth import exchange_code

    tenant_id = _pop_oauth_state(state)

    if not tenant_id:
        return HTMLResponse("<html><body><h2>Error: estado OAuth inválido</h2></body></html>", status_code=400)

    try:
        tokens = await exchange_code(code)
    except Exception:
        return HTMLResponse("<html><body><h2>Error al obtener tokens de Microsoft</h2></body></html>", status_code=400)

    encrypted = encrypt_credentials({
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "Bearer"),
        "expires_in": tokens.get("expires_in"),
    })

    for itype in ("outlook", "onedrive"):
        result = await db.execute(
            select(TenantIntegration).where(
                TenantIntegration.tenant_id == tenant_id,
                TenantIntegration.integration_type == itype,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.encrypted_credentials = encrypted
            existing.is_active = True
        else:
            db.add(TenantIntegration(
                tenant_id=tenant_id,
                integration_type=itype,
                encrypted_credentials=encrypted,
                is_active=True,
            ))

    await db.commit()

    return HTMLResponse("""
    <html><body>
    <script>
        if (window.opener) { window.opener.postMessage({type:'oauth_success',provider:'microsoft'}, '*'); window.close(); }
        else { window.location.href = 'http://localhost:3000/integraciones?connected=microsoft'; }
    </script>
    <p>Conectado con Microsoft. Puedes cerrar esta ventana.</p>
    </body></html>
    """)


@limiter.limit("10/minute")
@router.delete("/outlook/disconnect", status_code=200)
async def disconnect_outlook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect Outlook integration."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "outlook",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de Outlook no encontrada")
    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.delete("/onedrive/disconnect", status_code=200)
async def disconnect_onedrive(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect OneDrive integration."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "onedrive",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración de OneDrive no encontrada")
    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


@limiter.limit("10/minute")
@router.get("/outlook/recent")
async def outlook_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get last 5 Outlook messages for the dashboard widget."""
    token = await _get_oauth_access_token(db, current_user.tenant_id, "outlook")
    if not token:
        return []
    from app.integrations.outlook_client import OutlookClient
    client = OutlookClient(token)
    try:
        return await client.list_messages(top=5)
    except Exception:
        return []
    finally:
        await client.close()


@limiter.limit("10/minute")
@router.get("/onedrive/recent")
async def onedrive_recent(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get last 5 OneDrive files for the dashboard widget."""
    token = await _get_oauth_access_token(db, current_user.tenant_id, "onedrive")
    if not token:
        return []
    from app.integrations.onedrive_client import OneDriveClient
    client = OneDriveClient(token)
    try:
        files = await client.list_files(top=5)
        logger.info("onedrive/recent returned %d files", len(files))
        return files
    except Exception as e:
        logger.exception("onedrive/recent error: %s", e)
        return []
    finally:
        await client.close()


@limiter.limit("10/minute")
@router.get("/outlook/status")
async def outlook_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get Outlook connection status."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "outlook",
        )
    )
    integration = result.scalar_one_or_none()
    return {"connected": bool(integration and integration.is_active)}


@limiter.limit("10/minute")
@router.get("/onedrive/status")
async def onedrive_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get OneDrive connection status."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "onedrive",
        )
    )
    integration = result.scalar_one_or_none()
    return {"connected": bool(integration and integration.is_active)}
