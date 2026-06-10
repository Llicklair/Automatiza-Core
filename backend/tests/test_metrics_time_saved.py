"""Métrica de tiempo ahorrado: cálculo desde AuditLog y endpoint."""

import pytest

from app.services.audit import log_action
from app.services.metrics.time_saved import MINUTES_BY_ACTION, time_saved_summary

pytestmark = pytest.mark.asyncio


async def test_time_saved_cuenta_solo_success(db, seed_tenant_and_user):
    tenant, _user, _token = seed_tenant_and_user
    for status in ("success", "success", "error"):
        await log_action(
            db, tenant_id=tenant.id, agent_name="billing",
            action_type="create_invoice", status=status,
        )
    await db.commit()

    summary = await time_saved_summary(db, tenant.id, days=30)
    assert summary["total_actions"] == 2
    assert summary["total_minutes"] == 2 * MINUTES_BY_ACTION["create_invoice"]
    assert summary["breakdown"][0]["action_type"] == "create_invoice"


async def test_time_saved_excluye_fontaneria(db, seed_tenant_and_user):
    tenant, _user, _token = seed_tenant_and_user
    await log_action(
        db, tenant_id=tenant.id, agent_name="system",
        action_type="user_registered", status="success",
    )
    await db.commit()
    summary = await time_saved_summary(db, tenant.id, days=30)
    assert summary["total_actions"] == 0
    assert summary["total_minutes"] == 0


async def test_endpoint_time_saved(auth_client):
    resp = await auth_client.get("/api/v1/metrics/time-saved?days=7")
    assert resp.status_code == 200
    data = resp.json()
    assert {"days", "total_actions", "total_minutes", "total_hours", "breakdown"} <= data.keys()
    assert data["days"] == 7
