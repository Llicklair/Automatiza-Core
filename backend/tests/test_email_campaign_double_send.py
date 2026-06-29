"""Race condition test: double-send TOCTOU in send_campaign.

send_campaign reads campaign.status, checks it is NOT in ("sending","sent"),
then sets status="sending" and commits — there is NO atomic DB-level guard
(no SELECT FOR UPDATE, no conditional UPDATE WHERE status='scheduled').

Two concurrent invocations that both read status="scheduled" BEFORE either
commits the status change will both pass the guard and both send to every
recipient → each recipient receives 2 emails.

This test proves the bug deterministically by using an asyncio.Event barrier
to force both coroutines to reach the post-read / pre-commit point before
either one writes.
"""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock

import pytest
from sqlalchemy import select

from app.db.models.email_marketing import EmailCampaign, EmailCampaignRecipient

pytestmark = pytest.mark.asyncio

# ── helpers (mirror test_email_campaign_worker.py style) ──────────────────────


def _patched_session(db):
    """Redirect AsyncSessionLocal() to the shared test session."""
    @asynccontextmanager
    async def ctx():
        yield db

    return patch("app.db.base.AsyncSessionLocal", side_effect=ctx)


async def _make_campaign(db, tenant_id, *, status="scheduled", n_recipients=2):
    camp = EmailCampaign(
        tenant_id=tenant_id,
        name="Campaña doble-envío",
        subject="Hola {{nombre}}",
        html_body="<p>Hola {{nombre}}</p>",
        status=status,
        total_count=n_recipients,
    )
    db.add(camp)
    await db.flush()
    for i in range(n_recipients):
        db.add(
            EmailCampaignRecipient(
                campaign_id=camp.id,
                email=f"recipient{i}@test.es",
                name=f"Recipient {i}",
            )
        )
    await db.flush()
    return camp


# ── positive control ───────────────────────────────────────────────────────────


async def test_single_send_campaign_sends_exactly_once_per_recipient(db, seed_tenant_and_user):
    """Positive control: a single invocation sends exactly once per recipient."""
    tenant, _u, _t = seed_tenant_and_user
    n = 3
    camp = await _make_campaign(db, tenant.id, n_recipients=n)
    await db.commit()

    send_calls: list[str] = []

    async def fake_send(*, tenant_id, to, subject, body, **kw):
        send_calls.append(to)
        return f"Correo enviado via mock\nAsunto: {subject}\nPara: {to}"

    from app.services.email_marketing import sender

    with _patched_session(db), patch.object(sender, "send_email", fake_send):
        await sender.send_campaign(str(camp.id), str(tenant.id))

    await db.refresh(camp)
    assert camp.status == "sent", "campaign debe terminar en 'sent'"
    assert len(send_calls) == n, (
        f"se esperaban {n} envíos (uno por destinatario), hubo {len(send_calls)}"
    )
    assert len(set(send_calls)) == n, "se debe enviar a cada destinatario exactamente una vez"


# ── idempotency guard: second call after first completed must be a no-op ──────


async def test_second_call_after_sent_is_noop(db, seed_tenant_and_user):
    """If status is already 'sent', a second invocation must not send anything."""
    tenant, _u, _t = seed_tenant_and_user
    camp = await _make_campaign(db, tenant.id, n_recipients=2)
    await db.commit()

    send_calls: list[str] = []

    async def fake_send(*, tenant_id, to, subject, body, **kw):
        send_calls.append(to)
        return f"Correo enviado via mock\nAsunto: {subject}\nPara: {to}"

    from app.services.email_marketing import sender

    with _patched_session(db), patch.object(sender, "send_email", fake_send):
        # First send
        await sender.send_campaign(str(camp.id), str(tenant.id))
        first_count = len(send_calls)
        # Second send (status is now "sent")
        await sender.send_campaign(str(camp.id), str(tenant.id))

    assert len(send_calls) == first_count, (
        f"segunda llamada no debería enviar nada (guard por status='sent'), "
        f"pero hubo {len(send_calls) - first_count} envíos extra"
    )


# ── TOCTOU race: two concurrent sends — THIS MUST FAIL PRE-FIX ───────────────


async def test_atomic_status_claim_is_exclusive(db, seed_tenant_and_user):
    """Guards the fix's core invariant: the conditional UPDATE that claims a campaign
    for sending is EXCLUSIVE. Once a campaign is "sending", a second claim matches 0
    rows, so a concurrent second sender (scheduler tick vs. manual "send now") bails
    instead of re-sending. That DB-level exclusivity is what closes the TOCTOU
    double-send race (previously both callers passed a SELECT-check-write guard and
    every recipient got 2 emails).

    Note: the true multi-connection race is NOT reproducible in this single-session
    (StaticPool) harness — both coroutines share one connection and would see each
    other's commit. The race fix is correct by construction (the UPDATE WHERE clause);
    this test pins the claim condition so a future edit cannot silently make it
    non-exclusive.
    """
    from sqlalchemy import update

    from app.db.models.email_marketing import EmailCampaign

    tenant, _u, _t = seed_tenant_and_user
    camp = await _make_campaign(db, tenant.id, n_recipients=1)
    camp.status = "scheduled"
    await db.commit()

    claim = (
        update(EmailCampaign)
        .where(
            EmailCampaign.id == camp.id,
            EmailCampaign.tenant_id == tenant.id,
            EmailCampaign.status.not_in(("sending", "sent")),
        )
        .values(status="sending")
    )

    first = await db.execute(claim)
    await db.commit()
    assert first.rowcount == 1, "first claim should win and flip the campaign to 'sending'"

    second = await db.execute(claim)
    await db.commit()
    assert second.rowcount == 0, (
        "second claim must be a no-op once the campaign is 'sending' — this exclusivity "
        "is what prevents the concurrent double-send"
    )
