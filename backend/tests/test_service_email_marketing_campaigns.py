"""Regresión R1 (2026-06-25): la lógica de email marketing vive en services/, no en
la ruta. Cubre create_campaign (precarga de destinatarios) + CRUD vía servicio.
"""

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.db.models.crm import Client
from app.db.models.email_marketing import EmailCampaignRecipient
from app.services.email_marketing import campaigns as campaigns_svc
from app.services.email_marketing import recipients as recipients_svc
from app.services.email_marketing import templates as templates_svc


async def _seed_clients(db, tenant_id):
    # 2 consentidos con email; 1 sin consent; 1 sin email → solo 2 destinatarios válidos.
    db.add_all([
        Client(tenant_id=tenant_id, name="Ana", nif="B11111111", email="ana@x.com", marketing_consent=True),
        Client(tenant_id=tenant_id, name="Beto", nif="B22222222", email="beto@x.com", marketing_consent=True),
        Client(tenant_id=tenant_id, name="NoConsent", nif="B33333333", email="c@x.com", marketing_consent=False),
        Client(tenant_id=tenant_id, name="SinEmail", nif="B44444444", email="", marketing_consent=True),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_create_campaign_precarga_solo_destinatarios_consentidos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await _seed_clients(db, tenant.id)

    payload = SimpleNamespace(
        name="Promo", subject="Hola", html_body="<p>hi</p>", template_id=None, scheduled_at=None
    )
    campaign = await campaigns_svc.create_campaign(payload, tenant.id, db)

    assert campaign.status == "draft"
    assert campaign.total_count == 2  # solo Ana y Beto (consent + email)

    rows = (
        await db.execute(
            select(EmailCampaignRecipient).where(
                EmailCampaignRecipient.campaign_id == campaign.id
            )
        )
    ).scalars().all()
    assert {r.email for r in rows} == {"ana@x.com", "beto@x.com"}


@pytest.mark.asyncio
async def test_recipient_count(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    await _seed_clients(db, tenant.id)
    assert await recipients_svc.count_recipients(tenant.id, db) == 2


@pytest.mark.asyncio
async def test_campaign_crud_via_service(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    payload = SimpleNamespace(
        name="C", subject="S", html_body="<p>b</p>", template_id=None, scheduled_at=None
    )
    c = await campaigns_svc.create_campaign(payload, tenant.id, db)

    upd = await campaigns_svc.update_campaign(
        c.id, SimpleNamespace(name="C2", subject=None, html_body=None, scheduled_at=None), tenant.id, db
    )
    assert upd is not None and upd.name == "C2"

    assert await campaigns_svc.delete_campaign(c.id, tenant.id, db) is True
    assert await campaigns_svc.get_sendable_campaign(c.id, tenant.id, db) is None  # ya no existe


@pytest.mark.asyncio
async def test_template_crud_via_service(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    tpl = await templates_svc.create_template(
        SimpleNamespace(name="T", subject="S", html_body="<p>b</p>"), tenant.id, db
    )
    assert tpl.id is not None

    upd = await templates_svc.update_template(
        tpl.id, SimpleNamespace(name="T2", subject="S2", html_body="<p>x</p>"), tenant.id, db
    )
    assert upd is not None and upd.name == "T2"

    assert await templates_svc.delete_template(tpl.id, tenant.id, db) is True
    # tras borrar, update devuelve None (no encontrado)
    assert (
        await templates_svc.update_template(
            tpl.id, SimpleNamespace(name="x", subject="x", html_body="x"), tenant.id, db
        )
        is None
    )
