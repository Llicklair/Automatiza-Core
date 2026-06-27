"""Guard de `ignore_transaction`: no se puede ignorar una transaccion ya
conciliada (dejaria su asiento contable huerfano)."""
import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.db.models.accounting import BankTransaction
from app.services.banking import service as banking_svc

pytestmark = pytest.mark.asyncio


async def _make_tx(db, tenant_id, *, status="unreconciled"):
    tx = BankTransaction(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        date=date(2026, 1, 15),
        description="Pago cliente",
        amount=100,
        status=status,
    )
    db.add(tx)
    await db.commit()
    return tx.id


async def _status(db, tx_id):
    r = await db.execute(select(BankTransaction).where(BankTransaction.id == tx_id))
    return r.scalar_one().status


async def test_ignore_unreconciled_works(db, seed_tenant_and_user):
    """CONTROL: una transaccion no conciliada SI se puede ignorar."""
    tenant, _, _ = seed_tenant_and_user
    tx_id = await _make_tx(db, tenant.id)
    res = await banking_svc.ignore_transaction(db, tenant.id, tx_id)
    assert res["status"] == "ok"
    assert await _status(db, tx_id) == "ignored"


async def test_ignore_reconciled_raises_no_mutation(db, seed_tenant_and_user):
    """GUARD: ignorar una transaccion conciliada lanza ValueError y NO la muta."""
    tenant, _, _ = seed_tenant_and_user
    tx_id = await _make_tx(db, tenant.id, status="reconciled")
    with pytest.raises(ValueError, match="conciliada"):
        await banking_svc.ignore_transaction(db, tenant.id, tx_id)
    await db.rollback()
    assert await _status(db, tx_id) == "reconciled"
