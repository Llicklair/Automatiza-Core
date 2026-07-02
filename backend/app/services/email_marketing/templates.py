"""CRUD de plantillas de email marketing. Recibe `db` inyectado (CQRS-lite)."""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.email_marketing import EmailTemplate


async def list_templates(tenant_id: UUID, db: AsyncSession) -> list[EmailTemplate]:
    result = await db.execute(
        select(EmailTemplate).where(EmailTemplate.tenant_id == tenant_id).order_by(EmailTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def _get_template(template_id: UUID, tenant_id: UUID, db: AsyncSession) -> EmailTemplate | None:
    result = await db.execute(
        select(EmailTemplate).where(
            EmailTemplate.id == template_id,
            EmailTemplate.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def create_template(payload: Any, tenant_id: UUID, db: AsyncSession) -> EmailTemplate:
    tpl = EmailTemplate(
        tenant_id=tenant_id,
        name=payload.name,
        subject=payload.subject,
        html_body=payload.html_body,
    )
    db.add(tpl)
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def update_template(template_id: UUID, payload: Any, tenant_id: UUID, db: AsyncSession) -> EmailTemplate | None:
    tpl = await _get_template(template_id, tenant_id, db)
    if tpl is None:
        return None
    tpl.name = payload.name
    tpl.subject = payload.subject
    tpl.html_body = payload.html_body
    await db.commit()
    await db.refresh(tpl)
    return tpl


async def delete_template(template_id: UUID, tenant_id: UUID, db: AsyncSession) -> bool:
    tpl = await _get_template(template_id, tenant_id, db)
    if tpl is None:
        return False
    await db.delete(tpl)
    await db.commit()
    return True
