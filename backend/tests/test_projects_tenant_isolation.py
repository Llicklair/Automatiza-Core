"""
IDOR tests — Projects domain cross-tenant isolation.

PRE-FIX expectations (what the bug looks like):
  - test_create_task_cross_tenant_assignee   → FAILS (task committed with B's user as assignee)
  - test_create_project_cross_tenant_client  → FAILS (project committed with B's client)
  - test_create_task_same_tenant_assignee    → PASSES (positive control)
  - test_create_project_same_tenant_client   → PASSES (positive control)

A failing test here = confirmed IDOR bug with repro.
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Client, Project, ProjectTask, Tenant, User
from app.core.security import get_password_hash
from app.services import project_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def two_tenants(db: AsyncSession):
    """
    Returns (tenant_a, user_a, tenant_b, user_b, client_b).

    tenant_a: the attacker.
    tenant_b: the victim — owns user_b and client_b.
    """
    tenant_a = Tenant(id=uuid4(), name="Tenant A", nif="A11111111", plan="starter")
    tenant_b = Tenant(id=uuid4(), name="Tenant B", nif="B22222222", plan="starter")
    db.add(tenant_a)
    db.add(tenant_b)
    await db.flush()

    user_a = User(
        id=uuid4(),
        tenant_id=tenant_a.id,
        email="user_a@tenant-a.com",
        hashed_password=get_password_hash("PassA123!"),
        full_name="User A",
        role="admin",
    )
    user_b = User(
        id=uuid4(),
        tenant_id=tenant_b.id,
        email="user_b@tenant-b.com",
        hashed_password=get_password_hash("PassB123!"),
        full_name="User B",
        role="admin",
    )
    db.add(user_a)
    db.add(user_b)
    await db.flush()

    client_b = Client(
        id=uuid4(),
        tenant_id=tenant_b.id,
        name="Client of B",
        email="client@tenant-b.com",
    )
    db.add(client_b)
    await db.commit()

    return tenant_a, user_a, tenant_b, user_b, client_b


# ---------------------------------------------------------------------------
# Cross-tenant assignee_id — BUG: should raise/reject, currently succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_cross_tenant_assignee(db: AsyncSession, two_tenants):
    """
    Tenant A creates a task assigning tenant B's user as the assignee.

    EXPECTED (correct): raises ValueError / PermissionError / similar.
    PRE-FIX ACTUAL:     succeeds → task row written with assignee_id = B's user.
    A failure here CONFIRMS the IDOR bug in create_task (~line 73-82 of project_service.py).
    """
    tenant_a, user_a, tenant_b, user_b, client_b = two_tenants

    with pytest.raises((ValueError, PermissionError, LookupError)):
        await project_service.create_task(
            db,
            tenant_id=tenant_a.id,
            data={
                "title": "IDOR task",
                "assignee_id": user_b.id,   # B's user — different tenant
            },
        )


# ---------------------------------------------------------------------------
# Cross-tenant client_id — BUG: should raise/reject, currently succeeds
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_project_cross_tenant_client(db: AsyncSession, two_tenants):
    """
    Tenant A creates a project linking tenant B's client.

    EXPECTED (correct): raises ValueError / PermissionError / similar.
    PRE-FIX ACTUAL:     succeeds → project row written with client_id = B's client.
    A failure here CONFIRMS the IDOR bug in create_project (~line 18-23 of project_service.py).
    """
    tenant_a, user_a, tenant_b, user_b, client_b = two_tenants

    with pytest.raises((ValueError, PermissionError, LookupError)):
        await project_service.create_project(
            db,
            tenant_id=tenant_a.id,
            data={
                "name": "IDOR project",
                "client_id": client_b.id,   # B's client — different tenant
            },
        )


# ---------------------------------------------------------------------------
# Cross-tenant assignee via update_task — secondary surface
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_task_cross_tenant_assignee(db: AsyncSession, two_tenants):
    """
    Tenant A creates a task (no assignee), then re-assigns it to tenant B's user via update_task.

    EXPECTED (correct): raises on update.
    PRE-FIX ACTUAL:     update commits the foreign assignee_id silently.
    Bug surface: update_task (~line 85-100 of project_service.py).
    """
    tenant_a, user_a, tenant_b, user_b, client_b = two_tenants

    # First create a legitimate task (no assignee — safe)
    task = await project_service.create_task(
        db,
        tenant_id=tenant_a.id,
        data={"title": "Legitimate task"},
    )

    with pytest.raises((ValueError, PermissionError, LookupError)):
        await project_service.update_task(
            db,
            tenant_id=tenant_a.id,
            task_id=task.id,
            data={"assignee_id": user_b.id},  # B's user — different tenant
        )


# ---------------------------------------------------------------------------
# Positive controls — same-tenant operations MUST succeed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_same_tenant_assignee(db: AsyncSession, two_tenants):
    """
    Positive control: assigning a user from the SAME tenant must succeed.
    If this fails after a fix, the fix is too broad.
    """
    tenant_a, user_a, tenant_b, user_b, client_b = two_tenants

    task = await project_service.create_task(
        db,
        tenant_id=tenant_a.id,
        data={
            "title": "Legitimate assignment",
            "assignee_id": user_a.id,   # SAME tenant — valid
        },
    )
    assert task.assignee_id == user_a.id


@pytest.mark.asyncio
async def test_create_project_same_tenant_client(db: AsyncSession, two_tenants):
    """
    Positive control: linking a client from the SAME tenant must succeed.
    """
    tenant_a, user_a, tenant_b, user_b, client_b = two_tenants

    # Create a client owned by tenant_a
    client_a = Client(
        id=uuid4(),
        tenant_id=tenant_a.id,
        name="Client of A",
        email="client@tenant-a.com",
    )
    db.add(client_a)
    await db.commit()

    project = await project_service.create_project(
        db,
        tenant_id=tenant_a.id,
        data={
            "name": "Legit project",
            "client_id": client_a.id,   # SAME tenant — valid
        },
    )
    assert project.client_id == client_a.id
