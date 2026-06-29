"""Campañas de marketing social: CRUD básico (sin email-marketing)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import Campaign


async def list_campaigns(tenant_id, db: AsyncSession) -> list[Campaign]:
    result = await db.execute(
        select(Campaign)
        .where(Campaign.tenant_id == tenant_id)
        .order_by(Campaign.created_at.desc())
    )
    return list(result.scalars().all())


async def create_campaign(
    tenant_id,
    name: str,
    description: Optional[str],
    db: AsyncSession,
) -> Campaign:
    campaign = Campaign(
        tenant_id=tenant_id,
        name=name,
        description=description,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


async def get_campaign(campaign_id: UUID, tenant_id, db: AsyncSession) -> Campaign | None:
    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()
