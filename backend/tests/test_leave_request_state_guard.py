"""Tests for the state-machine guard on approve/reject leave requests.

Covers four scenarios:
1. Happy path: approve a pending request -> req.status=="approved", emp.status=="leave"
2. Double-approve: approve -> approve again -> ValueError
3. Orphan prevention: approve -> reject -> ValueError; emp.status still "leave" (no orphan)
4. Reject happy path + double-reject: reject pending -> rejected; reject again -> ValueError
"""
import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hr import LeaveRequest
from app.db.models.models import Employee, Tenant
from app.services.hr.commands import approve_leave_request, reject_leave_request

# ── Helpers ───────────────────────────────────────────────────────────────────

def _today() -> datetime.date:
    return datetime.date.today()


def _next_week() -> datetime.date:
    return _today() + datetime.timedelta(days=7)


async def _make_tenant(db: AsyncSession) -> Tenant:
    t = Tenant(id=uuid4(), name="Test S.L.", nif="B00000001", plan="starter")
    db.add(t)
    await db.flush()
    return t


async def _make_employee(db: AsyncSession, tenant_id) -> Employee:
    emp = Employee(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Empleado Test",
        status="active",
    )
    db.add(emp)
    await db.flush()
    return emp


async def _make_leave_request(db: AsyncSession, tenant_id, employee_id) -> LeaveRequest:
    req = LeaveRequest(
        id=uuid4(),
        tenant_id=tenant_id,
        employee_id=employee_id,
        leave_type="vacaciones",
        start_date=_today(),
        end_date=_next_week(),
        status="pending",
    )
    db.add(req)
    await db.commit()
    return req


# ── Tests ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_approve_pending_sets_approved_and_employee_leave(db: AsyncSession):
    """Happy path: approve a pending request -> req approved, emp.status == 'leave'."""
    tenant = await _make_tenant(db)
    emp = await _make_employee(db, tenant.id)
    req = await _make_leave_request(db, tenant.id, emp.id)

    result = await approve_leave_request(db, tenant.id, req.id)

    assert result.status == "approved"
    await db.refresh(emp)
    assert emp.status == "leave"
    assert emp.leave_type == "vacaciones"
    assert emp.leave_start == req.start_date
    assert emp.leave_end == req.end_date


@pytest.mark.asyncio
async def test_double_approve_raises_value_error(db: AsyncSession):
    """Idempotency: approve twice raises ValueError mentioning 'aprobar' or 'ya está'."""
    tenant = await _make_tenant(db)
    emp = await _make_employee(db, tenant.id)
    req = await _make_leave_request(db, tenant.id, emp.id)

    await approve_leave_request(db, tenant.id, req.id)

    with pytest.raises(ValueError, match=r"ya está|aprobar"):
        await approve_leave_request(db, tenant.id, req.id)


@pytest.mark.asyncio
async def test_approve_then_reject_blocked_no_orphan(db: AsyncSession):
    """Orphan-prevention: approve -> reject blocked; emp.status stays 'leave', req stays 'approved'."""
    tenant = await _make_tenant(db)
    emp = await _make_employee(db, tenant.id)
    req = await _make_leave_request(db, tenant.id, emp.id)

    await approve_leave_request(db, tenant.id, req.id)

    # Capture IDs before the expected exception (guard fires before any DB write,
    # so no partial mutation to roll back — session stays clean after the raise).
    req_id = req.id
    emp_id = emp.id

    # Reject must be blocked for an already-approved request
    with pytest.raises(ValueError, match=r"ya está|rechazar"):
        await reject_leave_request(db, tenant.id, req.id)

    # The guard raises before touching the DB, so the session is still usable.
    # Re-fetch both rows to confirm no orphan was created.
    req_row = (
        await db.execute(
            sa_select(LeaveRequest).where(LeaveRequest.id == req_id)
        )
    ).scalar_one()
    emp_row = (
        await db.execute(
            sa_select(Employee).where(Employee.id == emp_id)
        )
    ).scalar_one()

    assert req_row.status == "approved", (
        f"Expected req.status='approved' after blocked reject, got '{req_row.status}'"
    )
    assert emp_row.status == "leave", (
        f"Orphan detected: emp.status='{emp_row.status}' instead of 'leave' "
        "after the reject was blocked — the guard failed to prevent the orphan."
    )


@pytest.mark.asyncio
async def test_reject_pending_and_double_reject_raises(db: AsyncSession):
    """Reject happy path: pending -> rejected; double reject -> ValueError."""
    tenant = await _make_tenant(db)
    emp = await _make_employee(db, tenant.id)
    req = await _make_leave_request(db, tenant.id, emp.id)

    result = await reject_leave_request(db, tenant.id, req.id)

    assert result.status == "rejected"
    # Employee status should remain unaffected (still active)
    await db.refresh(emp)
    assert emp.status == "active"

    # Double reject
    with pytest.raises(ValueError, match=r"ya está|rechazar"):
        await reject_leave_request(db, tenant.id, req.id)
