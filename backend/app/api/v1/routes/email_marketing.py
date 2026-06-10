"""Email marketing: plantillas, campañas y envíos masivos."""

import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.crm import Client
from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient, EmailTemplate
from app.db.models.models import User
from app.services.email_marketing import send_campaign as send_campaign_service

router = APIRouter(prefix="/email-marketing", tags=["email-marketing"])

# ── Schemas ────────────────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    name: str
    subject: str
    html_body: str


class TemplateOut(BaseModel):
    id: UUID
    name: str
    subject: str
    html_body: str
    created_at: datetime.datetime
    updated_at: Optional[datetime.datetime] = None

    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    name: str
    subject: str
    html_body: str
    template_id: Optional[UUID] = None
    scheduled_at: Optional[datetime.datetime] = None


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None
    scheduled_at: Optional[datetime.datetime] = None


class CampaignOut(BaseModel):
    id: UUID
    name: str
    subject: str
    html_body: str
    status: str
    scheduled_at: Optional[datetime.datetime] = None
    sent_at: Optional[datetime.datetime] = None
    total_count: int
    sent_count: int
    failed_count: int
    template_id: Optional[UUID] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Templates ──────────────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailTemplate)
        .where(EmailTemplate.tenant_id == current_user.tenant_id)
        .order_by(EmailTemplate.created_at.desc())
    )
    return result.scalars().all()


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tpl = EmailTemplate(
        tenant_id=current_user.tenant_id,
        name=body.name,
        subject=body.subject,
        html_body=body.html_body,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.put("/templates/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: UUID,
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    tpl.name = body.name
    tpl.subject = body.subject
    tpl.html_body = body.html_body
    await db.commit()
    await db.refresh(tpl)
    return tpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == current_user.tenant_id,
        )
    )
    tpl = result.scalar_one_or_none()
    if not tpl:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    await db.delete(tpl)
    await db.commit()


# ── Campaigns ──────────────────────────────────────────────────────────────────


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailCampaign)
        .where(EmailCampaign.tenant_id == current_user.tenant_id)
        .order_by(EmailCampaign.created_at.desc())
    )
    return result.scalars().all()


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Cuenta destinatarios: clientes con email del tenant
    count_result = await db.execute(
        select(func.count()).select_from(Client).where(
            Client.tenant_id == current_user.tenant_id,
            Client.email.isnot(None),
            Client.email != "",
            Client.marketing_consent.is_(True),
        )
    )
    total = count_result.scalar() or 0

    campaign = EmailCampaign(
        tenant_id=current_user.tenant_id,
        template_id=body.template_id,
        name=body.name,
        subject=body.subject,
        html_body=body.html_body,
        scheduled_at=body.scheduled_at,
        status="scheduled" if body.scheduled_at else "draft",
        total_count=total,
    )
    db.add(campaign)
    await db.flush()

    # Precarga destinatarios desde CRM
    clients_result = await db.execute(
        select(Client).where(
            Client.tenant_id == current_user.tenant_id,
            Client.email.isnot(None),
            Client.email != "",
            Client.marketing_consent.is_(True),
        )
    )
    for client in clients_result.scalars().all():
        db.add(EmailCampaignRecipient(
            campaign_id=campaign.id,
            email=client.email,
            name=client.name,
        ))

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.put("/campaigns/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: UUID,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailCampaign).where(
            EmailCampaign.id == campaign_id,
            EmailCampaign.tenant_id == current_user.tenant_id,
            EmailCampaign.status.in_(["draft", "scheduled"]),
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada o ya enviada")
    if body.name is not None:
        campaign.name = body.name
    if body.subject is not None:
        campaign.subject = body.subject
    if body.html_body is not None:
        campaign.html_body = body.html_body
    if body.scheduled_at is not None:
        campaign.scheduled_at = body.scheduled_at
        campaign.status = "scheduled"
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailCampaign).where(
            EmailCampaign.id == campaign_id,
            EmailCampaign.tenant_id == current_user.tenant_id,
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    await db.delete(campaign)
    await db.commit()


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(EmailCampaign).where(
            EmailCampaign.id == campaign_id,
            EmailCampaign.tenant_id == current_user.tenant_id,
            EmailCampaign.status.in_(["draft", "scheduled"]),
        )
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada o ya enviada")

    background_tasks.add_task(
        send_campaign_service,
        str(campaign_id),
        str(current_user.tenant_id),
    )
    return {"queued": campaign.total_count}


@router.get("/recipients/count")
async def recipient_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(func.count()).select_from(Client).where(
            Client.tenant_id == current_user.tenant_id,
            Client.email.isnot(None),
            Client.email != "",
            Client.marketing_consent.is_(True),
        )
    )
    return {"count": result.scalar() or 0}
