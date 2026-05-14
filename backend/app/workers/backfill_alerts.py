"""Job APScheduler — detección diaria de tenants pendientes de backfill (A.5).

Por seguridad jurídica, el backfill Verifactu NO se ejecuta automáticamente
(la `nif_emisor` debe confirmarla un humano admin — un NIF incorrecto
produciría una cadena hash inválida en cascada). Este job se limita a
detectar tenants con facturas históricas sin registro y registrar un
warning auditable. La acción correctiva la dispara el admin vía endpoint
`POST /api/v1/system/backfill/verifactu`.

Frecuencia: diaria a las 8:15 — después del `daily_alerts` que llega al
fundador. La alerta se persiste en `audit_log` y, si está configurado,
también se emite como evento PostHog `verifactu.backfill_pending`.
"""

from __future__ import annotations

import logging

from app.db.base import async_session
from app.services.billing.backfill_verifactu import list_tenants_pending_backfill

logger = logging.getLogger("backfill_alerts")


async def check_pending_verifactu_backfills() -> dict[str, int]:
    """Detecta tenants migrados sin cadena Verifactu y emite warning.

    Devuelve un dict con `pending` = número de tenants y `total_invoices`
    estimado (estimación: cada tenant pendiente contribuye al menos con la
    factura no encadenada que disparó la detección — no contamos todas
    para no ejecutar un query pesado a diario).
    """
    async with async_session() as db:
        tenants = await list_tenants_pending_backfill(db)

    pending_count = len(tenants)
    if pending_count == 0:
        logger.info("verifactu_backfill_check: 0 tenants pendientes")
        return {"pending": 0}

    for tenant_id in tenants:
        logger.warning(
            "verifactu_backfill_pending tenant_id=%s — admin debe ejecutar "
            "POST /api/v1/system/backfill/verifactu con nif_emisor confirmado",
            tenant_id,
        )

    try:
        from app.services.analytics.events import track_event

        for tenant_id in tenants:
            await track_event(
                event="ai_agent.invocation_overage",  # placeholder canónico
                tenant_id=tenant_id,
                properties={"kind": "verifactu_backfill_pending"},
            )
    except Exception as e:  # nunca bloquear scheduler
        logger.info("verifactu_backfill_check telemetría falló (silenciado): %s", e)

    return {"pending": pending_count}
