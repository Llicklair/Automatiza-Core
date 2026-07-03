"""Tests de remesas SEPA persistidas: pain.008 + ciclo de estados."""

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from xml.etree.ElementTree import fromstring

import pytest
from sqlalchemy.exc import IntegrityError

from app.db.models.models import Client, Invoice
from app.db.models.treasury import SepaRemittance, SepaRemittanceOrder

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
    return CreditorParty(name="Acme SL", iban=_IBAN_A, creditor_id="ES12000B12345678")


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
    xml_str, summary = build_pain008(_creditor(), _TOMORROW, [_dd_order("FRST"), _dd_order("RCUR"), _dd_order("RCUR")])
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
    # Referencia UTC, no date.today() local (la validación usa UTC): evita el
    # fallo entre medianoche local y UTC. Ver test_pain001_rechaza_fecha_pasada.
    with pytest.raises(Pain008Error):
        build_pain008(_creditor(), datetime.now(UTC).date() - timedelta(days=1), [_dd_order()])


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
    rem = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())
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
    rem = await create_direct_debit_remittance(db, tenant.id, _creditor(), _TOMORROW, [_dd_order()])
    assert rem.remittance_type == "pain.008"
    assert rem.orders[0].mandate_id == "MNDT-001"
    assert rem.orders[0].sequence_type == "RCUR"


@pytest.mark.asyncio
async def test_ciclo_estados_remesa(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    rem = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())

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
    rem = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())
    with pytest.raises(RemittanceError):
        await update_remittance_status(db, tenant.id, rem.id, "reconciled")


@pytest.mark.asyncio
async def test_list_remittances_filtra_por_estado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    r1 = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())
    await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())
    await update_remittance_status(db, tenant.id, r1.id, "sent")

    todas, total = await list_remittances(db, tenant.id)
    assert total == 2
    enviadas, total_sent = await list_remittances(db, tenant.id, status="sent")
    assert total_sent == 1 and enviadas[0].id == r1.id


# ─── Guarda anti-duplicado (audit 2026-07-02) ──────────────────────────
# Escenario real: el usuario genera la remesa, navega (pierde el feedback
# local) y al volver la vuelve a generar → doble pago/cobro en tránsito.


async def _seed_invoice(db, tenant_id):
    client = Client(id=uuid.uuid4(), tenant_id=tenant_id, name="Cliente Remesa", nif="B11223344")
    db.add(client)
    await db.flush()
    inv = Invoice(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=client.id,
        invoice_number="REM-1",
        date=datetime.now(UTC),
        amount_base=Decimal("100"),
        tax_amount=Decimal("21"),
        amount_total=Decimal("121"),
        status="pending",
        invoice_type="issued",
    )
    db.add(inv)
    await db.flush()
    return inv


@pytest.mark.asyncio
async def test_guard_rechaza_factura_en_dos_remesas_vivas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    inv = await _seed_invoice(db, tenant.id)
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    links = [{"invoice_id": inv.id}]
    await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders(), links=links)
    with pytest.raises(RemittanceError, match="ya está incluida"):
        await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders(), links=links)


@pytest.mark.asyncio
async def test_guard_permite_reintentar_tras_cancelar(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    inv = await _seed_invoice(db, tenant.id)
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    links = [{"invoice_id": inv.id}]
    rem = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders(), links=links)
    await update_remittance_status(db, tenant.id, rem.id, "cancelled")
    rem2 = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders(), links=links)
    assert rem2.status == "generated"


@pytest.mark.asyncio
async def test_cancelled_solo_desde_generated(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    debtor = DebtorParty(name="Acme SL", iban=_IBAN_A)
    rem = await create_transfer_remittance(db, tenant.id, debtor, _TOMORROW, _transfer_orders())
    await update_remittance_status(db, tenant.id, rem.id, "sent")
    with pytest.raises(RemittanceError, match="Transición inválida"):
        await update_remittance_status(db, tenant.id, rem.id, "cancelled")


def _bare_remittance(tenant_id, msg_id: str) -> SepaRemittance:
    """Remesa mínima válida para tests que insertan órdenes directamente."""
    return SepaRemittance(
        tenant_id=tenant_id,
        remittance_type="pain.001",
        msg_id=msg_id,
        status="generated",
        execution_date=_TOMORROW,
        party_iban=_IBAN_A,
        nb_of_txs=1,
        total_amount=Decimal("100.00"),
        xml="<xml/>",
        sha256="0" * 64,
    )


def _bare_order(remittance, invoice_id) -> SepaRemittanceOrder:
    return SepaRemittanceOrder(
        remittance=remittance,
        counterparty_name="X",
        counterparty_iban=_IBAN_B,
        amount=Decimal("100.00"),
        end_to_end_id=f"E2E-{uuid.uuid4().hex[:16].upper()}",
        invoice_id=invoice_id,
    )


@pytest.mark.asyncio
async def test_barrera_bd_rechaza_orden_duplicada_viva(db, seed_tenant_and_user):
    """La BARRERA de BD (índice parcial único), no solo el guard de aplicación:
    dos órdenes vivas con la misma factura chocan al flush → IntegrityError.

    Salta el guard `_assert_links_free` insertando las órdenes directamente,
    como haría una carrera concurrente que pasa el check-then-act a la vez.
    """
    tenant, _u, _t = seed_tenant_and_user
    inv = await _seed_invoice(db, tenant.id)
    db.add(_bare_order(_bare_remittance(tenant.id, "MSG-A"), inv.id))
    await db.flush()
    db.add(_bare_order(_bare_remittance(tenant.id, "MSG-B"), inv.id))
    with pytest.raises(IntegrityError):
        await db.flush()
    await db.rollback()


@pytest.mark.asyncio
async def test_cancelar_marca_ordenes_is_cancelled(db, seed_tenant_and_user):
    """Cancelar la remesa desnormaliza is_cancelled=True en sus órdenes (lo que
    las libera del índice parcial único)."""
    tenant, _u, _t = seed_tenant_and_user
    inv = await _seed_invoice(db, tenant.id)
    rem = await create_transfer_remittance(
        db,
        tenant.id,
        DebtorParty(name="Acme SL", iban=_IBAN_A),
        _TOMORROW,
        _transfer_orders(),
        links=[{"invoice_id": inv.id}],
    )
    assert all(not o.is_cancelled for o in rem.orders)
    await update_remittance_status(db, tenant.id, rem.id, "cancelled")
    from sqlalchemy import select

    orders = (
        (await db.execute(select(SepaRemittanceOrder).where(SepaRemittanceOrder.remittance_id == rem.id)))
        .scalars()
        .all()
    )
    assert orders and all(o.is_cancelled for o in orders)
