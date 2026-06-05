"""Migración de movimientos bancarios (carga de extracto histórico).

Importe con signo, movimientos sin conciliar, idempotente por
(fecha, importe, concepto[, saldo]) para no duplicar al recargar el extracto.
"""

from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounting import BankTransaction
from app.db.models.models import Tenant
from app.services.migration.bulk_import import import_bank_transactions_rows


async def _seed(db: AsyncSession):
    tenant = Tenant(id=uuid4(), name="MigBank S.L.", nif="B40404040", plan="starter")
    db.add(tenant)
    await db.flush()
    return tenant


def _row(concepto="Pago proveedor", importe="-150.00", fecha="2026-02-03", saldo="1850.00"):
    return {"fecha": fecha, "concepto": concepto, "importe": importe, "saldo": saldo}


async def _count(db, tenant_id) -> int:
    r = await db.execute(
        select(func.count(BankTransaction.id)).where(BankTransaction.tenant_id == tenant_id)
    )
    return int(r.scalar() or 0)


class TestBankMigration:
    @pytest.mark.asyncio
    async def test_carga_con_signo_y_sin_conciliar(self, db: AsyncSession):
        tenant = await _seed(db)
        res = await import_bank_transactions_rows(
            [_row("Cobro cliente", "300.00"), _row("Pago luz", "-80.00")], tenant.id, db
        )
        assert res.created == 2
        txs = (await db.execute(
            select(BankTransaction).where(BankTransaction.tenant_id == tenant.id)
        )).scalars().all()
        assert {float(t.amount) for t in txs} == {300.0, -80.0}
        assert all(t.status == "unreconciled" for t in txs)

    @pytest.mark.asyncio
    async def test_idempotente_recargar_extracto(self, db: AsyncSession):
        tenant = await _seed(db)
        await import_bank_transactions_rows([_row()], tenant.id, db)
        res2 = await import_bank_transactions_rows([_row()], tenant.id, db)
        assert res2.created == 0
        assert res2.skipped == 1
        assert await _count(db, tenant.id) == 1

    @pytest.mark.asyncio
    async def test_falta_campo_obligatorio_error(self, db: AsyncSession):
        tenant = await _seed(db)
        res = await import_bank_transactions_rows([_row(importe="")], tenant.id, db)
        assert res.created == 0
        assert res.errors
