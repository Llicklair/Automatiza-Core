"""Tests del motor de tesorería (F2.7): cashflow proyectado + SEPA pain.001."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from xml.etree.ElementTree import fromstring

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.treasury.projection import project_cashflow
from app.services.treasury.sepa import (
    DebtorParty,
    Pain001Error,
    TransferOrder,
    build_pain001,
)


_NS = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}


# ─── Cashflow projection (DB) ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_projection_sin_movimientos_da_serie_plana(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    result = await project_cashflow(db, tenant.id, days_ahead=7, today=date(2026, 5, 21))
    assert result["days_ahead"] == 7
    assert len(result["series"]) == 8  # 0..7
    for d in result["series"]:
        assert d["inflow"] == 0
        assert d["outflow"] == 0
    assert result["summary"]["total_in"] == 0
    assert result["summary"]["total_out"] == 0


@pytest.mark.asyncio
async def test_projection_cuenta_cobros_emitidos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B11111111", name="Cliente")
    db.add(cli)
    await db.flush()

    today = date(2026, 5, 21)
    inv = Invoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        invoice_number="F-001",
        date=datetime(2026, 5, 1, tzinfo=UTC),
        due_date=datetime(2026, 5, 25, tzinfo=UTC),
        amount_base=Decimal("1000"),
        tax_amount=Decimal("210"),
        amount_total=Decimal("1210"),
        invoice_type="issued",
        status="sent",
    )
    db.add(inv)
    await db.commit()

    result = await project_cashflow(db, tenant.id, days_ahead=10, today=today)
    target_day = next(d for d in result["series"] if d["date"] == "2026-05-25")
    assert target_day["inflow"] == 1210.0
    assert any(e["kind"] == "invoice_in" for e in target_day["events"])
    assert result["summary"]["total_in"] == 1210.0


@pytest.mark.asyncio
async def test_projection_detecta_tension_liquidez(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B22222222", name="Proveedor")
    db.add(cli)
    await db.flush()

    today = date(2026, 5, 21)
    # Pago grande sin cobros → saldo proyectado negativo
    inv = Invoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        invoice_number="REC-001",
        date=datetime(2026, 5, 1, tzinfo=UTC),
        due_date=datetime(2026, 5, 25, tzinfo=UTC),
        amount_base=Decimal("5000"),
        tax_amount=Decimal("0"),
        amount_total=Decimal("5000"),
        invoice_type="received",
        status="sent",
    )
    db.add(inv)
    await db.commit()

    result = await project_cashflow(db, tenant.id, days_ahead=10, today=today)
    # Sin saldo de partida y con un pago de 5.000 → alerta de déficit
    assert result["alerts"], "Esperaba al menos una alerta de tensión"
    assert result["alerts"][0]["deficit"] >= 4999  # ~ 5000


@pytest.mark.asyncio
async def test_projection_rechaza_horizonte_invalido(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(ValueError):
        await project_cashflow(db, tenant.id, days_ahead=0)
    with pytest.raises(ValueError):
        await project_cashflow(db, tenant.id, days_ahead=999)


# ─── pain.001 — sin DB ────────────────────────────────────────────────


def _basic_debtor() -> DebtorParty:
    return DebtorParty(name="Mi Empresa SL", iban="ES9121000418450200051332")


def _basic_orders(n: int = 1) -> list[TransferOrder]:
    return [
        TransferOrder(
            creditor_name=f"Proveedor {i}",
            creditor_iban="DE89370400440532013000",
            amount_eur=Decimal("100.00"),
            concept=f"Pago factura {i}",
        )
        for i in range(n)
    ]


def test_pain001_xml_estructura_basica():
    today = date.today()
    xml_str, summary = build_pain001(_basic_debtor(), today + timedelta(days=1), _basic_orders(1))

    root = fromstring(xml_str)
    assert root.tag.endswith("Document")
    grp = root.find(".//p:GrpHdr", _NS)
    assert grp is not None
    assert grp.find("p:NbOfTxs", _NS).text == "1"
    assert grp.find("p:CtrlSum", _NS).text == "100.00"
    assert summary["nb_of_txs"] == 1
    assert summary["control_sum_eur"] == 100.0


def test_pain001_dos_transferencias_suma_control_sum():
    xml_str, summary = build_pain001(
        _basic_debtor(), date.today() + timedelta(days=1), _basic_orders(2),
    )
    assert summary["nb_of_txs"] == 2
    assert summary["control_sum_eur"] == 200.0
    root = fromstring(xml_str)
    txs = root.findall(".//p:CdtTrfTxInf", _NS)
    assert len(txs) == 2


def test_pain001_rechaza_iban_invalido():
    bad_order = TransferOrder(
        creditor_name="X",
        creditor_iban="NO_ES_IBAN",
        amount_eur=Decimal("10"),
        concept="x",
    )
    with pytest.raises(Pain001Error):
        build_pain001(_basic_debtor(), date.today() + timedelta(days=1), [bad_order])


def test_pain001_rechaza_importe_no_positivo():
    bad_order = TransferOrder(
        creditor_name="X",
        creditor_iban="DE89370400440532013000",
        amount_eur=Decimal("0"),
        concept="x",
    )
    with pytest.raises(Pain001Error):
        build_pain001(_basic_debtor(), date.today() + timedelta(days=1), [bad_order])


def test_pain001_rechaza_fecha_pasada():
    with pytest.raises(Pain001Error):
        build_pain001(_basic_debtor(), date.today() - timedelta(days=1), _basic_orders(1))


def test_pain001_rechaza_remesa_vacia():
    with pytest.raises(Pain001Error):
        build_pain001(_basic_debtor(), date.today() + timedelta(days=1), [])


def test_pain001_iban_normaliza_espacios_y_mayusculas():
    order = TransferOrder(
        creditor_name="X",
        creditor_iban="de89 3704 0044 0532 0130 00",
        amount_eur=Decimal("50"),
        concept="x",
    )
    _, summary = build_pain001(_basic_debtor(), date.today() + timedelta(days=1), [order])
    assert summary["debtor_iban"] == "ES9121000418450200051332"


def test_pain001_genera_msg_id_unico():
    _, s1 = build_pain001(_basic_debtor(), date.today() + timedelta(days=1), _basic_orders(1))
    _, s2 = build_pain001(_basic_debtor(), date.today() + timedelta(days=1), _basic_orders(1))
    assert s1["msg_id"] != s2["msg_id"]
    assert s1["sha256"] != s2["sha256"]  # CreDtTm + MsgId distintos
