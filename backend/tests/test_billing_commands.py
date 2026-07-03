"""Tests dirigidos de app/services/billing/commands.py — gaps de cobertura.

NO duplica lo ya cubierto por:
  - tests/test_service_invoice.py  → create_invoice básico, totales, descuentos,
    IVA inválido, número manual/duplicado, update_status (estado inválido), delete básico.
  - tests/test_rectificativa.py    → create_rectificativa completo.
  - tests/test_invoice_numbering.py → next_invoice_number.

Aquí se cubre:
  - Garantía "sin huecos": un create_invoice que falla en validación NO consume
    número de serie (RD 1619/2012).
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
    """Un total negativo se rechaza con ValueError. Tras el rechazo, un
    create_invoice válido produce una PROFORMA sin número fiscal: el ERP ya no
    emite facturas fiscales (invoice_number=NULL, invoice_type='proforma')."""
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
    assert inv.invoice_number is None
    assert inv.invoice_type == "proforma"
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
async def test_delete_borra_asientos_vinculados(db, seed_tenant_and_user):
    """Una factura BORRADOR con asiento contable se borra junto al asiento. Las
    emitidas ya numeradas NO se borran (N7) — se anulan con rectificativa."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = await _seed_invoice(db, tenant.id, cli.id, status="draft")

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
async def test_delete_bloqueado_si_factura_emitida_numerada(db, seed_tenant_and_user):
    """N7: una factura emitida ya numerada (pending/sent/paid) no se borra; se anula
    con una rectificativa. El contador correlativo no retrocede (RD 1619/2012)."""
    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = await _seed_invoice(db, tenant.id, cli.id, status="pending")
    inv_id = inv.id

    with pytest.raises(ValueError, match="rectificativa"):
        await delete_invoice(inv_id, tenant.id, db)
    await db.rollback()

    still = await db.execute(select(Invoice.id).where(Invoice.id == inv_id))
    assert still.scalar_one_or_none() is not None, "La factura emitida no debe borrarse"


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


@pytest.mark.asyncio
async def test_journal_entry_tolera_un_centimo_pero_no_dos(db, seed_tenant_and_user):
    """N6: un descuadre de 0,01 € (redondeo legítimo base/IVA/total) se tolera; uno
    de 0,02 € se rechaza. El cuadre se evalúa en Decimal, no en float."""
    tenant, _u, _t = seed_tenant_and_user
    entry = await create_journal_entry(
        db, tenant.id, date=datetime(YEAR, 5, 10, tzinfo=UTC),
        description="redondeo 1c", reference_id=None,
        lines=[
            {"account_code": "430", "debit": 100.00, "credit": 0.0},
            {"account_code": "700", "debit": 0.0, "credit": 99.99},
        ],
    )
    assert entry is not None  # 0,01 € tolerado

    with pytest.raises(ValueError, match="descuadrado"):
        await create_journal_entry(
            db, tenant.id, date=datetime(YEAR, 5, 10, tzinfo=UTC),
            description="descuadre 2c", reference_id=None,
            lines=[
                {"account_code": "430", "debit": 100.00, "credit": 0.0},
                {"account_code": "700", "debit": 0.0, "credit": 99.98},
            ],
        )


# ─── run_recurring ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_recurring_genera_factura(db, seed_tenant_and_user):
    """La plantilla recurrente genera una PROFORMA draft con totales correctos y
    avanza next_run_date según el intervalo.

    El ERP ya no emite facturas fiscales: run_recurring produce una proforma sin
    número (invoice_number=NULL, invoice_type='proforma').
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
    assert inv.invoice_type == "proforma"
    assert inv.client_id == cli.id
    # Una proforma no lleva número fiscal correlativo.
    assert inv.invoice_number is None
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


# ─── _process_recurring_invoices (cron diario) ───────────────────────────────


@pytest.mark.asyncio
async def test_process_recurring_invoices_cron_produces_proforma(db, seed_tenant_and_user):
    """Opción A (candado): el cron diario de recurrentes NO emite facturas
    fiscales — genera PROFORMAS sin número correlativo (invoice_number=NULL,
    invoice_type='proforma'). Regresión de workers.tasks_scheduler._process_recurring_invoices."""
    from datetime import date

    from app.db.base import AsyncSessionLocal
    from app.workers.tasks_scheduler import _process_recurring_invoices

    tenant, _u, _t = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id, name="Cliente Cron S.L.")
    rec = RecurringInvoice(
        tenant_id=tenant.id,
        client_id=cli.id,
        name="Cuota mensual",
        interval_type="monthly",
        is_active=True,
        next_run_date=date(2000, 1, 1),  # vencida → el cron la procesa
        lines_json=[
            {"description": "Cuota", "quantity": 1, "unit_price": 50.0, "tax_percentage": 21}
        ],
    )
    db.add(rec)
    await db.commit()

    result = await _process_recurring_invoices()
    assert result == {"generated": 1}

    # El cron abre su propia sesión (AsyncSessionLocal). Se relee en una sesión
    # fresca para evitar chocar con la sesión del fixture en la conexión SQLite
    # compartida (StaticPool).
    async with AsyncSessionLocal() as fresh:
        res = await fresh.execute(select(Invoice).where(Invoice.tenant_id == tenant.id))
        invoices = res.scalars().all()
    assert len(invoices) == 1
    assert invoices[0].invoice_number is None
    assert invoices[0].invoice_type == "proforma"
