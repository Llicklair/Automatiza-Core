"""Tests para la maquina de estados de Expense (commands.py).

Cubre los guards introducidos en la correccion:
  pending → approved → reimbursed  (happy path)
  pending → rejected               (happy path)
  INVALIDO: reimburse desde pending o rejected
  INVALIDO: transiciones desde estados terminales (idempotencia / estado final)
"""
from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Employee, Tenant
from app.services.hr.commands import (
    approve_expense,
    create_expense,
    reimburse_expense,
    reject_expense,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_tenant_and_employee(db: AsyncSession):
    tenant = Tenant(id=uuid4(), name="Test S.L.", nif="B99999999", plan="starter")
    db.add(tenant)
    await db.flush()

    emp = Employee(
        id=uuid4(),
        tenant_id=tenant.id,
        name="Ana López",
        nif="12345678Z",
        email="ana@test.com",
        base_salary=2000.0,
    )
    db.add(emp)
    await db.flush()
    return tenant, emp


async def _make_expense(db, tenant_id, employee_id, amount=100.0):
    return await create_expense(
        db=db,
        tenant_id=tenant_id,
        employee_id=employee_id,
        amount=amount,
        category="viaje",
        description="Desplazamiento cliente",
        date=date(2024, 6, 15),
    )


# ---------------------------------------------------------------------------
# 1. Happy path: ciclo completo pending → approved → reimbursed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_forward_lifecycle(db: AsyncSession):
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    assert exp.status == "pending"

    approved = await approve_expense(db, tenant.id, exp.id)
    assert approved.status == "approved"

    reimbursed = await reimburse_expense(db, tenant.id, exp.id)
    assert reimbursed.status == "reimbursed"


# ---------------------------------------------------------------------------
# 2. Happy path: pending → rejected
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_pending_expense(db: AsyncSession):
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    assert exp.status == "pending"

    rejected = await reject_expense(db, tenant.id, exp.id)
    assert rejected.status == "rejected"


# ---------------------------------------------------------------------------
# 3. CORE FIX — reimbursar sin aprobar previamente debe fallar
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reimburse_pending_raises(db: AsyncSession):
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)

    with pytest.raises(ValueError, match="aprobado"):
        await reimburse_expense(db, tenant.id, exp.id)

    # El estado no debe haber cambiado
    await db.refresh(exp)
    assert exp.status == "pending"


@pytest.mark.asyncio
async def test_reimburse_rejected_raises(db: AsyncSession):
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    await reject_expense(db, tenant.id, exp.id)

    with pytest.raises(ValueError, match="aprobado"):
        await reimburse_expense(db, tenant.id, exp.id)

    await db.refresh(exp)
    assert exp.status == "rejected"


# ---------------------------------------------------------------------------
# 4. Idempotencia / estados terminales — toda transicion no valida raise
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_double_approve_raises(db: AsyncSession):
    """Aprobar un gasto ya aprobado debe fallar (idempotencia — no re-abre)."""
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    await approve_expense(db, tenant.id, exp.id)

    with pytest.raises(ValueError, match="pendiente"):
        await approve_expense(db, tenant.id, exp.id)

    await db.refresh(exp)
    assert exp.status == "approved"


@pytest.mark.asyncio
async def test_double_reimburse_raises(db: AsyncSession):
    """Reembolsar un gasto ya reembolsado debe fallar."""
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    await approve_expense(db, tenant.id, exp.id)
    await reimburse_expense(db, tenant.id, exp.id)

    with pytest.raises(ValueError, match="aprobado"):
        await reimburse_expense(db, tenant.id, exp.id)

    await db.refresh(exp)
    assert exp.status == "reimbursed"


@pytest.mark.asyncio
async def test_approve_rejected_raises(db: AsyncSession):
    """No se puede re-aprobar un gasto rechazado (estado terminal)."""
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    await reject_expense(db, tenant.id, exp.id)

    with pytest.raises(ValueError, match="pendiente"):
        await approve_expense(db, tenant.id, exp.id)

    await db.refresh(exp)
    assert exp.status == "rejected"


@pytest.mark.asyncio
async def test_reject_approved_raises(db: AsyncSession):
    """No se puede rechazar un gasto ya aprobado (evita anular algo listo para pago)."""
    tenant, emp = await _seed_tenant_and_employee(db)
    exp = await _make_expense(db, tenant.id, emp.id)
    await approve_expense(db, tenant.id, exp.id)

    with pytest.raises(ValueError, match="pendiente"):
        await reject_expense(db, tenant.id, exp.id)

    await db.refresh(exp)
    assert exp.status == "approved"
