"""Email marketing: plantillas, campañas y envíos masivos.

Rutas delgadas: validan input + mapean a HTTP. La lógica de negocio vive en
`services/email_marketing/` (templates / campaigns / recipients).
"""

import datetime
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.email_marketing import EmailCampaign, EmailTemplate
from app.db.models.models import User
from app.services.email_marketing import campaigns as campaigns_svc
from app.services.email_marketing import recipients as recipients_svc
from app.services.email_marketing import send_campaign as send_campaign_service
from app.services.email_marketing import templates as templates_svc

router = APIRouter(prefix="/email-marketing", tags=["email-marketing"])


def _validate_future(v: datetime.datetime | None) -> datetime.datetime | None:
    """Rechaza un `scheduled_at` en el pasado (normaliza naive→UTC para comparar)."""
    if v is not None:
        now = datetime.datetime.now(datetime.UTC)
        vv = v if v.tzinfo is not None else v.replace(tzinfo=datetime.UTC)
        if vv < now:
            raise ValueError("scheduled_at debe ser una fecha futura")
    return v


# ── Schemas ────────────────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    name: str = Field(max_length=200)
    subject: str = Field(max_length=300)
    html_body: str = Field(max_length=500_000)


class TemplateOut(BaseModel):
    id: UUID
    name: str
    subject: str
    html_body: str
    created_at: datetime.datetime
    updated_at: datetime.datetime | None = None

    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    name: str = Field(max_length=200)
    subject: str = Field(max_length=300)
    html_body: str = Field(max_length=500_000)
    template_id: UUID | None = None
    scheduled_at: datetime.datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _check_scheduled_at(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return _validate_future(v)


class CampaignUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    html_body: str | None = None
    scheduled_at: datetime.datetime | None = None

    @field_validator("scheduled_at")
    @classmethod
    def _check_scheduled_at(cls, v: datetime.datetime | None) -> datetime.datetime | None:
        return _validate_future(v)


class CampaignOut(BaseModel):
    id: UUID
    name: str
    subject: str
    html_body: str
    status: str
    scheduled_at: datetime.datetime | None = None
    sent_at: datetime.datetime | None = None
    total_count: int
    sent_count: int
    failed_count: int
    template_id: UUID | None = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Templates ──────────────────────────────────────────────────────────────────


@router.get("/templates", response_model=list[TemplateOut])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailTemplate]:
    return await templates_svc.list_templates(current_user.tenant_id, db)


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplate:
    return await templates_svc.create_template(body, current_user.tenant_id, db)


@router.put("/templates/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: UUID,
    body: TemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailTemplate:
    tpl = await templates_svc.update_template(template_id, body, current_user.tenant_id, db)
    if tpl is None:
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")
    return tpl


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not await templates_svc.delete_template(template_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Plantilla no encontrada")


# ── Campaigns ──────────────────────────────────────────────────────────────────


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[EmailCampaign]:
    return await campaigns_svc.list_campaigns(current_user.tenant_id, db)


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailCampaign:
    return await campaigns_svc.create_campaign(body, current_user.tenant_id, db)


@router.put("/campaigns/{campaign_id}", response_model=CampaignOut)
async def update_campaign(
    campaign_id: UUID,
    body: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EmailCampaign:
    campaign = await campaigns_svc.update_campaign(campaign_id, body, current_user.tenant_id, db)
    if campaign is None:
        raise HTTPException(status_code=404, detail="Campaña no encontrada o ya enviada")
    return campaign


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        deleted = await campaigns_svc.delete_campaign(campaign_id, current_user.tenant_id, db)
    except campaigns_svc.CampaignInSendingError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La campaña se está enviando ahora mismo; espera a que termine para borrarla",
        ) from None
    if not deleted:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    campaign = await campaigns_svc.get_sendable_campaign(campaign_id, current_user.tenant_id, db)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaña no encontrada o ya enviada")

    background_tasks.add_task(
        send_campaign_service,
        str(campaign_id),
        str(current_user.tenant_id),
    )
    return {"queued": campaign.total_count}  # type: ignore[dict-item]


@router.get("/recipients/count")
async def recipient_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    return {"count": await recipients_svc.count_recipients(current_user.tenant_id, db)}
