"""Tool `create_campaign` del agente marketing: gate + programación de posts."""

from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.agents.marketing.tools import create_campaign
from app.db.models.marketing import Campaign, ScheduledPost, SocialAccount
from app.services.autonomy import set_policy

pytestmark = pytest.mark.asyncio


def _patched_sessions(db):
    """Patcha AsyncSessionLocal en el gate (import local) y en el body de la tool."""

    @asynccontextmanager
    async def ctx():
        yield db

    return (
        patch("app.db.base.AsyncSessionLocal", side_effect=ctx),
        patch("app.agents.marketing.tools.AsyncSessionLocal", side_effect=ctx),
    )


async def _seed_account(db, tenant_id) -> SocialAccount:
    acc = SocialAccount(
        tenant_id=tenant_id,
        platform="twitter",
        account_id="123",
        account_name="@pyme",
        access_token="enc",
        is_active=True,
    )
    db.add(acc)
    await db.flush()
    return acc


def _posts(account_id: str) -> list[dict]:
    return [
        {
            "platform": "twitter",
            "social_account_id": account_id,
            "content": "Post 1 🚀 #pyme",
            "scheduled_at": "2026-06-15T10:00:00Z",
        },
        {
            "platform": "twitter",
            "social_account_id": account_id,
            "content": "Post 2 ☀️ #verano",
            "scheduled_at": "2026-06-16T19:00:00Z",
            "image_url": "https://images.example/x.jpg",
        },
    ]


async def test_auto_programa_campania_y_posts(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await set_policy(db, tenant_id=tenant.id, domain="marketing", mode="AUTO")
    acc = await _seed_account(db, tenant.id)
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        result = await create_campaign.coroutine(
            tenant_id=str(tenant.id),
            name="Lanzamiento verano",
            posts=_posts(str(acc.id)),
        )

    assert "creada" in result
    camp = (await db.execute(select(Campaign).where(Campaign.tenant_id == tenant.id))).scalar_one()
    assert camp.name == "Lanzamiento verano"
    posts = (await db.execute(select(ScheduledPost).where(ScheduledPost.campaign_id == camp.id))).scalars().all()
    assert len(posts) == 2
    assert all(p.status == "scheduled" for p in posts)


async def test_confirm_por_defecto_no_programa(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    acc = await _seed_account(db, tenant.id)
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        result = await create_campaign.coroutine(
            tenant_id=str(tenant.id),
            name="Campaña gateada",
            posts=_posts(str(acc.id)),
        )

    assert "pendiente" in result.lower()
    camps = (await db.execute(select(Campaign).where(Campaign.tenant_id == tenant.id))).scalars().all()
    assert camps == []


async def test_valida_campos_y_cuentas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await set_policy(db, tenant_id=tenant.id, domain="marketing", mode="AUTO")
    acc = await _seed_account(db, tenant.id)
    await db.commit()

    p1, p2 = _patched_sessions(db)
    with p1, p2:
        # post sin content
        bad = [{"platform": "twitter", "social_account_id": str(acc.id), "scheduled_at": "2026-06-15T10:00:00Z"}]
        result = await create_campaign.coroutine(tenant_id=str(tenant.id), name="X", posts=bad)
        assert "faltan campos" in result

        # cuenta inexistente
        ghost = _posts("00000000-0000-0000-0000-000000000001")
        result = await create_campaign.coroutine(tenant_id=str(tenant.id), name="X", posts=ghost)
        assert "no encontradas" in result

        # sin posts
        result = await create_campaign.coroutine(tenant_id=str(tenant.id), name="X", posts=[])
        assert "al menos un post" in result
