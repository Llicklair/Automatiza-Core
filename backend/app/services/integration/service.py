"""Servicio de dominio para integraciones de terceros.

Encapsula: connect/disconnect/status de PSD2, Email, Google OAuth, Microsoft OAuth.
Gestión de OAuth state y token refresh.
"""

import logging
import time as _time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import TenantIntegration
from app.services.encryption import decrypt_credentials, encrypt_credentials

logger = logging.getLogger(__name__)

# OAuth state store en memoria con TTL. Guarda también el code_verifier PKCE
# (Google) para reenviarlo en el callback; None para flujos sin PKCE (Microsoft).
_oauth_states: dict[str, tuple[str, float, str | None]] = {}
_OAUTH_STATE_TTL = 600


def set_oauth_state(state: str, tenant_id: str, code_verifier: str | None = None) -> None:
    _oauth_states[state] = (tenant_id, _time.time() + _OAUTH_STATE_TTL, code_verifier)


def pop_oauth_state(state: str) -> tuple[str, str | None] | None:
    """Devuelve (tenant_id, code_verifier) o None si no existe o expiró."""
    entry = _oauth_states.pop(state, None)
    if entry and entry[1] > _time.time():
        return entry[0], entry[2]
    return None


# ── Generic helpers ──────────────────────────────────────────────────────────


async def get_integration(
    tenant_id,
    integration_type: str,
    db: AsyncSession,
) -> TenantIntegration | None:
    result = await db.execute(
        select(TenantIntegration).where(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_type == integration_type,
        )
    )
    return result.scalar_one_or_none()


async def list_integrations(tenant_id, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(TenantIntegration).where(TenantIntegration.tenant_id == tenant_id)
    )
    return [
        {
            "integration_type": i.integration_type,
            "is_active": i.is_active,
            "last_sync_at": i.last_sync_at.isoformat() if i.last_sync_at else None,
        }
        for i in result.scalars().all()
    ]


async def upsert_integration(
    tenant_id,
    integration_type: str,
    encrypted_creds: str,
    db: AsyncSession,
) -> None:
    """Crea o actualiza una integración con credenciales cifradas."""
    existing = await get_integration(tenant_id, integration_type, db)
    if existing:
        existing.encrypted_credentials = encrypted_creds
        existing.is_active = True
    else:
        db.add(
            TenantIntegration(
                tenant_id=tenant_id,
                integration_type=integration_type,
                encrypted_credentials=encrypted_creds,
                is_active=True,
            )
        )


async def disconnect_integration(
    tenant_id,
    integration_type: str,
    db: AsyncSession,
) -> bool:
    """Desactiva una integración. Retorna False si no existe."""
    integration = await get_integration(tenant_id, integration_type, db)
    if not integration:
        return False
    integration.is_active = False
    await db.commit()
    return True


async def get_status(tenant_id, integration_type: str, db: AsyncSession) -> dict:
    integration = await get_integration(tenant_id, integration_type, db)
    return {"connected": bool(integration and integration.is_active)}


# ── PSD2 ─────────────────────────────────────────────────────────────────────


async def connect_psd2(secret_id: str, secret_key: str, tenant_id, db: AsyncSession) -> None:
    """Conecta PSD2. Lanza ValueError si credenciales inválidas."""
    if not secret_id.strip() or not secret_key.strip():
        raise ValueError("El secret_id y secret_key no pueden estar vacíos")

    from app.integrations.psd2 import NordigenClient

    client = NordigenClient(secret_id=secret_id, secret_key=secret_key)
    try:
        await client._get_access_token()
    except Exception:
        raise ValueError("Las credenciales de Nordigen/GoCardless no son válidas.")
    finally:
        await client.close()

    encrypted = encrypt_credentials({"secret_id": secret_id, "secret_key": secret_key})
    await upsert_integration(tenant_id, "psd2", encrypted, db)
    await db.commit()


# ── Email (IMAP/SMTP) ───────────────────────────────────────────────────────


async def connect_email(
    email_address: str,
    password: str,
    provider: str,
    imap_host: str | None,
    imap_port: int | None,
    smtp_host: str | None,
    smtp_port: int | None,
    tenant_id,
    db: AsyncSession,
) -> dict:
    """Conecta email via IMAP/SMTP. Lanza ValueError si falla."""
    import asyncio

    from app.services.email.service import PROVIDER_PRESETS, EmailCredentials, test_imap_connection

    if not email_address.strip() or not password.strip():
        raise ValueError("El email y la contraseña no pueden estar vacíos")

    preset = PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["gmail"])
    creds = EmailCredentials(
        email_address=email_address,
        password=password,
        imap_host=imap_host or preset["imap_host"],
        imap_port=imap_port or preset["imap_port"],
        smtp_host=smtp_host or preset["smtp_host"],
        smtp_port=smtp_port or preset["smtp_port"],
        provider=provider,
    )

    is_valid = await asyncio.to_thread(test_imap_connection, creds)
    if not is_valid:
        raise ValueError(
            f"No se pudo conectar con {creds.imap_host}. "
            "Verifica el email, la contraseña de aplicación y que IMAP esté habilitado."
        )

    encrypted = encrypt_credentials(
        {
            "email_address": creds.email_address,
            "password": creds.password,
            "provider": creds.provider,
            "imap_host": creds.imap_host,
            "imap_port": creds.imap_port,
            "smtp_host": creds.smtp_host,
            "smtp_port": creds.smtp_port,
        }
    )
    await upsert_integration(tenant_id, "email", encrypted, db)
    await db.commit()
    return {"provider": provider, "email": email_address}


async def email_status(tenant_id, db: AsyncSession) -> dict:
    integration = await get_integration(tenant_id, "email", db)
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


# ── OAuth (Google / Microsoft) ───────────────────────────────────────────────


async def handle_oauth_callback(
    code: str,
    state: str,
    provider: str,
    db: AsyncSession,
) -> str | None:
    """Procesa OAuth callback. Retorna tenant_id o None si state inválido."""
    popped = pop_oauth_state(state)
    if not popped:
        return None
    tenant_id, code_verifier = popped

    if provider == "google":
        from app.integrations.google_oauth import exchange_code

        integration_types = ("gmail", "gdrive")
    else:
        from app.integrations.microsoft_oauth import exchange_code

        integration_types = ("outlook", "onedrive")

    try:
        # Google usa PKCE → reenvía el verifier; Microsoft no lo acepta.
        if provider == "google":
            tokens = await exchange_code(code, code_verifier)
        else:
            tokens = await exchange_code(code)
    except Exception:
        logger.exception("OAuth token exchange failed for provider=%s", provider)
        return None
    encrypted = encrypt_credentials(
        {
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            "token_type": tokens.get("token_type", "Bearer"),
            "expires_in": tokens.get("expires_in"),
        }
    )

    for itype in integration_types:
        await upsert_integration(tenant_id, itype, encrypted, db)
    await db.commit()
    return tenant_id


async def get_oauth_access_token(
    db: AsyncSession,
    tenant_id,
    integration_type: str = "gmail",
) -> str | None:
    """Carga y auto-refresca OAuth access token para un tenant."""
    integration = await get_integration(tenant_id, integration_type, db)
    if not integration or not integration.is_active:
        logger.warning("No active integration found for type=%s", integration_type)
        return None

    creds = decrypt_credentials(integration.encrypted_credentials)
    access_token = creds.get("access_token")
    refresh_token = creds.get("refresh_token")
    if not access_token:
        logger.warning("No access_token in credentials for type=%s", integration_type)
        return None

    is_microsoft = integration_type in ("outlook", "onedrive")
    test_url = (
        "https://graph.microsoft.com/v1.0/me"
        if is_microsoft
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


async def get_recent_messages(
    tenant_id,
    integration_type: str,
    db: AsyncSession,
) -> list:
    """Obtiene mensajes recientes de Gmail u Outlook."""
    token = await get_oauth_access_token(db, tenant_id, integration_type)
    if not token:
        return []

    if integration_type == "outlook":
        from app.integrations.outlook_client import OutlookClient

        client = OutlookClient(token)
        try:
            return await client.list_messages(top=5)
        except Exception:
            return []
        finally:
            await client.close()
    else:
        from app.integrations.gmail_client import GmailClient

        client = GmailClient(token)
        try:
            return await client.list_messages(max_results=5)
        except Exception:
            return []
        finally:
            await client.close()


async def get_recent_files(
    tenant_id,
    integration_type: str,
    db: AsyncSession,
) -> list:
    """Obtiene archivos recientes de Google Drive u OneDrive.

    Si la integración no está conectada o el token caducó (el refresh del
    proveedor devuelve 4xx), se trata como "no conectado": se devuelve lista
    vacía en vez de propagar un 500 con el error del proveedor. El estado real
    de conexión lo reporta el endpoint `/status`.
    """
    try:
        token = await get_oauth_access_token(db, tenant_id, integration_type)
    except Exception as e:
        logger.warning(
            "%s/recent: no se pudo refrescar el token (¿reconectar la integración?): %s",
            integration_type,
            e,
        )
        return []
    if not token:
        return []

    if integration_type == "onedrive":
        from app.integrations.onedrive_client import OneDriveClient

        client = OneDriveClient(token)
    else:
        from app.integrations.google_drive_client import GoogleDriveClient

        client = GoogleDriveClient(token)

    try:
        files = (
            await client.list_files(top=5)
            if integration_type == "onedrive"
            else await client.list_files(page_size=5)
        )
        logger.info("%s/recent returned %d files", integration_type, len(files))
        return files
    except Exception as e:
        logger.exception("%s/recent error: %s", integration_type, e)
        return []
    finally:
        await client.close()
