"""Idempotencia/estado de la conciliación manual (reconcile_transaction).

Cubre el defecto residual L3: una 2ª conciliación de una tx YA conciliada debe
RECHAZARSE (ValueError → 400), sin re-procesar ni re-asociar la tx a otra factura
(que dejaba la 1ª factura "paid" sin transacción vinculada → descuadre silencioso).
El asiento duplicado ya lo frena _has_entry (PAY-INV-{id}); aquí se valida el guard
de estado.

No duplica test_banking_auto_reconcile.py (auto_reconcile + pre-filtro SQL): el
motor automático ya filtra status=="unreconciled" en SQL, así que el guard no le
afecta. Aquí se prueba la ruta MANUAL.

Reutiliza los mismos helpers de seeding que test_banking_auto_reconcile.py.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models.accounting import JournalEntry
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import BankTransaction
from app.services.banking.service import reconcile_transaction


async def _seed_client(db, tenant_id, name="Acme Industrial S.L.") -> Client:
    cli = Client(tenant_id=tenant_id, name=name, nif="B22222222")
    db.add(cli)
    await db.flush()
    return cli


def _invoice(tenant_id, client_id, *, number, total, status="sent", day=10) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, day, tzinfo=UTC),
        amount_base=Decimal(str(round(total / 1.21, 2))),
        tax_amount=Decimal(str(round(total - total / 1.21, 2))),
        amount_total=Decimal(str(total)),
        invoice_type="issued",
        status=status,
    )


def _tx(tenant_id, *, amount, description, status="unreconciled", day=12) -> BankTransaction:
    return BankTransaction(
        tenant_id=tenant_id,
        date=datetime(2026, 5, day, tzinfo=UTC),
        amount=Decimal(str(amount)),
        description=description,
        status=status,
    )


async def _count_entries(db, tenant_id) -> int:
    res = await db.execute(
        select(func.count()).select_from(JournalEntry).where(
            JournalEntry.tenant_id == tenant_id
        )
    )
    return int(res.scalar() or 0)


@pytest.mark.asyncio
async def test_segunda_conciliacion_misma_tx_se_rechaza(db, seed_tenant_and_user):
    """Concilia una tx (éxito); volver a conciliar la MISMA tx → ValueError.
    Verifica que NO se re-procesa: el estado/factura no cambian y no se duplica
    el asiento."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-100", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL F-100")
    db.add_all([inv, tx])
    await db.commit()

    # 1ª conciliación: éxito
    res = await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv.id))
    assert res["status"] == "ok"
    await db.refresh(tx)
    await db.refresh(inv)
    assert tx.status == "reconciled"
    assert tx.invoice_id == inv.id
    assert inv.status == "paid"

    entries_after_first = await _count_entries(db, tenant.id)

    # 2ª conciliación de la MISMA tx → rechazada
    with pytest.raises(ValueError):
        await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv.id))

    await db.refresh(tx)
    assert tx.status == "reconciled"
    assert tx.invoice_id == inv.id
    # No se duplicó el asiento
    assert await _count_entries(db, tenant.id) == entries_after_first


@pytest.mark.asyncio
async def test_segunda_conciliacion_otra_factura_no_reasocia(db, seed_tenant_and_user):
    """El caso peligroso: 2ª llamada con un invoice_id DISTINTO no debe re-asociar
    la tx ya conciliada a otra factura (dejaba la 1ª factura 'paid' huérfana)."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv_a = _invoice(tenant.id, cli.id, number="F-200", total=121.0)
    inv_b = _invoice(tenant.id, cli.id, number="F-201", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL")
    db.add_all([inv_a, inv_b, tx])
    await db.commit()

    await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv_a.id))
    await db.refresh(tx)
    assert tx.invoice_id == inv_a.id

    # 2ª llamada apuntando a OTRA factura → rechazada, sin re-asociar
    with pytest.raises(ValueError):
        await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv_b.id))

    await db.refresh(tx)
    await db.refresh(inv_b)
    assert tx.invoice_id == inv_a.id  # sigue en la 1ª factura
    assert inv_b.status != "paid"     # la 2ª factura no quedó marcada


@pytest.mark.asyncio
async def test_conciliar_tx_no_conciliada_funciona(db, seed_tenant_and_user):
    """CONTROL: conciliar una tx no conciliada sigue funcionando (estado
    conciliada, factura pagada, asiento creado)."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-300", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL F-300")
    db.add_all([inv, tx])
    await db.commit()

    before = await _count_entries(db, tenant.id)
    res = await reconcile_transaction(db, tenant.id, user.id, tx.id, str(inv.id))

    assert res["status"] == "ok"
    await db.refresh(tx)
    await db.refresh(inv)
    assert tx.status == "reconciled"
    assert tx.invoice_id == inv.id
    assert inv.status == "paid"
    # Se creó el asiento de cobro
    assert await _count_entries(db, tenant.id) == before + 1
    assert tx.journal_entry_id is not None
