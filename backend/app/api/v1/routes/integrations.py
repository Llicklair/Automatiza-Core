"""Rutas para gestionar integraciones de cada tenant (Holded, Gmail, etc.)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import TenantIntegration, User
from app.services.encryption import encrypt_credentials, decrypt_credentials

router = APIRouter(prefix="/integrations", tags=["integrations"])

# In-memory state store for OAuth flows (production: use Redis)
_oauth_states: dict[str, str] = {}


# ─── Schemas ─────────────────────────────────────────────────────────────────

class HoldedConnectRequest(BaseModel):
    api_key: str


class IntegrationStatusOut(BaseModel):
    integration_type: str
    is_active: bool
    last_sync_at: str | None = None


# ─── Rutas ───────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[IntegrationStatusOut])
async def list_integrations(
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


@router.post("/holded/connect", status_code=201)
async def connect_holded(
    payload: HoldedConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conecta la cuenta de Holded del tenant guardando la API key cifrada."""
    if not payload.api_key.strip():
        raise HTTPException(status_code=400, detail="La API key no puede estar vacía")

    # Verificar que la API key funciona antes de guardar
    from app.integrations.holded import HoldedClient
    client = HoldedClient(api_key=payload.api_key)
    try:
        await client.get_contacts(page=1)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="La API key de Holded no es válida o no tiene permisos. Verifica en tu cuenta de Holded."
        )
    finally:
        await client.close()

    # Cifrar y guardar (upsert)
    encrypted = encrypt_credentials({"api_key": payload.api_key})

    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "holded",
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.encrypted_credentials = encrypted
        existing.is_active = True
    else:
        db.add(TenantIntegration(
            tenant_id=current_user.tenant_id,
            integration_type="holded",
            encrypted_credentials=encrypted,
            is_active=True,
        ))

    await db.commit()
    return {"status": "conectado", "integration": "holded"}


@router.delete("/holded/disconnect", status_code=200)
async def disconnect_holded(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desactiva la integración con Holded (no borra las credenciales)."""
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == current_user.tenant_id,
            TenantIntegration.integration_type == "holded",
        )
    )
    integration = result.scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=404, detail="Integración con Holded no encontrada")

    integration.is_active = False
    await db.commit()
    return {"status": "desconectado"}


class Psd2ConnectRequest(BaseModel):
    secret_id: str
    secret_key: str

@router.post("/psd2/connect", status_code=201)
async def connect_psd2(
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


@router.delete("/psd2/disconnect", status_code=200)
async def disconnect_psd2(
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


@router.post("/email/connect", status_code=201)
async def connect_email(
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


@router.delete("/email/disconnect", status_code=200)
async def disconnect_email(
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


@router.get("/email/status")
async def email_status(
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

@router.get("/google/auth-url")
async def google_auth_url(current_user: User = Depends(get_current_user)):
    """Generate Google OAuth consent URL."""
    from app.integrations.google_oauth import generate_auth_url
    url, state = generate_auth_url(str(current_user.tenant_id))
    _oauth_states[state] = str(current_user.tenant_id)
    return {"auth_url": url, "state": state}


@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback — exchanges code for tokens and stores them."""
    from app.integrations.google_oauth import exchange_code

    tenant_id = _oauth_states.pop(state, None)
    if not tenant_id and ":" in state:
        tenant_id = state.split(":")[0]

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
        else { window.location.href = '/integraciones?connected=google'; }
    </script>
    <p>Conectado con Google. Puedes cerrar esta ventana.</p>
    </body></html>
    """)


@router.delete("/gmail/disconnect", status_code=200)
async def disconnect_gmail(
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


@router.delete("/gdrive/disconnect", status_code=200)
async def disconnect_gdrive(
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


@router.get("/gmail/status")
async def gmail_status(
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


@router.get("/gdrive/status")
async def gdrive_status(
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

@router.get("/microsoft/auth-url")
async def microsoft_auth_url(current_user: User = Depends(get_current_user)):
    """Generate Microsoft OAuth consent URL."""
    from app.integrations.microsoft_oauth import generate_auth_url
    url, state = generate_auth_url(str(current_user.tenant_id))
    _oauth_states[state] = str(current_user.tenant_id)
    return {"auth_url": url, "state": state}


@router.get("/microsoft/callback", response_class=HTMLResponse)
async def microsoft_callback(code: str, state: str, db: AsyncSession = Depends(get_db)):
    """Handle Microsoft OAuth callback — exchanges code for tokens and stores them."""
    from app.integrations.microsoft_oauth import exchange_code

    tenant_id = _oauth_states.pop(state, None)
    if not tenant_id and ":" in state:
        tenant_id = state.split(":")[0]

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
        else { window.location.href = '/integraciones?connected=microsoft'; }
    </script>
    <p>Conectado con Microsoft. Puedes cerrar esta ventana.</p>
    </body></html>
    """)


@router.delete("/outlook/disconnect", status_code=200)
async def disconnect_outlook(
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


@router.delete("/onedrive/disconnect", status_code=200)
async def disconnect_onedrive(
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


@router.get("/outlook/status")
async def outlook_status(
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


@router.get("/onedrive/status")
async def onedrive_status(
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
