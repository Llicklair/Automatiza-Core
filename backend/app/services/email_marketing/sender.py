"""Envío de campañas de email marketing.

Lógica compartida entre el endpoint "enviar ahora" (BackgroundTasks) y el
worker APScheduler que dispara las campañas programadas al vencer su
`scheduled_at`.
"""

import html
import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update

from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient
from app.services.audit import log_action
from app.services.email.sender import send_email, send_failed

logger = logging.getLogger(__name__)


def _render(template: str, recipient: EmailCampaignRecipient, *, escape_html: bool = False) -> str:
    # En el CUERPO HTML escapamos los valores sustituidos (no la plantilla, que es
    # HTML que el tenant escribe a propósito) para que `&`, `<`, `>`… no rompan el
    # HTML ni permitan inyección de marcado/XSS. En el ASUNTO (cabecera de texto
    # plano) NO se escapa: el cliente de correo no decodifica entidades HTML en el
    # Subject, así que escaparlo mostraría `&amp;` literal.
    name = str(recipient.name or "")
    email = str(recipient.email or "")
    if escape_html:
        name = html.escape(name)
        email = html.escape(email)
    return template.replace("{{nombre}}", name).replace("{{email}}", email)


async def send_campaign(campaign_id: str, tenant_id: str) -> None:
    """Envía una campaña completa: un email por destinatario pendiente.

    Abre su propia sesión (corre en background o en el scheduler). Marca la
    campaña `sending` → `sent` y cada destinatario `sent`/`failed`.
    """
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        # Esta sesión corre en background/scheduler: NO pasa por get_current_user,
        # así que el tenant del listener RLS no está fijado. Anclamos la consulta
        # al tenant_id (que ya llega como parámetro) como defensa en profundidad:
        # un campaign_id de otro tenant nunca se envía con estas credenciales.
        # Atomic claim: flip the campaign to "sending" in ONE conditional UPDATE.
        # Only one concurrent caller (scheduler tick vs. manual "send now") can match
        # `status NOT IN (sending, sent)`; the loser matches 0 rows and bails. This
        # closes the TOCTOU double-send race (the old SELECT-check-write let both
        # callers pass the guard and every recipient got 2 emails). Correct by
        # construction at the DB level — the exclusivity is the UPDATE's WHERE, not a
        # read-then-write window.
        claim = await db.execute(
            update(EmailCampaign)
            .where(
                EmailCampaign.id == UUID(campaign_id),
                EmailCampaign.tenant_id == UUID(tenant_id),
                EmailCampaign.status.not_in(("sending", "sent")),
            )
            .values(status="sending")
        )
        await db.commit()
        if claim.rowcount == 0:
            return  # already claimed by a concurrent sender, missing, or wrong tenant

        result = await db.execute(
            select(EmailCampaign).where(
                EmailCampaign.id == UUID(campaign_id),
                EmailCampaign.tenant_id == UUID(tenant_id),
            )
        )
        campaign = result.scalar_one_or_none()
        if not campaign:
            return

        recipients = await db.execute(
            select(EmailCampaignRecipient).where(
                EmailCampaignRecipient.campaign_id == UUID(campaign_id),
                EmailCampaignRecipient.status == "pending",
            )
        )
        rows = recipients.scalars().all()

        sent = 0
        failed = 0
        for r in rows:
            try:
                result = await send_email(
                    tenant_id=tenant_id,
                    to=r.email,
                    subject=_render(campaign.subject, r),
                    body=_render(campaign.html_body, r, escape_html=True),
                )
            except Exception as e:  # send_email no debería lanzar, pero por si acaso
                result = f"Error al enviar correo: {e}"
            if send_failed(result):
                r.status = "failed"
                r.error_message = str(result)[:500]
                failed += 1
            else:
                r.status = "sent"
                r.sent_at = datetime.now(UTC)
                sent += 1

        campaign.status = "sent"
        campaign.sent_at = datetime.now(UTC)
        campaign.sent_count = sent
        campaign.failed_count = failed
        await log_action(
            db,
            tenant_id=UUID(tenant_id),
            agent_name="email_marketing",
            action_type="email_campaign_sent",
            status="success" if failed == 0 else "error",
            output_data={"campaign_id": campaign_id, "sent": sent, "failed": failed},
        )
        await db.commit()
        logger.info("[EMAIL-MKT] Campaña %s enviada: %s ok, %s fallidos", campaign_id, sent, failed)
