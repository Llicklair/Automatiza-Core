"""Banking agent — PSD2 credential helpers and demo data."""

import logging
import uuid

from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.models import TenantIntegration
from app.services.encryption import decrypt_credentials

logger = logging.getLogger(__name__)

ALERT_THRESHOLDS = {
    "cargo_inusual_eur": 5_000,
    "saldo_minimo_eur": 1_000,
}

_DEMO_SALDOS = [
    {
        "account_id": "demo_001",
        "iban": "ES91 2100 0418 4502 0005 1332",
        "nombre": "Cuenta Corriente (Demo)",
        "saldo": 18450.72,
        "moneda": "EUR",
    },
    {
        "account_id": "demo_002",
        "iban": "ES80 2310 0001 1800 0001 2345",
        "nombre": "Cuenta Ahorro (Demo)",
        "saldo": 5200.00,
        "moneda": "EUR",
    },
]

_DEMO_TXS = [
    {
        "id": "1",
        "fecha": "2026-03-15",
        "concepto": "TRANSFERENCIA RECIBIDA ACME SL",
        "importe": 4500,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "2",
        "fecha": "2026-03-14",
        "concepto": "AMAZON WEB SERVICES",
        "importe": -350,
        "tipo": "cargo",
        "categoria": "proveedor_servicio",
    },
    {
        "id": "3",
        "fecha": "2026-03-13",
        "concepto": "NOMINAS MARZO 2026",
        "importe": -12000,
        "tipo": "cargo",
        "categoria": "nominas",
    },
    {
        "id": "4",
        "fecha": "2026-03-12",
        "concepto": "ENGIE ENERGIA FACTURA",
        "importe": -280.50,
        "tipo": "cargo",
        "categoria": "suministros",
    },
    {
        "id": "5",
        "fecha": "2026-03-11",
        "concepto": "COBRO FACTURA #2026-041",
        "importe": 7200,
        "tipo": "abono",
        "categoria": "cliente_cobro",
    },
    {
        "id": "6",
        "fecha": "2026-03-10",
        "concepto": "CUOTA PRESTAMO BANCO",
        "importe": -1100,
        "tipo": "cargo",
        "categoria": "financiero",
    },
]


async def _get_psd2_credentials(tenant_id: str) -> dict | None:
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
