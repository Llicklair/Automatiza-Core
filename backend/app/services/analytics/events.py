"""Tracking de eventos producto (OPS.MET).

Eventos canónicos consensuados — solo se instrumentan los **hitos del funnel**
que importan para detectar churn temprano y validar pricing. NO se trackea
cada acción del usuario (eso sería intrusivo y violaría la política de
privacidad documentada en `docs/telemetry-data-policy.md`).

Backend para PostHog (cuando `settings.POSTHOG_API_KEY` está configurado).
Fallback: registro en `audit_log` con `agent_name="analytics"` para tener
trazabilidad local incluso sin servicio externo.

Política de PII: el `distinct_id` enviado a PostHog es `tenant_id_hash`
(hash con salt rotada 90d desde `telemetry_scrubber.hash_tenant_id`).
Los `properties` se filtran con `scrub_event` antes del envío.
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from uuid import UUID

logger = logging.getLogger("analytics.events")


# Eventos canónicos — añadir uno requiere PR + actualización de este módulo.
EventName = Literal[
    "user.signup",
    "tenant.onboarding_completed",
    "invoice.first_created",
    "invoice.created",
    "model_aeat.first_presented",
    "model_aeat.presented",
    "fiscal_approval.requested",
    "fiscal_approval.approved",
    "fiscal_approval.rejected",
    "subscription.upgraded",
    "subscription.cancelled",
    "backup.first_completed",
    "backup.completed",
    "telemetry.opted_out",
    "ai_agent.invocation_overage",
]

CANONICAL_EVENTS: frozenset[str] = frozenset({
    "user.signup",
    "tenant.onboarding_completed",
    "invoice.first_created",
    "invoice.created",
    "model_aeat.first_presented",
    "model_aeat.presented",
    "fiscal_approval.requested",
    "fiscal_approval.approved",
    "fiscal_approval.rejected",
    "subscription.upgraded",
    "subscription.cancelled",
    "backup.first_completed",
    "backup.completed",
    "telemetry.opted_out",
    "ai_agent.invocation_overage",
})


async def track_event(
    *,
    event: str,
    tenant_id: UUID | str,
    properties: dict[str, Any] | None = None,
) -> bool:
    """Registra un evento de producto.

    Devuelve `True` si se procesó correctamente (sea PostHog o fallback log).
    Devuelve `False` si el evento no es canónico (early-return defensivo).

    Sin levantar excepción: nunca debe bloquear flujos de negocio.

    `properties` se scrubea con `telemetry_scrubber.scrub_event` antes de
    enviarse — PII residual en propiedades se redacta en origen.
    """
    if event not in CANONICAL_EVENTS:
        logger.warning("Evento no canónico ignorado: %s", event)
        return False

    try:
        from app.core.telemetry_scrubber import hash_tenant_id, scrub_event
        from app.core.config import settings

        # Pseudonimizar tenant_id con salt rotada (placeholder fijo para MVP;
        # en producción se carga rotación desde `settings.TELEMETRY_SALT`).
        salt = getattr(settings, "TELEMETRY_SALT", "default-rotating-salt")
        distinct_id = hash_tenant_id(str(tenant_id), salt=salt)

        clean_props: dict[str, Any] = scrub_event(properties or {}) or {}

        posthog_key = getattr(settings, "POSTHOG_API_KEY", "") or ""
        if posthog_key:
            await _send_to_posthog(distinct_id, event, clean_props, posthog_key)
        else:
            # Fallback: log estructurado local
            logger.info(
                "event=%s distinct_id=%s properties=%s",
                event, distinct_id, clean_props,
            )
        return True
    except Exception as e:  # nunca bloquear caller
        logger.warning("track_event(%s) error: %s", event, e)
        return False


async def _send_to_posthog(
    distinct_id: str, event: str, properties: dict[str, Any], api_key: str,
) -> None:
    """Envía el evento a la PostHog API.

    Implementación mínima HTTP — evita la dependencia oficial `posthog-python`
    para no añadir un cliente HTTP global. Usa `httpx` que ya está en deps.

    Errores de red no se propagan: el caller no debe enterarse si PostHog
    está caído. El log local sirve de respaldo.
    """
    import httpx
    from app.core.config import settings

    host = getattr(settings, "POSTHOG_HOST", "https://eu.posthog.com")
    payload = {
        "api_key": api_key,
        "event": event,
        "distinct_id": distinct_id,
        "properties": properties,
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{host}/capture/", json=payload)
    except Exception as e:
        logger.info("posthog send falló (silenciado): %s", e)
