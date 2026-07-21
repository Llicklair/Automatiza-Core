"""Regresión de la barrera fiscal del agente de facturación (B2 / B11, 2026-06-25).

- B2: el agente NO puede cambiar base/IVA de una factura que ya tiene registro
  VeriFactu (cadena inmutable, RD 1007/2023) → debe exigir una rectificativa.
  Cuando NO hay registro, recalcula los importes con Decimal vía
  `compute_invoice_totals` (sin arrastre de redondeo del float).
- B11: las transiciones de estado del agente usan la máquina de estado canónica
  (services/state_machine), que prohíbe cancelar una factura pagada y admite
  el estado 'sent' que la tabla duplicada del agente ignoraba.
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.agents.billing._invoice_write_tools import (
    _update_invoice_async,
    _update_invoice_status_async,
)
from app.db.models.billing import Invoice, VerifactuRecord
from app.db.models.crm import Client


async def _seed_client(db, tenant_id) -> Client:
    cli = Client(tenant_id=tenant_id, name="Acme Industrial S.L.", nif="B22222222")
    db.add(cli)
    await db.flush()
    return cli


def _invoice(tenant_id, client_id, *, number, base, tax, total, status="draft") -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 10, tzinfo=UTC),
        amount_base=Decimal(str(base)),
        tax_amount=Decimal(str(tax)),
        amount_total=Decimal(str(total)),
        invoice_type="issued",
        status=status,
    )


def _verifactu_record(tenant_id, invoice_id) -> VerifactuRecord:
    return VerifactuRecord(
        tenant_id=tenant_id,
        invoice_id=invoice_id,
        huella="A" * 64,
        huella_anterior=None,
        payload_canonico="num=F-VF&importe=121.00",
        nif_emisor="B00000000",
        serie_factura="F",
        numero_factura="F-VF",
        fecha_emision=datetime(2026, 5, 10, tzinfo=UTC),
        importe_total=Decimal("121.00"),
    )


async def _reload(db, invoice_id) -> Invoice:
    db.expire_all()
    return (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one()


# ─── B2: barrera VeriFactu sobre importes ─────────────────────────────────────


@pytest.mark.asyncio
async def test_agente_no_edita_importes_con_registro_verifactu(db, seed_tenant_and_user):
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-VF", base="100.00", tax="21.00", total="121.00")
    db.add(inv)
    await db.flush()
    db.add(_verifactu_record(tenant.id, inv.id))
    await db.commit()

    res = await _update_invoice_async(
        str(tenant.id), str(inv.id), concept="", amount_base_str="200", vat_rate=21, notes=""
    )

    assert "VeriFactu" in res
    assert "rectificativa" in res
    fresh = await _reload(db, inv.id)
    assert fresh.amount_base == Decimal("100.00")  # importes intactos
    assert fresh.amount_total == Decimal("121.00")


@pytest.mark.asyncio
async def test_agente_si_edita_notas_con_registro_verifactu(db, seed_tenant_and_user):
    """La barrera solo aplica a importes: las notas (no fiscales) sí se editan."""
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-VF2", base="100.00", tax="21.00", total="121.00")
    db.add(inv)
    await db.flush()
    db.add(_verifactu_record(tenant.id, inv.id))
    await db.commit()

    res = await _update_invoice_async(
        str(tenant.id), str(inv.id), concept="", amount_base_str="", vat_rate=-1, notes="Revisada"
    )

    assert "actualizada" in res
    fresh = await _reload(db, inv.id)
    assert fresh.notes == "Revisada"


@pytest.mark.asyncio
async def test_agente_recalcula_importes_con_decimal_sin_registro(db, seed_tenant_and_user):
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-CALC", base="50.00", tax="5.00", total="55.00")
    db.add(inv)
    await db.commit()

    res = await _update_invoice_async(
        str(tenant.id), str(inv.id), concept="", amount_base_str="100", vat_rate=21, notes=""
    )

    assert "actualizada" in res
    fresh = await _reload(db, inv.id)
    assert fresh.amount_base == Decimal("100.00")
    assert fresh.tax_amount == Decimal("21.00")
    assert fresh.amount_total == Decimal("121.00")


# ─── B11: transiciones por la máquina de estado canónica ──────────────────────


@pytest.mark.asyncio
async def test_agente_no_cancela_factura_pagada(db, seed_tenant_and_user):
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(
        tenant.id, cli.id, number="F-PAID", base="100.00", tax="21.00", total="121.00", status="paid"
    )
    db.add(inv)
    await db.commit()

    res = await _update_invoice_status_async(str(tenant.id), str(inv.id), "cancelled")

    # Mensaje canonico del chokepoint (commands.update_status), al que la tool
    # ahora delega (re-audit B1/B2): mismo fondo, otra literal.
    assert res.startswith("Error")
    assert "'paid'" in res and "'cancelled'" in res
    fresh = await _reload(db, inv.id)
    assert fresh.status == "paid"  # sigue pagada


@pytest.mark.asyncio
async def test_agente_admite_transicion_a_sent(db, seed_tenant_and_user):
    """'sent' existe en la máquina canónica; la tabla duplicada del agente lo ignoraba."""
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-SENT", base="100.00", tax="21.00", total="121.00")
    db.add(inv)
    await db.commit()

    res = await _update_invoice_status_async(str(tenant.id), str(inv.id), "sent")

    assert "draft → sent" in res
    fresh = await _reload(db, inv.id)
    assert fresh.status == "sent"
