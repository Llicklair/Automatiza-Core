"""Credenciales de email del tenant (SMTP/IMAP y OAuth gmail/outlook).

Lógica reutilizable extraída de `agents/email/tools.py` para respetar el límite de
capas: las rutas (`api/v1/routes/messaging.py`) y otros agentes consumen estas
funciones desde aquí, sin importar internals privados de un agente.
"""

import logging
import uuid

import httpx
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantIntegration
from app.services.email.service import credentials_from_dict
from app.services.encryption import decrypt_credentials, encrypt_credentials

logger = logging.getLogger(__name__)


async def get_email_credentials(tenant_id: str):
    """
    Carga las credenciales de email del tenant desde la BD.
    Devuelve EmailCredentials si están configuradas, None si no.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                    TenantIntegration.integration_type == "email",
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = result.scalar_one_or_none()

        if not integration:
            return None

        creds_dict = decrypt_credentials(integration.encrypted_credentials)
        return credentials_from_dict(creds_dict)
    except Exception as e:
        logger.error("Error cargando credenciales de email para tenant %s: %s", tenant_id, e)
        return None


async def get_oauth_token(tenant_id: str, integration_type: str) -> str | None:
    """
    Carga el access_token OAuth del tenant para el tipo dado (gmail/outlook).
    Si el token ha expirado, intenta refrescarlo automáticamente.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                    TenantIntegration.integration_type == integration_type,
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = result.scalar_one_or_none()

            if not integration:
                return None

            try:
                creds = decrypt_credentials(integration.encrypted_credentials)
            except Exception as dec_exc:
                # La encryption key cambió desde que se guardaron los tokens:
                # los datos son irrecuperables. Marcar la integración como
                # inactive para forzar reconexión vía /integrations/google/auth-url
                # y evitar que cada llamada al email agent vuelva a fallar igual.
                integration.is_active = False
                await db.commit()
                logger.error(
                    "[OAUTH] Credenciales %s del tenant %s no se pueden desencriptar "
                    "(la encryption key cambió). Marcada inactive. El usuario debe "
                    "reconectar en /integrations/google/auth-url. Error: %s: %s",
                    integration_type, tenant_id, type(dec_exc).__name__, dec_exc,
                )
                return None
            access_token = creds.get("access_token")
            refresh_token = creds.get("refresh_token")

            if not access_token:
                return None

            # Test token validity
            is_microsoft = integration_type == "outlook"
            test_url = (
                "https://graph.microsoft.com/v1.0/me"
                if is_microsoft
                else "https://gmail.googleapis.com/gmail/v1/users/me/profile"
            )

            async with httpx.AsyncClient() as client:
                test = await client.get(
                    test_url, headers={"Authorization": f"Bearer {access_token}"}
                )

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
    except Exception as e:
        logger.error(
            "Error obteniendo token OAuth (%s) para tenant %s: %s", integration_type, tenant_id, e
        )
        return None
