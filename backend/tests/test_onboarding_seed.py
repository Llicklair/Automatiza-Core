"""Tests del seed de datos de ejemplo del onboarding (services/onboarding/seed.py).

Garantías que se prueban:
  - Siembra los datos esperados y marca el paso `data` del wizard.
  - Es idempotente (no duplica en una segunda llamada).
  - Las facturas demo quedan FUERA de lo fiscal (chokepoint AEAT `_invoices_in_period`)
    pero SÍ son visibles en la lista cruda de facturas (objetivo: producto vivo).
  - Las facturas demo NO consumen la serie correlativa real.
  - El borrado elimina solo lo demo; los datos reales quedan intactos.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db.models.models import Client, Invoice
from app.services.billing.numbering import next_invoice_number
from app.services.onboarding.seed import (
    clear_demo_data,
    demo_status,
    seed_demo_data,
)
from app.services.onboarding.wizard import get_state
from app.services.reports.modelos_aeat import _invoices_in_period


async def test_seed_creates_data_and_marks_step(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    res = await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)

    assert res["already_seeded"] is False
    assert res["clients"] == 4
    assert res["products"] == 4
    assert res["invoices"] == 5

    # Todo lo sembrado lleva is_demo=True
    demo_clients = await db.scalar(
        select(func.count()).select_from(Client).where(
            Client.tenant_id == tenant.id, Client.is_demo.is_(True)
        )
    )
    assert demo_clients == 4

    # El paso "tengo datos" queda marcado
    state = await get_state(db, tenant_id=tenant.id)
    assert state.step_data is True


async def test_seed_is_idempotent(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)
    res2 = await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)

    assert res2["already_seeded"] is True
    total = await db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant.id)
    )
    assert total == 5  # no duplicó


async def test_demo_invoices_excluded_from_fiscal_but_visible(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)

    start = (datetime.now(UTC) - timedelta(days=400)).date()
    end = (datetime.now(UTC) + timedelta(days=1)).date()

    # FISCAL: el chokepoint de los modelos AEAT excluye demo → 0 facturas.
    issued_fiscal = await _invoices_in_period(
        db, tenant.id, invoice_type="issued", start=start, end=end
    )
    received_fiscal = await _invoices_in_period(
        db, tenant.id, invoice_type="received", start=start, end=end
    )
    assert issued_fiscal == []
    assert received_fiscal == []

    # VISIBLE: la lista cruda de facturas SÍ ve las demo (producto vivo).
    issued_visible = await db.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.tenant_id == tenant.id, Invoice.invoice_type == "issued"
        )
    )
    assert issued_visible == 4


async def test_real_invoice_still_appears_in_fiscal(db, seed_tenant_and_user):
    """El filtro is_demo NO debe ocultar facturas reales de lo fiscal."""
    tenant, user, _ = seed_tenant_and_user
    real_client = Client(tenant_id=tenant.id, name="Cliente Real", nif="B11111111")
    db.add(real_client)
    await db.flush()
    db.add(
        Invoice(
            tenant_id=tenant.id, client_id=real_client.id, invoice_number="A2026-0001",
            date=datetime.now(UTC), status="paid", invoice_type="issued",
            amount_base=100, tax_amount=21, amount_total=121,
        )
    )
    await db.commit()
    await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)

    start = (datetime.now(UTC) - timedelta(days=2)).date()
    end = (datetime.now(UTC) + timedelta(days=1)).date()
    issued_fiscal = await _invoices_in_period(
        db, tenant.id, invoice_type="issued", start=start, end=end
    )
    # Solo la real entra en fiscal (las demo, no).
    assert len(issued_fiscal) == 1
    assert issued_fiscal[0].invoice_number == "A2026-0001"


async def test_demo_invoices_do_not_consume_real_series(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)

    # La primera factura REAL sigue siendo la 0001: el seed no tocó el contador.
    num = await next_invoice_number(db, tenant.id, series="A")
    assert num == f"A{datetime.now(UTC).year}-0001"


async def test_clear_removes_only_demo(db, seed_tenant_and_user):
    tenant, user, _ = seed_tenant_and_user
    # Dato real que NO debe borrarse.
    real_client = Client(tenant_id=tenant.id, name="Cliente Real", nif="B22222222")
    db.add(real_client)
    await db.flush()
    db.add(
        Invoice(
            tenant_id=tenant.id, client_id=real_client.id, invoice_number="A2026-0001",
            date=datetime.now(UTC), status="paid", invoice_type="issued",
            amount_base=100, tax_amount=21, amount_total=121,
        )
    )
    await db.commit()

    await seed_demo_data(db, tenant_id=tenant.id, user_id=user.id)
    await clear_demo_data(db, tenant_id=tenant.id)

    status = await demo_status(db, tenant_id=tenant.id)
    assert status["seeded"] is False
    assert status["counts"] == {"clients": 0, "products": 0, "invoices": 0}

    # El dato real sigue ahí.
    assert await db.scalar(
        select(func.count()).select_from(Invoice).where(Invoice.tenant_id == tenant.id)
    ) == 1
    assert await db.scalar(
        select(func.count()).select_from(Client).where(Client.tenant_id == tenant.id)
    ) == 1
