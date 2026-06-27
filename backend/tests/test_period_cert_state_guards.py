"""State-guard and idempotency tests for:

  - reopen_period: only a "closed" period can be reopened (ValueError otherwise).
  - revoke_certificate: idempotent — a 2nd revoke must NOT overwrite revoked_at.

Uses the project's standard SQLite/StaticPool fixture (conftest.py: db, seed_tenant_and_user).
No new dependencies introduced.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounting import AccountingPeriod, TenantCertificate
from app.services.accounting.period_close import reopen_period
from app.services.aeat.certificate_storage import revoke_certificate

# ─── helpers ────────────────────────────────────────────────────────────────

def _make_period(tenant_id, status: str) -> AccountingPeriod:
    """Minimal valid AccountingPeriod. Only status varies."""
    return AccountingPeriod(
        id=uuid4(),
        tenant_id=tenant_id,
        year=2025,
        kind="month",
        period_index=1,
        status=status,
        closed_at=datetime.now(timezone.utc),
    )


def _make_cert(tenant_id, status: str) -> TenantCertificate:
    """Minimal valid TenantCertificate with dummy encrypted blobs."""
    return TenantCertificate(
        id=uuid4(),
        tenant_id=tenant_id,
        label="Test cert",
        encrypted_pfx=b"dummy-pfx-bytes-for-testing-only",
        encrypted_password="dummy-password-token",
        status=status,
        uploaded_at=datetime.now(timezone.utc),
    )


# ─── reopen_period ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reopen_period_happy_path_closed(db: AsyncSession, seed_tenant_and_user):
    """A period with status='closed' is successfully reopened."""
    tenant, user, _ = seed_tenant_and_user

    period = _make_period(tenant.id, status="closed")
    db.add(period)
    await db.commit()

    result = await reopen_period(db, tenant.id, user.id, period.id, reason="Corrección asiento enero")

    assert result.status == "reopened"
    assert result.reopened_at is not None
    assert result.reopened_by_id == user.id
    assert result.reopen_reason == "Corrección asiento enero"


@pytest.mark.asyncio
async def test_reopen_period_guard_open_raises(db: AsyncSession, seed_tenant_and_user):
    """A period with status='open' cannot be reopened — guard raises ValueError."""
    tenant, user, _ = seed_tenant_and_user

    # AccountingPeriod default status in the model is "closed", but we override to "open"
    # to simulate a period that was never closed.
    period = AccountingPeriod(
        id=uuid4(),
        tenant_id=tenant.id,
        year=2025,
        kind="month",
        period_index=2,
        status="open",         # NOT closed — guard should fire
        closed_at=datetime.now(timezone.utc),
    )
    db.add(period)
    await db.commit()

    period_id = period.id  # capture before any rollback

    with pytest.raises(ValueError, match="cerrado"):
        await reopen_period(db, tenant.id, user.id, period_id, reason="motivo cualquiera")

    # After the expected error the session may be in a bad state; rollback so we can re-query.
    await db.rollback()

    from sqlalchemy import select
    res = await db.execute(
        select(AccountingPeriod).where(AccountingPeriod.id == period_id)
    )
    row = res.scalar_one_or_none()
    # Status must be unchanged — guard did not mutate the record.
    assert row is not None
    assert row.status == "open"


@pytest.mark.asyncio
async def test_reopen_period_guard_reopened_raises(db: AsyncSession, seed_tenant_and_user):
    """A period already with status='reopened' cannot be reopened again."""
    tenant, user, _ = seed_tenant_and_user

    period = _make_period(tenant.id, status="reopened")
    db.add(period)
    await db.commit()

    period_id = period.id

    with pytest.raises(ValueError, match="cerrado"):
        await reopen_period(db, tenant.id, user.id, period_id, reason="reabrir de nuevo")

    await db.rollback()

    from sqlalchemy import select
    res = await db.execute(
        select(AccountingPeriod).where(AccountingPeriod.id == period_id)
    )
    row = res.scalar_one_or_none()
    assert row is not None
    assert row.status == "reopened"  # unchanged


# ─── revoke_certificate ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_revoke_certificate_happy_path_active(db: AsyncSession, seed_tenant_and_user):
    """An active cert is revoked: status='revoked' and revoked_at is set."""
    tenant, _, _ = seed_tenant_and_user

    cert = _make_cert(tenant.id, status="active")
    db.add(cert)
    await db.commit()

    result = await revoke_certificate(db, tenant.id, cert.id)

    assert result.status == "revoked"
    assert result.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_certificate_idempotent_preserves_revoked_at(
    db: AsyncSession, seed_tenant_and_user
):
    """Revoking an already-revoked cert must NOT overwrite revoked_at (audit timestamp)."""
    tenant, _, _ = seed_tenant_and_user

    cert = _make_cert(tenant.id, status="active")
    db.add(cert)
    await db.commit()

    # First revocation
    result1 = await revoke_certificate(db, tenant.id, cert.id)
    assert result1.status == "revoked"
    first_revoked_at = result1.revoked_at
    assert first_revoked_at is not None

    # Second revocation — must be a no-op on revoked_at
    result2 = await revoke_certificate(db, tenant.id, cert.id)
    assert result2.status == "revoked"

    # KEY assertion: revoked_at unchanged — the original audit timestamp is preserved.
    assert result2.revoked_at == first_revoked_at, (
        f"revoked_at was overwritten! original={first_revoked_at}, now={result2.revoked_at}"
    )
