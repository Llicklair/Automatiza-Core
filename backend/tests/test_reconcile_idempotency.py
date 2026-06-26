"""Regresión: conciliar DOS veces la misma transacción no duplica el asiento de cobro.

Fija el guard de idempotencia añadido a reconcile_transaction (service.py): tras
cargar la BankTransaction (con .with_for_update()), si tx.status == "reconciled"
retorna {"message": "La transacción ya estaba conciliada", ...} SIN volver a llamar
_apply_payment_entry. Antes, un doble-clic / reintento sobre la misma tx pasaba el
guard inexistente y reejecutaba la conciliación.

Qué se cuenta: el asiento de cobro lo crea create_invoice_payment_entry como un
JournalEntry con reference_id == f"PAY-INV-{invoice.id}" (cargo 572 Bancos / abono
430 Clientes). El test cuenta esos JournalEntry y exige que siga habiendo UNO tras
la segunda llamada.

No-tautológico: la 2ª llamada SOLO devuelve el mensaje idempotente si el guard de
reconcile_transaction existe; sin él, la 2ª llamada seguiría el camino normal y
devolvería "Conciliado correctamente" → el assert del mensaje rompe.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import BankTransaction, JournalEntry
from app.services.banking.service import reconcile_transaction


async def _count_payment_entries(db, tenant_id, invoice_id) -> int:
    """Asientos de cobro de esta factura (reference_id == PAY-INV-<invoice_id>)."""
    res = await db.execute(
        select(func.count())
        .select_from(JournalEntry)
        .where(
            JournalEntry.tenant_id == tenant_id,
            JournalEntry.reference_id == f"PAY-INV-{invoice_id}",
        )
    )
    return int(res.scalar_one())


@pytest.mark.asyncio
async def test_reconcile_dos_veces_no_duplica_asiento(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user

    client = Client(tenant_id=tenant.id, name="Acme Industrial S.L.", nif="B22222222")
    db.add(client)
    await db.flush()

    invoice = Invoice(
        tenant_id=tenant.id,
        client_id=client.id,
        invoice_number="F-IDEMP-1",
        date=datetime(2026, 5, 10, tzinfo=UTC),
        amount_base=Decimal("100.00"),
        tax_amount=Decimal("21.00"),
        amount_total=Decimal("121.00"),
        invoice_type="issued",
        status="sent",  # conciliable: sent → paid
    )
    tx = BankTransaction(
        tenant_id=tenant.id,
        date=datetime(2026, 5, 12, tzinfo=UTC),
        amount=Decimal("121.00"),
        description="TRF SEPA ACME INDUSTRIAL ref F-IDEMP-1",
        status="unreconciled",
    )
    db.add_all([invoice, tx])
    await db.commit()

    # ── 1ª conciliación: crea exactamente UN asiento de cobro ──────────────────
    res1 = await reconcile_transaction(db, tenant.id, user.id, tx.id, str(invoice.id))
    assert res1["status"] == "ok"
    assert res1["message"] == "Conciliado correctamente"
    assert await _count_payment_entries(db, tenant.id, invoice.id) == 1

    await db.refresh(tx)
    assert tx.status == "reconciled"

    # ── 2ª conciliación (mismos args): guard idempotente, NO un 2º asiento ──────
    res2 = await reconcile_transaction(db, tenant.id, user.id, tx.id, str(invoice.id))

    # Mensaje idempotente: SOLO lo produce el guard de reconcile_transaction.
    assert res2["status"] == "ok"
    assert res2["message"] == "La transacción ya estaba conciliada"

    # Invariante contable: sigue habiendo UN solo asiento de cobro (no 2).
    assert await _count_payment_entries(db, tenant.id, invoice.id) == 1
