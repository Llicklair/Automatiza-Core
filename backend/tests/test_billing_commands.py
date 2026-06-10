"""Tests dirigidos de app/services/billing/commands.py — gaps de cobertura.

NO duplica lo ya cubierto por:
  - tests/test_service_invoice.py  → create_invoice básico, totales, descuentos,
    IVA inválido, número manual/duplicado, update_status (estado inválido), delete básico.
  - tests/test_rectificativa.py    → create_rectificativa completo.
  - tests/test_invoice_numbering.py → next_invoice_number.

Aquí se cubre:
  - Garantía "sin huecos": un create_invoice que falla en validación NO consume
    número de serie (RD 1619/2012).
  - delete_invoice bloqueado si la factura tiene registro Verifactu (cadena inmutable).
  - delete_invoice borra en cascada los asientos contables vinculados.
  - create_journal_entry rechaza asientos descuadrados.
  - run_recurring genera una factura desde la plantilla y avanza next_run_date.
  - update_status valida transiciones contra state_machine (paid → draft se rechaza).
"""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.models.billing import VerifactuRecord
from app.db.models.crm import Client
from app.db.models.models import Invoice, JournalEntry, RecurringInvoice
from app.services.billing.commands import (
    create_invoice,
    create_journal_entry,
    delete_invoice,
    run_recurring,
    update_status,
)

YEAR = datetime.now(UTC).year


async def _seed_client(db, tenant_id, name="Cliente Test S.L.") -> Client:
    cli = Client(tenant_id=tenant_id, name=name, nif="B11111111")
    db.add(cli)
    await db.flush()
    return cli


def _line(unit_price: float, quantity: float = 1, tax: float = 21) -> dict:
    return {
        "description": "Servicio",
        "quantity": quantity,
        "unit_price": unit_price,
        "discount_percentage": 0,
        "tax_percentage": tax,
    }


async def _seed_invoice(db, tenant_id, client_id, *, status="pending", number="F-TEST-1") -> Invoice:
    inv = Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(YEAR, 5, 10, tzinfo=UTC),
        amount_base=Decimal("100"),
        tax_amount=Decimal("21"),
        amount_total=Decimal("121"),
        status=status,
        invoice_type="issued",
    )
    db.add(inv)
    await db.commit()
    return inv


# ─── create_invoice: garantía sin huecos ──────────────────────────────────────


@pytest.mark.asyncio
async def test_total_negativo_rechazado_y_no_consume_numero(db, seed_tenant_and_user):
    """Si la validación falla (total negativo), el contador de serie no se toca:
    la siguiente factura válida recibe el número 0001 (sin huecos)."""
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    await db.commit()

    with pytest.raises(ValueError):
        await create_invoice(
            client_id=cli.id,
            payload_dict={"date": datetime.now(UTC), "status": "draft", "invoice_type": "issued"},
            lines_data=[_line(-100.0)],
            tenant_id=tenant.id,
            user_id=user.id,
            db=db,
        )
    await db.rollback()

    inv = await create_invoice(
        client_id=cli.id,
        payload_dict={"date": datetime.now(UTC), "status": "draft", "invoice_type": "issued"},
        lines_data=[_line(100.0)],
        tenant_id=tenant.id,
        user_id=user.id,
        db=db,
    )
    assert inv.invoice_number == f"F{YEAR}-0001"
    assert float(inv.amount_base) == 100.0
    assert float(inv.tax_amount) == 21.0
    assert float(inv.amount_total) == 121.0


# ─── update_status: gap de máquina de estados ─────────────────────────────────


@pytest.mark.asyncio
async def test_update_status_paid_a_draft_deberia_rechazarse(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = await _seed_invoice(db, tenant.id, cli.id, status="paid")

    with pytest.raises(ValueError):
        await update_status(inv.id, tenant.id, "draft", db)


# ─── delete_invoice: salvaguardas ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_bloqueado_si_hay_registro_verifactu(db, seed_tenant_and_user):
    """La cadena Verifactu es append-only: una factura encadenada no se borra."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = await _seed_invoice(db, tenant.id, cli.id)
    inv_id = inv.id  # capturar antes: el rollback posterior expira el objeto

    db.add(
        VerifactuRecord(
            tenant_id=tenant.id,
            invoice_id=inv.id,
            huella="a" * 64,
            huella_anterior=None,
            payload_canonico="{}",
            nif_emisor="B12345678",
            serie_factura="F",
            numero_factura=inv.invoice_number,
            fecha_emision=datetime(YEAR, 5, 10, tzinfo=UTC),
            importe_total=Decimal("121"),
        )
    )
    await db.commit()

    with pytest.raises(ValueError, match="Verifactu"):
        await delete_invoice(inv_id, tenant.id, db)
    await db.rollback()

    still = await db.execute(select(Invoice.id).where(Invoice.id == inv_id))
    assert still.scalar_one_or_none() is not None, "La factura no debe haberse borrado"


@pytest.mark.asyncio
async def test_delete_borra_asientos_vinculados(db, seed_tenant_and_user):
    """Una factura con asiento contable (periodo abierto) se borra junto al asiento."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = await _seed_invoice(db, tenant.id, cli.id)

    entry = await create_journal_entry(
        db,
        tenant.id,
        date=datetime(YEAR, 5, 10, tzinfo=UTC),
        description="Venta",
        reference_id=inv.invoice_number,
        lines=[
            {"account_code": "430", "account_name": "Clientes", "debit": 121.0, "credit": 0.0},
            {"account_code": "700", "account_name": "Ventas", "debit": 0.0, "credit": 121.0},
        ],
        invoice_id=inv.id,
    )

    assert await delete_invoice(inv.id, tenant.id, db) is True

    gone_inv = await db.execute(select(Invoice.id).where(Invoice.id == inv.id))
    assert gone_inv.scalar_one_or_none() is None
    gone_entry = await db.execute(select(JournalEntry.id).where(JournalEntry.id == entry.id))
    assert gone_entry.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_journal_entry_descuadrado_rechazado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(ValueError, match="descuadrado"):
        await create_journal_entry(
            db,
            tenant.id,
            date=datetime(YEAR, 5, 10, tzinfo=UTC),
            description="Asiento roto",
            reference_id=None,
            lines=[
                {"account_code": "430", "debit": 100.0, "credit": 0.0},
                {"account_code": "700", "debit": 0.0, "credit": 50.0},
            ],
        )


# ─── run_recurring ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_recurring_genera_factura(db, seed_tenant_and_user):
    """La plantilla recurrente genera factura draft con totales correctos y
    avanza next_run_date según el intervalo.

    Observación (no bug bloqueante, documentado): run_recurring numera con
    "REC-<timestamp>" fuera de la numeración correlativa de next_invoice_number,
    a diferencia de create_invoice.
    """
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    rec = RecurringInvoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        name="Cuota mensual",
        interval_type="monthly",
        next_run_date=datetime.now(UTC).date(),
        lines_json=[
            {"description": "Cuota", "quantity": 2, "unit_price": 50.0, "tax_percentage": 21}
        ],
    )
    db.add(rec)
    await db.commit()

    inv = await run_recurring(rec.id, tenant.id, db)

    assert inv is not None
    assert inv.status == "draft"
    assert inv.invoice_type == "issued"
    assert inv.client_id == cli.id
    assert inv.invoice_number.startswith("REC-")
    assert float(inv.amount_base) == 100.0
    assert float(inv.tax_amount) == 21.0
    assert float(inv.amount_total) == 121.0
    assert len(inv.lines) == 1

    await db.refresh(rec)
    assert rec.last_run_date == datetime.now(UTC).date()
    assert rec.next_run_date > rec.last_run_date  # avanzó al siguiente periodo


@pytest.mark.asyncio
async def test_run_recurring_inexistente_devuelve_none(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    assert await run_recurring(uuid4(), tenant.id, db) is None
