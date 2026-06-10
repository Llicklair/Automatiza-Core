"""Tests de auto_reconcile y del pre-filtro SQL de get_reconciliation_suggestions.

NO duplica tests/test_reconciliation_explainable.py (scoring _explain_match,
_normalize_client_name, rechazo persistente sobre get_reconciliation_suggestions).

Aquí se cubre:
  - auto_reconcile concilia un match claro (candidato único por importe).
  - auto_reconcile NO concilia una tx ambigua (2 facturas candidatas empatadas).
  - auto_reconcile respeta los pares rechazados (_load_rejected_pairs).
  - Pre-filtro SQL por rango min-max de importes (H10): con txs de 100 y 500,
    la factura de 500 sigue siendo candidata de su tx y la de 9999 no se carga.
  - Sin txs sin conciliar → [] (guarda contra min()/max() de secuencia vacía).
  - GAP (xfail): auto_reconcile nunca marca la factura como pagada porque usa
    estados "sent"/"draft" que no existen en la máquina de estados de Invoice.
"""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import BankTransaction
from app.services.banking.service import (
    auto_reconcile,
    get_reconciliation_suggestions,
    reject_reconciliation_suggestion,
)


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


# ─── auto_reconcile ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_auto_reconcile_concilia_match_claro(db, seed_tenant_and_user):
    """Importe exacto + cliente en el concepto + candidato único → se concilia."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-100", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL ref F-100")
    db.add_all([inv, tx])
    await db.commit()

    res = await auto_reconcile(db, tenant.id, user.id)

    assert res["matched"] == 1
    assert res["total"] == 1
    await db.refresh(tx)
    assert tx.status == "reconciled"
    assert tx.invoice_id == inv.id


@pytest.mark.asyncio
async def test_auto_reconcile_ambigua_no_concilia(db, seed_tenant_and_user):
    """Dos facturas con el mismo importe y señales idénticas (empate de score)
    → no hay ganador claro y la tx queda sin conciliar."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id, name="Cliente Genérico S.L.")
    inv_a = _invoice(tenant.id, cli.id, number="F-200", total=121.0)
    inv_b = _invoice(tenant.id, cli.id, number="F-201", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="transferencia recibida")
    db.add_all([inv_a, inv_b, tx])
    await db.commit()

    res = await auto_reconcile(db, tenant.id, user.id)

    assert res["matched"] == 0
    await db.refresh(tx)
    assert tx.status == "unreconciled"
    assert tx.invoice_id is None


@pytest.mark.asyncio
async def test_auto_reconcile_respeta_pares_rechazados(db, seed_tenant_and_user):
    """Un par (tx, invoice) rechazado por el usuario no se auto-concilia aunque
    sea candidato único."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-300", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL ref F-300")
    db.add_all([inv, tx])
    await db.commit()

    await reject_reconciliation_suggestion(db, tenant.id, tx.id, inv.id, reason="no es")

    res = await auto_reconcile(db, tenant.id, user.id)

    assert res["matched"] == 0
    await db.refresh(tx)
    assert tx.status == "unreconciled"


@pytest.mark.asyncio
@pytest.mark.xfail(
    reason="GAP: auto_reconcile busca facturas con status in ('sent','draft') pero la "
    "máquina de estados de Invoice solo define draft→issued→paid: "
    "can_transition('Invoice','sent','paid') y ('draft','paid') son False, así que la "
    "factura ganadora NUNCA pasa a 'paid' (la tx sí queda 'reconciled'). Desajuste de "
    "vocabulario de estados entre banking/service.py y state_machine.py. Documentado.",
    strict=True,
)
async def test_auto_reconcile_marca_factura_pagada(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-400", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="TRF SEPA ACME INDUSTRIAL ref F-400")
    db.add_all([inv, tx])
    await db.commit()

    res = await auto_reconcile(db, tenant.id, user.id)
    assert res["matched"] == 1

    await db.refresh(inv)
    assert inv.status == "paid"


# ─── get_reconciliation_suggestions: pre-filtro SQL (H10) ─────────────────────


@pytest.mark.asyncio
async def test_prefiltro_sql_rango_min_max(db, seed_tenant_and_user):
    """Con txs de 100 y 500: la factura de 500 sigue siendo candidata de la tx
    de 500 (el rango min-max no la excluye) y la de 9999 no se carga nunca."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv_500 = _invoice(tenant.id, cli.id, number="F-500", total=500.0)
    inv_9999 = _invoice(tenant.id, cli.id, number="F-9999", total=9999.0)
    tx_100 = _tx(tenant.id, amount=100.0, description="recibo varios")
    tx_500 = _tx(tenant.id, amount=500.0, description="TRF ACME INDUSTRIAL F-500")
    db.add_all([inv_500, inv_9999, tx_100, tx_500])
    await db.commit()

    out = await get_reconciliation_suggestions(db, tenant.id)

    by_tx = {o["tx"]["id"]: o["suggestions"] for o in out}
    assert set(by_tx) == {str(tx_100.id), str(tx_500.id)}

    # La factura de 500 aparece como candidata de la tx de 500
    sugg_500 = by_tx[str(tx_500.id)]
    assert [s["invoice_number"] for s in sugg_500] == ["F-500"]

    # La tx de 100 no tiene candidatas (la de 500 difiere >0.02)
    assert by_tx[str(tx_100.id)] == []

    # La factura de 9999 no aparece en ninguna sugerencia (pre-filtro SQL)
    all_numbers = {s["invoice_number"] for sugg in by_tx.values() for s in sugg}
    assert "F-9999" not in all_numbers


@pytest.mark.asyncio
async def test_suggestions_sin_txs_devuelve_vacio(db, seed_tenant_and_user):
    """Sin txs unreconciled devuelve [] sin tocar min()/max() (secuencia vacía)."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-600", total=121.0)
    tx = _tx(tenant.id, amount=121.0, description="ya conciliada", status="reconciled")
    db.add_all([inv, tx])
    await db.commit()

    assert await get_reconciliation_suggestions(db, tenant.id) == []
