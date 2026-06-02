"""Caps de aprobación en tools de escritura financiera (#8 consejo 2026-06-02).

Verifican que por encima de APPROVAL_THRESHOLD_EUR la tool devuelve
"APROBACIÓN REQUERIDA" y NO crea/aprueba el registro, y que por debajo opera
con normalidad. Cubre create_journal_entry y approve_payroll.

DB SQLite en memoria vía conftest (FK no se fuerzan, así que las nóminas usan
un employee_id sintético sin sembrar Employee).
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select

from app.agents.accounting.tools import create_journal_entry
from app.agents.hr._payroll_crud import approve_payroll
from app.agents.shared.validators.billing import APPROVAL_THRESHOLD_EUR
from app.db.base import AsyncSessionLocal
from app.db.models.accounting import JournalEntry
from app.db.models.hr import Payroll
from app.db.models.models import Tenant

_OVER = float(APPROVAL_THRESHOLD_EUR) + 1000  # 6000
_UNDER = float(APPROVAL_THRESHOLD_EUR) - 4000  # 1000


async def _seed_tenant() -> str:
    async with AsyncSessionLocal() as db:
        tenant = Tenant(id=uuid4(), name="Caps Test S.L.", nif="B11122233", plan="starter")
        db.add(tenant)
        await db.commit()
        return str(tenant.id)


def _balanced_lines(amount: float) -> list[dict]:
    return [
        {"account_code": "600", "account_name": "Compras", "debit": amount, "credit": 0},
        {"account_code": "400", "account_name": "Proveedores", "debit": 0, "credit": amount},
    ]


async def _count_journal_entries(tenant_id: str) -> int:
    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(func.count()).select_from(JournalEntry).where(
                JournalEntry.tenant_id == UUID(tenant_id)
            )
        )
        return int(res.scalar() or 0)


# ── create_journal_entry ─────────────────────────────────────────────────────


async def test_journal_entry_over_threshold_blocked():
    tenant_id = await _seed_tenant()
    result = await create_journal_entry.ainvoke({
        "tenant_id": tenant_id,
        "description": "Compra material",
        "entry_date": "2026-06-02",
        "lines": _balanced_lines(_OVER),
    })
    assert "APROBACIÓN REQUERIDA" in result
    assert await _count_journal_entries(tenant_id) == 0  # no se creó nada


async def test_journal_entry_under_threshold_created():
    tenant_id = await _seed_tenant()
    result = await create_journal_entry.ainvoke({
        "tenant_id": tenant_id,
        "description": "Compra menor",
        "entry_date": "2026-06-02",
        "lines": _balanced_lines(_UNDER),
    })
    assert "APROBACIÓN REQUERIDA" not in result
    assert "creado correctamente" in result.lower() or "creado" in result.lower()
    assert await _count_journal_entries(tenant_id) == 1


# ── approve_payroll ──────────────────────────────────────────────────────────


async def _seed_payroll(tenant_id: str, net: float, status: str = "draft") -> str:
    now = datetime(2026, 5, 31, tzinfo=UTC)
    async with AsyncSessionLocal() as db:
        p = Payroll(
            id=uuid4(),
            tenant_id=UUID(tenant_id),
            employee_id=uuid4(),  # FK no forzada en SQLite de test
            period_start=datetime(2026, 5, 1, tzinfo=UTC),
            period_end=now,
            issue_date=now,
            base_salary=Decimal(str(net)),
            net_salary=Decimal(str(net)),
            status=status,
        )
        db.add(p)
        await db.commit()
        return str(p.id)


async def _payroll_status(payroll_id: str) -> str:
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(Payroll.status).where(Payroll.id == UUID(payroll_id)))
        return res.scalar_one()


async def test_approve_payroll_over_threshold_blocked():
    tenant_id = await _seed_tenant()
    payroll_id = await _seed_payroll(tenant_id, _OVER)
    result = await approve_payroll.ainvoke({"tenant_id": tenant_id, "payroll_id": payroll_id})
    assert "APROBACIÓN REQUERIDA" in result
    assert await _payroll_status(payroll_id) == "draft"  # sigue sin aprobar


async def test_approve_payroll_under_threshold_ok():
    tenant_id = await _seed_tenant()
    payroll_id = await _seed_payroll(tenant_id, _UNDER)
    result = await approve_payroll.ainvoke({"tenant_id": tenant_id, "payroll_id": payroll_id})
    assert "APROBACIÓN REQUERIDA" not in result
    assert "aprobada" in result.lower()
    assert await _payroll_status(payroll_id) == "approved"
