"""Campañas de email: envío por servicio, worker de programadas y opt-in RGPD."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.db.models.crm import Client
from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient

pytestmark = pytest.mark.asyncio


def _patched_session(db):
    @asynccontextmanager
    async def ctx():
        yield db

    return patch("app.db.base.AsyncSessionLocal", side_effect=ctx)


async def _make_campaign(db, tenant_id, *, status="scheduled", scheduled_at=None, recipients=1):
    camp = EmailCampaign(
        tenant_id=tenant_id,
        name="News junio",
        subject="Hola {{nombre}}",
        html_body="<p>Hola {{nombre}}</p>",
        status=status,
        scheduled_at=scheduled_at,
        total_count=recipients,
    )
    db.add(camp)
    await db.flush()
    for i in range(recipients):
        db.add(EmailCampaignRecipient(campaign_id=camp.id, email=f"c{i}@test.es", name=f"Cli {i}"))
    await db.flush()
    return camp


async def test_send_campaign_envia_y_marca(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    camp = await _make_campaign(db, tenant.id, recipients=2)
    await db.commit()

    sent_to = []

    async def fake_send(*, tenant_id, to, subject, body, **kw):
        sent_to.append((to, subject))

    from app.services.email_marketing import sender

    with _patched_session(db), patch.object(sender, "send_email", fake_send):
        await sender.send_campaign(str(camp.id), str(tenant.id))

    await db.refresh(camp)
    assert camp.status == "sent"
    assert camp.sent_count == 2
    assert camp.failed_count == 0
    assert sent_to[0][1] == "Hola Cli 0"  # variable {{nombre}} renderizada
    rec_status = (
        await db.execute(select(EmailCampaignRecipient.status).where(EmailCampaignRecipient.campaign_id == camp.id))
    ).scalars().all()
    assert set(rec_status) == {"sent"}


async def test_send_campaign_marca_fallos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    camp = await _make_campaign(db, tenant.id, recipients=1)
    await db.commit()

    async def boom(**kw):
        raise RuntimeError("SMTP caído")

    from app.services.email_marketing import sender

    with _patched_session(db), patch.object(sender, "send_email", boom):
        await sender.send_campaign(str(camp.id), str(tenant.id))

    await db.refresh(camp)
    assert camp.failed_count == 1
    assert camp.sent_count == 0


async def test_worker_envia_solo_vencidas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    due = await _make_campaign(db, tenant.id, scheduled_at=datetime.now(UTC) - timedelta(minutes=5))
    future = await _make_campaign(db, tenant.id, scheduled_at=datetime.now(UTC) + timedelta(hours=2))
    draft = await _make_campaign(db, tenant.id, status="draft", scheduled_at=None)
    await db.commit()

    sent_ids = []

    async def fake_send_campaign(campaign_id, tenant_id):
        sent_ids.append(campaign_id)

    from app.workers.tasks_scheduler import _send_scheduled_email_campaigns

    with _patched_session(db), patch(
        "app.services.email_marketing.send_campaign", fake_send_campaign
    ):
        result = await _send_scheduled_email_campaigns()

    assert result == {"sent": 1}
    assert sent_ids == [str(due.id)]
    assert str(future.id) not in sent_ids and str(draft.id) not in sent_ids


async def test_campaign_solo_clientes_con_consentimiento(db, auth_client, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    db.add(Client(tenant_id=tenant.id, name="Con consent", email="si@test.es", marketing_consent=True))
    db.add(Client(tenant_id=tenant.id, name="Sin consent", email="no@test.es", marketing_consent=False))
    db.add(Client(tenant_id=tenant.id, name="Sin email", marketing_consent=True))
    await db.commit()

    resp = await auth_client.get("/api/v1/email-marketing/recipients/count")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    resp = await auth_client.post(
        "/api/v1/email-marketing/campaigns",
        json={"name": "Test", "subject": "S", "html_body": "<p>b</p>"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["total_count"] == 1

    recipients = (
        await db.execute(
            select(EmailCampaignRecipient.email).join(
                EmailCampaign, EmailCampaign.id == EmailCampaignRecipient.campaign_id
            ).where(EmailCampaign.tenant_id == tenant.id)
        )
    ).scalars().all()
    assert recipients == ["si@test.es"]
