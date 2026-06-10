"""Tests de remesas SEPA persistidas: pain.008 + ciclo de estados."""
from datetime import date, timedelta
from decimal import Decimal
from xml.etree.ElementTree import fromstring

import pytest

from app.services.treasury.remittances import (
    RemittanceError,
    create_direct_debit_remittance,
    create_transfer_remittance,
    get_remittance,
    list_remittances,
    update_remittance_status,
)
from app.services.treasury.sepa import (
    CreditorParty,
    DebtorParty,
    DirectDebitOrder,
    Pain008Error,
    TransferOrder,
    build_pain008,
)

_NS008 = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.008.001.02"}

_IBAN_A = "ES9121000418450200051332"
_IBAN_B = "ES7921000813610123456789"

_TOMORROW = date.today() + timedelta(days=1)


def _creditor() -> CreditorParty:
    return CreditorParty(
        name="Acme SL", iban=_IBAN_A, creditor_id="ES12000B12345678"
    )


def _dd_order(seq: str = "RCUR", amount: str = "100.00") -> DirectDebitOrder:
    return DirectDebitOrder(
        debtor_name="Cliente Uno",
        debtor_iban=_IBAN_B,
        amount_eur=Decimal(amount),
        concept="Cuota mensual",
        mandate_id="MNDT-001",
        mandate_date=date(2025, 1, 15),
        sequence_type=seq,
    )


# ─── build_pain008 (puro) ──────────────────────────────────────────────


def test_pain008_xml_estructura_basica():
    xml_str, summary = build_pain008(_creditor(), _TOMORROW, [_dd_order()])
    root = fromstring(xml_str)
    assert root.tag.endswith("Document")
    grp = root.find(".//p:GrpHdr", _NS008)
    assert grp.find("p:NbOfTxs", _NS008).text == "1"
    pmt = root.find(".//p:PmtInf", _NS008)
    assert pmt.find("p:PmtMtd", _NS008).text == "DD"
    assert pmt.find(".//p:LclInstrm/p:Cd", _NS008).text == "CORE"
    assert pmt.find("p:PmtTpInf/p:SeqTp", _NS008).text == "RCUR"
    tx = pmt.find("p:DrctDbtTxInf", _NS008)
    assert tx.find(".//p:MndtId", _NS008).text == "MNDT-001"
    assert summary["nb_of_txs"] == 1
    assert summary["control_sum_eur"] == 100.0


def test_pain008_agrupa_pmtinf_por_secuencia():
    xml_str, summary = build_pain008(
        _creditor(), _TOMORROW, [_dd_order("FRST"), _dd_order("RCUR"), _dd_order("RCUR")]
    )
    root = fromstring(xml_str)
    pmts = root.findall(".//p:PmtInf", _NS008)
    assert len(pmts) == 2
    seqs = sorted(p.find("p:PmtTpInf/p:SeqTp", _NS008).text for p in pmts)
    assert seqs == ["FRST", "RCUR"]
    assert summary["nb_of_txs"] == 3
    assert summary["control_sum_eur"] == 300.0


def test_pain008_rechaza_secuencia_invalida():
    with pytest.raises(Pain008Error):
        build_pain008(_creditor(), _TOMORROW, [_dd_order("XXXX")])


def test_pain008_rechaza_sin_mandato():
    order = _dd_order()
    order.mandate_id = ""
    with pytest.raises(Pain008Error):
        build_pain008(_creditor(), _TOMORROW, [order])


def test_pain008_rechaza_fecha_pasada():
    with pytest.raises(Pain008Error):
        build_pain008(_creditor(), date.today() - timedelta(days=1), [_dd_order()])


def test_pain008_rechaza_remesa_vacia():
    with pytest.raises(Pain008Error):
        build_pain008(_creditor(), _TOMORROW, [])


# ─── Persistencia y ciclo de estados (DB) ──────────────────────────────


def _transfer_orders() -> list[TransferOrder]:
    return [
        TransferOrder(
            creditor_name="Proveedor SA",
            creditor_iban=_IBAN_B,
            amount_eur=Decimal("250.50"),
            concept="Factura 123",
        )
    ]


@pytest.mark.asyncio
async def test_remesa_pain001_se_persiste(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    rem = await create_transfer_remittance(
        db, tenant.id, debtor, _TOMORROW, _transfer_orders()
    )
    assert rem.status == "generated"
    assert rem.remittance_type == "pain.001"
    assert rem.nb_of_txs == 1
    assert float(rem.total_amount) == 250.50
    assert rem.xml.startswith("<?xml")
    assert len(rem.orders) == 1
    assert rem.orders[0].end_to_end_id  # autogenerado y persistido
    assert rem.orders[0].end_to_end_id in rem.xml

    fetched = await get_remittance(db, tenant.id, rem.id)
    assert fetched is not None and fetched.msg_id == rem.msg_id


@pytest.mark.asyncio
async def test_remesa_pain008_se_persiste_con_mandato(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    rem = await create_direct_debit_remittance(
        db, tenant.id, _creditor(), _TOMORROW, [_dd_order()]
    )
    assert rem.remittance_type == "pain.008"
    assert rem.orders[0].mandate_id == "MNDT-001"
    assert rem.orders[0].sequence_type == "RCUR"


@pytest.mark.asyncio
async def test_ciclo_estados_remesa(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    rem = await create_transfer_remittance(
        db, tenant.id, debtor, _TOMORROW, _transfer_orders()
    )

    rem = await update_remittance_status(db, tenant.id, rem.id, "sent")
    assert rem.status == "sent"

    rem = await update_remittance_status(db, tenant.id, rem.id, "executed")
    assert rem.status == "executed"
    assert rem.executed_at is not None

    rem = await update_remittance_status(db, tenant.id, rem.id, "reconciled")
    assert rem.status == "reconciled"

    # estado final: no admite más transiciones
    with pytest.raises(RemittanceError):
        await update_remittance_status(db, tenant.id, rem.id, "sent")


@pytest.mark.asyncio
async def test_transicion_invalida_rechazada(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    rem = await create_transfer_remittance(
        db, tenant.id, debtor, _TOMORROW, _transfer_orders()
    )
    with pytest.raises(RemittanceError):
        await update_remittance_status(db, tenant.id, rem.id, "reconciled")


@pytest.mark.asyncio
async def test_list_remittances_filtra_por_estado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    r1 = await create_transfer_remittance(
        db, tenant.id, debtor, _TOMORROW, _transfer_orders()
    )
    await create_transfer_remittance(
        db, tenant.id, debtor, _TOMORROW, _transfer_orders()
    )
    await update_remittance_status(db, tenant.id, r1.id, "sent")

    todas, total = await list_remittances(db, tenant.id)
    assert total == 2
    enviadas, total_sent = await list_remittances(db, tenant.id, status="sent")
    assert total_sent == 1 and enviadas[0].id == r1.id
