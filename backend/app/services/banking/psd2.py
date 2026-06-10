"""Credenciales PSD2 del tenant (TenantIntegration cifrada).

Service reutilizable: lo consumen el agente banking y cualquier capa que
necesite operar contra la API PSD2 sin importar internals del agente.
"""

import logging
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantIntegration
from app.services.encryption import decrypt_credentials

logger = logging.getLogger(__name__)


async def get_psd2_credentials(tenant_id: str) -> dict | None:
    """Obtiene credenciales PSD2 del tenant si están configuradas."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(TenantIntegration).where(
                    TenantIntegration.tenant_id == uuid.UUID(tenant_id),
                    TenantIntegration.integration_type == "psd2",
                    TenantIntegration.is_active.is_(True),
                )
            )
            integration = result.scalars().first()
            if not integration:
                return None
            creds = decrypt_credentials(integration.encrypted_credentials)
            if not creds.get("secret_id") or not creds.get("secret_key"):
                return None
            return creds
    except Exception as e:
        logger.error("Error obteniendo credenciales PSD2 para tenant %s: %s", tenant_id, e)
        return None
