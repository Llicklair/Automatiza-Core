"""
Registro de query providers para condiciones de workflow basadas en BD.

Cada provider es una funcion async que recibe (tenant_id, db, params)
y retorna un escalar (int, float, bool). Todos filtran por tenant_id.

Uso:
    from app.services.workflow.db_query_providers import QUERY_PROVIDERS
    fn = QUERY_PROVIDERS["billing.pending_invoice_count"]
    count = await fn(tenant_id, db, {"status": "pending"})
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Employee, Invoice, Payroll

logger = logging.getLogger(__name__)

QueryProvider = Callable[[UUID, AsyncSession, dict], Coroutine[Any, Any, int | float | bool]]


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


async def _billing_invoice_count_by_status(tenant_id: UUID, db: AsyncSession, params: dict) -> int:
    status = params.get("status", "pending")
    result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status == status,
        )
    )
    return result.scalar_one()


async def _billing_unpaid_total(tenant_id: UUID, db: AsyncSession, params: dict) -> float:
    result = await db.execute(
        select(func.coalesce(func.sum(Invoice.amount_total), 0)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status != "paid",
        )
    )
    return float(result.scalar_one())


async def _billing_overdue_count(tenant_id: UUID, db: AsyncSession, params: dict) -> int:
    result = await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.tenant_id == tenant_id,
            Invoice.status != "paid",
            Invoice.due_date < datetime.now(UTC),
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# HR
# ---------------------------------------------------------------------------


async def _hr_payrolls_this_month(tenant_id: UUID, db: AsyncSession, params: dict) -> int:
    now = datetime.now(UTC)
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Payroll.id)).where(
            Payroll.tenant_id == tenant_id,
            Payroll.created_at >= first_of_month,
        )
    )
    return result.scalar_one()


async def _hr_employee_count(tenant_id: UUID, db: AsyncSession, params: dict) -> int:
    result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.tenant_id == tenant_id,
        )
    )
    return result.scalar_one()


async def _hr_draft_payroll_count(tenant_id: UUID, db: AsyncSession, params: dict) -> int:
    result = await db.execute(
        select(func.count(Payroll.id)).where(
            Payroll.tenant_id == tenant_id,
            Payroll.status == "draft",
        )
    )
    return result.scalar_one()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

QUERY_PROVIDERS: dict[str, QueryProvider] = {
    "billing.pending_invoice_count": _billing_invoice_count_by_status,
    "billing.unpaid_total": _billing_unpaid_total,
    "billing.overdue_count": _billing_overdue_count,
    "hr.payrolls_this_month": _hr_payrolls_this_month,
    "hr.employee_count": _hr_employee_count,
    "hr.draft_payroll_count": _hr_draft_payroll_count,
}
