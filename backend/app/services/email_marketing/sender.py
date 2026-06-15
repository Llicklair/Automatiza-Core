"""Envío de campañas de email marketing.

Lógica compartida entre el endpoint "enviar ahora" (BackgroundTasks) y el
worker APScheduler que dispara las campañas programadas al vencer su
`scheduled_at`.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient
from app.services.audit import log_action
from app.services.email.sender import send_email, send_failed

logger = logging.getLogger(__name__)


def _render(template: str, recipient: EmailCampaignRecipient) -> str:
    return template.replace("{{nombre}}", recipient.name or "").replace(
        "{{email}}", recipient.email
    )


async def send_campaign(campaign_id: str, tenant_id: str) -> None:
    """Envía una campaña completa: un email por destinatario pendiente.

    Abre su propia sesión (corre en background o en el scheduler). Marca la
    campaña `sending` → `sent` y cada destinatario `sent`/`failed`.
    """
    from app.db.base import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(EmailCampaign).where(EmailCampaign.id == UUID(campaign_id))
        )
        campaign = result.scalar_one_or_none()
        if not campaign or campaign.status in ("sending", "sent"):
            return

        campaign.status = "sending"
        await db.commit()

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
                    body=_render(campaign.html_body, r),
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
        logger.info(
            "[EMAIL-MKT] Campaña %s enviada: %s ok, %s fallidos", campaign_id, sent, failed
        )
