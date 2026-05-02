"""
Email-sender service — public API para que cualquier capa (agentes, routes,
otros services) envíe emails sin importar directamente del agente de email.

Cumple la regla de arquitectura "agentes NUNCA importan otros agentes":
billing/hr/etc llaman a este service, no a `app.agents.email`.

La implementación real vive aún en `agents/email/agent.py` (refactor pendiente
para mover los helpers OAuth/SMTP a este módulo); este facade aísla a los
callers de esa decisión, así el refactor futuro será transparente.
"""
from __future__ import annotations


async def send_email(
    tenant_id: str,
    to: str,
    subject: str,
    body: str,
    attachment_ids: list[str] | None = None,
) -> str:
    """Envía un email usando las credenciales del tenant (gmail > outlook > smtp).

    Devuelve un string descriptivo del resultado (success o error). No lanza
    excepciones — los errores se reportan como string para no romper agentes.
    """
    from app.agents.email.agent import send_email_direct

    return await send_email_direct(
        tenant_id=tenant_id,
        to=to,
        subject=subject,
        body=body,
        attachment_ids=attachment_ids,
    )
