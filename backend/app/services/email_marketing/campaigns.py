"""CRUD de campañas de email marketing + precarga de destinatarios.

Recibe `db` inyectado (CQRS-lite). La lógica de "qué clientes son destinatarios"
vive en `recipients.py` (única fuente).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient
from app.services.email_marketing.recipients import list_recipients

_EDITABLE_STATUSES = ("draft", "scheduled")


class CampaignInSendingError(Exception):
    """La campaña está en pleno envío: no se puede borrar (la ruta lo mapea a HTTP 409)."""


async def list_campaigns(tenant_id: UUID, db: AsyncSession) -> list[EmailCampaign]:
    result = await db.execute(
        select(EmailCampaign)
        .where(EmailCampaign.tenant_id == tenant_id)
        .order_by(EmailCampaign.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_campaign(
    campaign_id: UUID, tenant_id: UUID, db: AsyncSession, *, statuses: tuple[str, ...] | None = None
) -> EmailCampaign | None:
    query = select(EmailCampaign).where(
        EmailCampaign.id == campaign_id,
        EmailCampaign.tenant_id == tenant_id,
    )
    if statuses is not None:
        query = query.where(EmailCampaign.status.in_(statuses))
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_campaign(payload: Any, tenant_id: UUID, db: AsyncSession) -> EmailCampaign:
    """Crea la campaña y precarga un EmailCampaignRecipient por cada destinatario.

    `payload` es el schema Pydantic de la ruta (CampaignCreate). Se tipa como Any
    porque el schema vive en la capa route y los services no importan de routes.
    """
    # Una sola lectura de destinatarios: total_count = nº de filas realmente
    # insertadas (evita el TOCTOU entre un count() y un list() separados que podían
    # divergir si un cliente se añadía/quitaba entre las dos consultas).
    recipients = await list_recipients(tenant_id, db)
    campaign = EmailCampaign(
        tenant_id=tenant_id,
        template_id=payload.template_id,
        name=payload.name,
        subject=payload.subject,
        html_body=payload.html_body,
        scheduled_at=payload.scheduled_at,
        status="scheduled" if payload.scheduled_at else "draft",
        total_count=len(recipients),
    )
    db.add(campaign)
    await db.flush()  # poblar campaign.id antes de las líneas (atómico, un solo commit)

    for client in recipients:
        db.add(
            EmailCampaignRecipient(
                campaign_id=campaign.id,
                email=client.email,
                name=client.name,
            )
        )

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def update_campaign(
    campaign_id: UUID, payload: Any, tenant_id: UUID, db: AsyncSession
) -> EmailCampaign | None:
    """Actualiza una campaña aún editable (draft/scheduled). None si no existe/ya enviada."""
    campaign = await _get_campaign(campaign_id, tenant_id, db, statuses=_EDITABLE_STATUSES)
    if campaign is None:
        return None
    if payload.name is not None:
        campaign.name = payload.name
    if payload.subject is not None:
        campaign.subject = payload.subject
    if payload.html_body is not None:
        campaign.html_body = payload.html_body
    if payload.scheduled_at is not None:
        campaign.scheduled_at = payload.scheduled_at
        campaign.status = "scheduled"
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def delete_campaign(campaign_id: UUID, tenant_id: UUID, db: AsyncSession) -> bool:
    campaign = await _get_campaign(campaign_id, tenant_id, db)
    if campaign is None:
        return False
    if campaign.status == "sending":
        # No borrar en pleno envío: el worker en background sigue iterando los
        # EmailCampaignRecipient de esta campaña; el cascade delete los dejaría
        # huérfanos o lanzaría IntegrityError a mitad de envío.
        raise CampaignInSendingError
    await db.delete(campaign)
    await db.commit()
    return True


async def get_sendable_campaign(
    campaign_id: UUID, tenant_id: UUID, db: AsyncSession
) -> EmailCampaign | None:
    """Campaña en estado enviable (draft/scheduled), para la ruta /send."""
    return await _get_campaign(campaign_id, tenant_id, db, statuses=_EDITABLE_STATUSES)
