"""Regresión de los arreglos fiscales de 2026-06-24.

- B1/B5: `create_invoice_payment_entry` es idempotente (re-conciliar no duplica
  el asiento de cobro 572/430).
- B16: `auto_reconcile` genera el asiento de cobro (antes marcaba la factura
  pagada SIN dejar huella contable, a diferencia de la conciliación manual).
- B9/B10: el acuse de una presentación AEAT simulada (dry_run) se marca como
  SIN VALIDEZ y no incluye la línea de verificación en sede (línea roja: no
  falsificar justificante/CSV).
"""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.models import BankTransaction, JournalEntry
from app.services.aeat.presentation_service import build_acuse_text
from app.services.banking.service import auto_reconcile
from app.services.billing.auto_accounting import create_invoice_payment_entry


async def _seed_client(db, tenant_id, name="Acme Industrial S.L.") -> Client:
    cli = Client(tenant_id=tenant_id, name=name, nif="B22222222")
    db.add(cli)
    await db.flush()
    return cli


def _invoice(tenant_id, client_id, *, number, total, status="sent") -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 10, tzinfo=UTC),
        amount_base=Decimal(str(round(total / 1.21, 2))),
        tax_amount=Decimal(str(round(total - total / 1.21, 2))),
        amount_total=Decimal(str(total)),
        invoice_type="issued",
        status=status,
    )


async def _count_payment_entries(db, tenant_id, invoice_id) -> int:
    return (
        await db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.tenant_id == tenant_id,
                JournalEntry.reference_id == f"PAY-INV-{invoice_id}",
            )
        )
    ).scalar()


# ─── B1/B5: asiento de cobro idempotente ──────────────────────────────────────


@pytest.mark.asyncio
async def test_invoice_payment_entry_no_duplica(db, seed_tenant_and_user):
    tenant, _user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-IDEM", total=121.0)
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    first = await create_invoice_payment_entry(db, tenant.id, inv)
    second = await create_invoice_payment_entry(db, tenant.id, inv)  # re-conciliación
    await db.commit()

    assert first is not None
    assert second is None  # idempotente: no crea un segundo asiento
    assert await _count_payment_entries(db, tenant.id, inv.id) == 1


# ─── B16: auto_reconcile deja huella contable ─────────────────────────────────


@pytest.mark.asyncio
async def test_auto_reconcile_genera_asiento_de_cobro(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    cli = await _seed_client(db, tenant.id)
    inv = _invoice(tenant.id, cli.id, number="F-B16", total=121.0)
    tx = BankTransaction(
        tenant_id=tenant.id,
        date=datetime(2026, 5, 12, tzinfo=UTC),
        amount=Decimal("121.0"),
        description="TRF SEPA ACME INDUSTRIAL ref F-B16",
        status="unreconciled",
    )
    db.add_all([inv, tx])
    await db.commit()

    res = await auto_reconcile(db, tenant.id, user.id)
    assert res["matched"] == 1

    await db.refresh(inv)
    await db.refresh(tx)
    assert inv.status == "paid"
    assert tx.journal_entry_id is not None  # antes quedaba None
    assert await _count_payment_entries(db, tenant.id, inv.id) == 1


# ─── B9/B10: acuse de ensayo (dry_run) sin validez ────────────────────────────


class _FakePres:
    """Stub mínimo de AeatPresentation para probar build_acuse_text (función pura)."""

    def __init__(self, status, csv):
        self.model_code = "303"
        self.year = 2026
        self.period = "2T"
        self.environment = "preproduccion"
        self.status = status
        self.csv_justificante = csv
        self.submitted_at = None
        self.accepted_at = None


def test_acuse_simulado_se_marca_sin_validez():
    txt = build_acuse_text(_FakePres("simulado", None))
    assert "SIMULADO" in txt
    assert "SIN VALIDEZ" in txt
    assert "Verificable en" not in txt  # nunca debe parecer un justificante real


def test_acuse_aceptado_real_es_verificable():
    txt = build_acuse_text(_FakePres("accepted", "ABCD1234EFGH5678"))
    assert "SIMULADO" not in txt
    assert "Verificable en" in txt
