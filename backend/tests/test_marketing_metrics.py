"""Tests para la analítica de marketing — scheduled_post_metrics (5.1)."""
from datetime import date
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select


def _social_account(tenant_id, platform="twitter"):
    from app.db.models.marketing import SocialAccount

    return SocialAccount(
        id=uuid4(), tenant_id=tenant_id, platform=platform,
        account_id="acc-1", account_name="@test",
    )


def _post(tenant_id, account_id, campaign_id=None, status="published"):
    from app.db.models.marketing import ScheduledPost

    return ScheduledPost(
        id=uuid4(), tenant_id=tenant_id, social_account_id=account_id,
        campaign_id=campaign_id, platform="twitter", content="hola",
        status=status, platform_post_id="tw-123",
    )


@pytest.mark.asyncio
class TestMarketingMetrics:
    async def test_upsert_is_idempotent_per_day(self, db, seed_tenant_and_user):
        from app.db.models.marketing import ScheduledPostMetrics
        from app.services.marketing.metrics import _upsert_metrics

        tenant, _u, _t = seed_tenant_and_user
        acc = _social_account(tenant.id)
        db.add(acc)
        await db.flush()
        post = _post(tenant.id, acc.id)
        db.add(post)
        await db.flush()

        day = date(2026, 6, 11)
        await _upsert_metrics(db, post, {"impressions": 100, "likes": 5}, day)
        await _upsert_metrics(db, post, {"impressions": 150, "likes": 9, "reach": 200}, day)
        await db.commit()

        rows = (
            await db.execute(
                select(ScheduledPostMetrics).where(
                    ScheduledPostMetrics.scheduled_post_id == post.id
                )
            )
        ).scalars().all()
        assert len(rows) == 1  # upsert sobre el mismo día, no duplica
        assert rows[0].impressions == 150
        assert rows[0].likes == 9
        assert rows[0].reach == 200

    async def test_get_campaign_metrics_aggregates_latest(self, db, seed_tenant_and_user):
        from app.db.models.marketing import Campaign, ScheduledPostMetrics
        from app.services.marketing.metrics import get_campaign_metrics

        tenant, _u, _t = seed_tenant_and_user
        acc = _social_account(tenant.id)
        db.add(acc)
        await db.flush()
        campaign = Campaign(id=uuid4(), tenant_id=tenant.id, name="Camp")
        db.add(campaign)
        await db.flush()
        p1 = _post(tenant.id, acc.id, campaign_id=campaign.id)
        p2 = _post(tenant.id, acc.id, campaign_id=campaign.id)
        db.add_all([p1, p2])
        await db.flush()
        # p1 con dos snapshots — debe contar el más reciente (10-jun: 100; 11-jun: 130)
        db.add_all([
            ScheduledPostMetrics(id=uuid4(), tenant_id=tenant.id, scheduled_post_id=p1.id,
                                 metric_date=date(2026, 6, 10), impressions=100, likes=3),
            ScheduledPostMetrics(id=uuid4(), tenant_id=tenant.id, scheduled_post_id=p1.id,
                                 metric_date=date(2026, 6, 11), impressions=130, likes=7),
            ScheduledPostMetrics(id=uuid4(), tenant_id=tenant.id, scheduled_post_id=p2.id,
                                 metric_date=date(2026, 6, 11), impressions=50, likes=2),
        ])
        await db.commit()

        result = await get_campaign_metrics(db, tenant.id, campaign.id)
        assert result["num_posts"] == 2
        assert result["totals"]["impressions"] == 180  # 130 (último de p1) + 50
        assert result["totals"]["likes"] == 9  # 7 + 2

    async def test_endpoint_unknown_campaign_404(self, auth_client: AsyncClient):
        resp = await auth_client.get(f"/api/v1/marketing/campaigns/{uuid4()}/metrics")
        assert resp.status_code == 404

    async def test_endpoint_returns_totals(self, db, auth_client, seed_tenant_and_user):
        from app.db.models.marketing import Campaign, ScheduledPostMetrics

        tenant, _u, _t = seed_tenant_and_user
        acc = _social_account(tenant.id)
        db.add(acc)
        await db.flush()
        campaign = Campaign(id=uuid4(), tenant_id=tenant.id, name="Camp")
        db.add(campaign)
        await db.flush()
        post = _post(tenant.id, acc.id, campaign_id=campaign.id)
        db.add(post)
        await db.flush()
        db.add(
            ScheduledPostMetrics(
                id=uuid4(), tenant_id=tenant.id, scheduled_post_id=post.id,
                metric_date=date(2026, 6, 11), impressions=42, likes=4,
            )
        )
        await db.commit()

        resp = await auth_client.get(
            f"/api/v1/marketing/campaigns/{campaign.id}/metrics"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["num_posts"] == 1
        assert body["totals"]["impressions"] == 42
        assert len(body["posts"]) == 1
