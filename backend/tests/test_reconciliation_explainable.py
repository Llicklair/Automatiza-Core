"""Tests del scoring explicable de conciliación + rechazo persistente (F2.6)."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import BankTransaction
from app.services.banking.service import (
    _explain_match,
    _normalize_client_name,
    get_reconciliation_suggestions,
    reject_reconciliation_suggestion,
)


# ─── _normalize_client_name ────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Acme Industrial S.L.", "acme industrial"),
        ("Construcciones López SA", "construcciones lópez"),
        ("Talleres SLU", "talleres"),
        ("Servicios", "servicios"),
        ("", ""),
    ],
)
def test_normalize_client_name(raw, expected):
    assert _normalize_client_name(raw) == expected


# ─── _explain_match ────────────────────────────────────────────────────


def _make_pair(*, days_diff: int, description: str, client_name: str, invoice_number: str = "F-001"):
    tx_date = datetime(2026, 5, 10, tzinfo=UTC)
    inv_date = tx_date - timedelta(days=days_diff)
    tx = SimpleNamespace(
        id="tx", amount=Decimal("121"), date=tx_date, description=description
    )
    inv = SimpleNamespace(
        id="inv",
        amount_total=Decimal("121"),
        date=inv_date,
        invoice_number=invoice_number,
        client=SimpleNamespace(name=client_name),
    )
    return tx, inv


def test_explain_match_solo_importe():
    tx, inv = _make_pair(days_diff=100, description="movimiento desconocido", client_name="Cliente XYZ")
    score, reasons = _explain_match(tx, inv, 121.0)
    codes = {r["code"] for r in reasons}
    assert codes == {"amount_exact"}
    assert score == 50


def test_explain_match_importe_y_fecha_proxima():
    tx, inv = _make_pair(days_diff=5, description="movimiento desconocido", client_name="Cliente XYZ")
    score, reasons = _explain_match(tx, inv, 121.0)
    codes = {r["code"] for r in reasons}
    assert codes == {"amount_exact", "date_within_15d"}
    assert score == 80


def test_explain_match_cliente_completo_en_concepto():
    tx, inv = _make_pair(
        days_diff=5,
        description="TRF SEPA - ACME INDUSTRIAL ref F-001",
        client_name="Acme Industrial S.L.",
        invoice_number="F-001",
    )
    score, reasons = _explain_match(tx, inv, 121.0)
    codes = {r["code"] for r in reasons}
    assert "client_name_match" in codes
    assert "invoice_number_match" in codes
    assert score == 100  # 50 + 30 + 30 + 20 = 130 → cap 100


def test_explain_match_cliente_por_token_largo():
    tx, inv = _make_pair(
        days_diff=20,
        description="cobro CONSTRUCCIONES varios",
        client_name="Construcciones Lopez SA",
    )
    score, reasons = _explain_match(tx, inv, 121.0)
    codes = {r["code"] for r in reasons}
    # Días=20 → date_within_45d (no within_15d)
    assert "date_within_45d" in codes
    assert "client_token_match" in codes
    # No coincide nombre completo normalizado ("construcciones lopez") en concepto
    assert "client_name_match" not in codes


def test_explain_match_normaliza_suffix_legal():
    """Acme Industrial S.L. → 'acme industrial', encuentra 'acme industrial' en concepto."""
    tx, inv = _make_pair(
        days_diff=5,
        description="pago acme industrial mayo",
        client_name="Acme Industrial S.L.",
    )
    _, reasons = _explain_match(tx, inv, 121.0)
    codes = {r["code"] for r in reasons}
    assert "client_name_match" in codes


# ─── Rechazo persistente con DB ────────────────────────────────────────


@pytest.mark.asyncio
async def test_rechazo_oculta_par_de_sugerencias(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B11111111", name="Cliente")
    db.add(cli)
    await db.flush()

    inv = Invoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        invoice_number="F-100",
        date=datetime(2026, 5, 10, tzinfo=UTC),
        amount_base=Decimal("100"),
        tax_amount=Decimal("21"),
        amount_total=Decimal("121"),
        invoice_type="issued",
        status="sent",
    )
    tx = BankTransaction(
        tenant_id=tenant.id,
        date=datetime(2026, 5, 12, tzinfo=UTC),
        amount=Decimal("121"),
        description="TRF SEPA Cliente F-100",
        status="unreconciled",
    )
    db.add_all([inv, tx])
    await db.commit()

    sugg = await get_reconciliation_suggestions(db, tenant.id)
    assert sugg, "Esperaba al menos una transacción con sugerencias"
    target = next((s for s in sugg if s["tx"]["id"] == str(tx.id)), None)
    assert target and target["suggestions"], "La sugerencia para esta tx debería aparecer"

    # Rechazar el par
    result = await reject_reconciliation_suggestion(db, tenant.id, tx.id, inv.id, reason="no es")
    assert result["rejected"] is True
    assert result["new"] is True

    # Ya no debe aparecer
    sugg2 = await get_reconciliation_suggestions(db, tenant.id)
    target2 = next((s for s in sugg2 if s["tx"]["id"] == str(tx.id)), None)
    assert target2 is not None
    assert target2["suggestions"] == []


@pytest.mark.asyncio
async def test_rechazo_idempotente(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B11111111", name="X")
    db.add(cli)
    await db.flush()
    inv = Invoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        invoice_number="F-1",
        date=datetime(2026, 5, 1, tzinfo=UTC),
        amount_base=Decimal("10"), tax_amount=Decimal("0"), amount_total=Decimal("10"),
        invoice_type="issued", status="sent",
    )
    tx = BankTransaction(
        tenant_id=tenant.id,
        date=datetime(2026, 5, 2, tzinfo=UTC),
        amount=Decimal("10"), description="x", status="unreconciled",
    )
    db.add_all([inv, tx])
    await db.commit()

    r1 = await reject_reconciliation_suggestion(db, tenant.id, tx.id, inv.id)
    r2 = await reject_reconciliation_suggestion(db, tenant.id, tx.id, inv.id, reason="otra vez")
    assert r1["new"] is True
    assert r2["new"] is False
