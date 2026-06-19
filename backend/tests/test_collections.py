"""Tests de inteligencia de cobros (F3.9)."""
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.collections.reminders import (
    INTERES_DEMORA_PCT_ANUAL,
    build_reminder_schedule,
    invoices_due_for_reminder,
)
from app.services.collections.risk import (
    compute_client_risk,
    rank_tenant_collections,
)


def _inv(
    tenant_id, client_id, *, number: str, total: Decimal, status: str,
    issue: datetime, due: datetime | None, updated: datetime | None = None,
) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=issue,
        due_date=due,
        amount_base=total,
        tax_amount=Decimal("0"),
        amount_total=total,
        invoice_type="issued",
        status=status,
        updated_at=updated or issue,
    )


# ─── Risk scoring (puro, sin DB) ────────────────────────────────────────


def test_compute_risk_cliente_perfecto():
    client = Client(name="Cliente OK", nif="B1")
    today = date(2026, 5, 21)
    inv = _inv(
        None, None,
        number="F1",
        total=Decimal("1000"),
        status="paid",
        issue=datetime(2026, 1, 5, tzinfo=UTC),
        due=datetime(2026, 2, 5, tzinfo=UTC),
        updated=datetime(2026, 2, 4, tzinfo=UTC),  # pagada 1 día antes
    )
    score = compute_client_risk(client, [inv], today=today)
    assert score.risk_level == "low"
    assert score.overdue_count == 0
    assert score.paid_count == 1
    assert score.ratio_paid_on_time == 1.0


def test_compute_risk_cliente_con_factura_vencida():
    """Una sola factura vencida 50 días con 8000€ → medium (alerta pero no rojo)."""
    client = Client(name="Moroso SL", nif="B2")
    today = date(2026, 5, 21)
    inv = _inv(
        None, None,
        number="F1", total=Decimal("8000"), status="sent",
        issue=datetime(2026, 3, 1, tzinfo=UTC),
        due=datetime(2026, 4, 1, tzinfo=UTC),
    )
    score = compute_client_risk(client, [inv], today=today)
    assert score.overdue_count == 1
    assert score.max_days_overdue == 50
    assert score.risk_level == "medium"
    assert score.overdue_amount == 8000.0
    assert any("vencida" in d for d in score.drivers)


def test_compute_risk_multiples_facturas_vencidas_da_high():
    """3+ facturas vencidas con demora alta → high (patrón sostenido)."""
    client = Client(name="Moroso reincidente", nif="B9")
    today = date(2026, 5, 21)
    invs = [
        _inv(
            None, None, number=f"F{i}", total=Decimal("3000"), status="sent",
            issue=datetime(2026, 2, 1, tzinfo=UTC),
            due=datetime(2026, 3, 1, tzinfo=UTC),
        )
        for i in range(3)
    ]
    score = compute_client_risk(client, invs, today=today)
    assert score.overdue_count == 3
    assert score.risk_level == "high"


def test_compute_risk_mix_paga_tarde_sin_vencidas():
    client = Client(name="Tarde SA", nif="B3")
    today = date(2026, 5, 21)
    # Cobradas pero todas con 60 días de retraso
    inv1 = _inv(
        None, None, number="F1", total=Decimal("1000"), status="paid",
        issue=datetime(2026, 1, 1, tzinfo=UTC),
        due=datetime(2026, 1, 31, tzinfo=UTC),
        updated=datetime(2026, 3, 30, tzinfo=UTC),  # 88 días después
    )
    score = compute_client_risk(client, [inv1], today=today)
    assert score.overdue_count == 0
    assert score.days_avg_to_pay is not None
    assert score.days_avg_to_pay >= 45
    # Pagó tarde → ratio_paid_on_time = 0
    assert score.ratio_paid_on_time == 0.0
    assert score.risk_level in ("medium", "high")


# ─── Reminder schedule (puro, sin DB) ──────────────────────────────────


def test_build_reminder_schedule_4_pasos():
    client = Client(name="X", nif="B1", email="cliente@example.com")
    inv = _inv(
        None, "c1", number="F-100",
        total=Decimal("1210"),
        status="sent",
        issue=datetime(2026, 5, 1, tzinfo=UTC),
        due=datetime(2026, 5, 31, tzinfo=UTC),
    )
    inv.client = client
    inv.client_id = "c1"
    inv.id = "inv1"

    steps = build_reminder_schedule(inv, today=date(2026, 5, 21))
    assert [s.step for s in steps] == [
        "friendly_pre", "reminder_due", "formal_d15", "formal_d30",
    ]
    assert steps[0].fire_date == date(2026, 5, 28)
    assert steps[1].fire_date == date(2026, 5, 31)
    assert steps[2].fire_date == date(2026, 6, 15)
    assert steps[3].fire_date == date(2026, 6, 30)


def test_reminder_d30_calcula_intereses_demora():
    client = Client(name="X", nif="B1")
    inv = _inv(
        None, "c1", number="F-100",
        total=Decimal("12000"),
        status="sent",
        issue=datetime(2026, 1, 1, tzinfo=UTC),
        due=datetime(2026, 2, 1, tzinfo=UTC),
    )
    inv.client = client
    inv.client_id = "c1"
    inv.id = "inv2"

    steps = build_reminder_schedule(inv)
    d30 = [s for s in steps if s.step == "formal_d30"][0]
    # 12000 * 12.5% * 30/365 ≈ 123.29
    expected = 12000 * float(INTERES_DEMORA_PCT_ANUAL) / 100 * 30 / 365
    assert abs(d30.interest_amount - expected) < 1.0
    assert "intereses" in d30.body.lower() or "demora" in d30.body.lower()


def test_factura_pagada_no_genera_recordatorios():
    client = Client(name="X", nif="B1")
    inv = _inv(
        None, "c1", number="F-100",
        total=Decimal("100"),
        status="paid",
        issue=datetime(2026, 1, 1, tzinfo=UTC),
        due=datetime(2026, 2, 1, tzinfo=UTC),
    )
    inv.client = client
    inv.client_id = "c1"
    inv.id = "inv3"
    assert build_reminder_schedule(inv) == []


def test_factura_sin_due_date_no_genera_recordatorios():
    client = Client(name="X", nif="B1")
    inv = _inv(
        None, "c1", number="F-100",
        total=Decimal("100"),
        status="sent",
        issue=datetime(2026, 1, 1, tzinfo=UTC),
        due=None,
    )
    inv.client = client
    inv.client_id = "c1"
    inv.id = "inv4"
    assert build_reminder_schedule(inv) == []


# ─── Integración con DB ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rank_tenant_collections_ordena_por_score(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    good = Client(tenant_id=tenant.id, nif="B11111111", name="Buen Cliente")
    bad = Client(tenant_id=tenant.id, nif="B22222222", name="Moroso")
    db.add_all([good, bad])
    await db.flush()

    today = date(2026, 5, 21)
    # Buen cliente: pagada
    db.add(_inv(
        tenant.id, good.id, number="OK-1",
        total=Decimal("500"), status="paid",
        issue=datetime(2026, 1, 1, tzinfo=UTC),
        due=datetime(2026, 1, 31, tzinfo=UTC),
        updated=datetime(2026, 1, 30, tzinfo=UTC),
    ))
    # Moroso: 3 facturas vencidas
    for i in range(3):
        db.add(_inv(
            tenant.id, bad.id, number=f"BAD-{i}",
            total=Decimal("2000"), status="sent",
            issue=datetime(2026, 2, 1, tzinfo=UTC),
            due=datetime(2026, 3, 1, tzinfo=UTC),
        ))
    await db.commit()

    ranked = await rank_tenant_collections(db, tenant.id, today=today)
    assert ranked, "Esperaba al menos un cliente con outstanding"
    assert ranked[0].client_name == "Moroso"
    assert ranked[0].risk_level == "high"


@pytest.mark.asyncio
async def test_invoices_due_for_reminder_devuelve_solo_fire_date(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B1", name="X", email="c@x.es")
    db.add(cli)
    await db.flush()

    today = date(2026, 5, 21)
    # Factura cuyo "reminder_due" cae hoy (due=today)
    db.add(_inv(
        tenant.id, cli.id, number="DUE-TODAY",
        total=Decimal("100"), status="sent",
        issue=datetime(2026, 4, 21, tzinfo=UTC),
        due=datetime(2026, 5, 21, tzinfo=UTC),
    ))
    # Factura cuyo "formal_d15" cae hoy (due=today-15)
    db.add(_inv(
        tenant.id, cli.id, number="D15-TODAY",
        total=Decimal("200"), status="sent",
        issue=datetime(2026, 4, 1, tzinfo=UTC),
        due=datetime(2026, 5, 6, tzinfo=UTC),
    ))
    # Factura cuyo paso de hoy no toca (due en 30 días → friendly_pre cae en day+27)
    db.add(_inv(
        tenant.id, cli.id, number="FAR",
        total=Decimal("300"), status="sent",
        issue=datetime(2026, 5, 1, tzinfo=UTC),
        due=datetime(2026, 6, 20, tzinfo=UTC),
    ))
    await db.commit()

    steps = await invoices_due_for_reminder(db, tenant.id, today=today)
    by_number = {s.invoice_number: s for s in steps}
    assert "DUE-TODAY" in by_number
    assert by_number["DUE-TODAY"].step == "reminder_due"
    assert "D15-TODAY" in by_number
    assert by_number["D15-TODAY"].step == "formal_d15"
    assert "FAR" not in by_number
