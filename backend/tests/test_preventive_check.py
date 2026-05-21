"""Tests del asistente fiscal preventivo (F1.4)."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.db.models.billing import Invoice, InvoiceLine
from app.db.models.crm import Client
from app.services.aeat.preventive_check import Finding, check_quarter


def _inv(
    tenant_id,
    client_id,
    *,
    total: Decimal,
    base: Decimal,
    tax: Decimal,
    fecha: datetime,
    tipo: str,
    status: str = "issued",
    number: str | None = None,
) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number or f"INV-{int(total):06d}",
        date=fecha,
        amount_base=base,
        tax_amount=tax,
        amount_total=total,
        invoice_type=tipo,
        status=status,
    )


def _line(qty: int = 1, price: Decimal = Decimal("100"), tax_pct: float = 21.0) -> InvoiceLine:
    return InvoiceLine(
        description="Servicio",
        quantity=qty,
        unit_price=price,
        tax_percentage=tax_pct,
    )


def _codes(findings: list[Finding]) -> set[str]:
    return {f.code for f in findings}


@pytest.mark.asyncio
async def test_sin_facturas_sin_hallazgos(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    assert findings == []


@pytest.mark.asyncio
async def test_received_sin_nif_proveedor_detectado(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    proveedor_sin_nif = Client(tenant_id=tenant.id, name="Proveedor desconocido")
    db.add(proveedor_sin_nif)
    await db.flush()

    inv = _inv(
        tenant.id,
        proveedor_sin_nif.id,
        total=Decimal("121"),
        base=Decimal("100"),
        tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC),
        tipo="received",
    )
    inv.lines = [_line()]
    db.add(inv)
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    assert "received_without_supplier_nif" in _codes(findings)


@pytest.mark.asyncio
async def test_factura_sin_lineas_detectada(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()
    inv = _inv(
        tenant.id,
        cli.id,
        total=Decimal("121"),
        base=Decimal("100"),
        tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC),
        tipo="issued",
        status="confirmed",
    )
    db.add(inv)
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    assert "invoices_without_lines" in _codes(findings)


@pytest.mark.asyncio
async def test_totales_descuadrados(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()
    inv = _inv(
        tenant.id,
        cli.id,
        total=Decimal("200"),  # base+tax = 121, total = 200 → mismatch
        base=Decimal("100"),
        tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC),
        tipo="issued",
        status="confirmed",
    )
    inv.lines = [_line()]
    db.add(inv)
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    assert "amount_mismatch" in _codes(findings)


@pytest.mark.asyncio
async def test_draft_emitida_en_periodo_detectada(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()
    inv = _inv(
        tenant.id,
        cli.id,
        total=Decimal("121"),
        base=Decimal("100"),
        tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC),
        tipo="issued",
        status="draft",
    )
    inv.lines = [_line()]
    db.add(inv)
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    high = [f for f in findings if f.code == "draft_issued_in_period"]
    assert high and high[0].severity == "high"


@pytest.mark.asyncio
async def test_iva_repercutido_sin_facturas_recibidas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
    db.add(cli)
    await db.flush()
    inv = _inv(
        tenant.id,
        cli.id,
        total=Decimal("1210"),
        base=Decimal("1000"),
        tax=Decimal("210"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC),
        tipo="issued",
        status="confirmed",
    )
    inv.lines = [_line(qty=10, price=Decimal("100"))]
    db.add(inv)
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    assert "no_received_invoices" in _codes(findings)


@pytest.mark.asyncio
async def test_severidad_ordenada_high_primero(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli_sin_nif = Client(tenant_id=tenant.id, name="Sin NIF")
    cli_ok = Client(tenant_id=tenant.id, nif="B11111111", name="OK")
    db.add_all([cli_sin_nif, cli_ok])
    await db.flush()

    inv_recibida_sin_nif = _inv(
        tenant.id, cli_sin_nif.id,
        total=Decimal("121"), base=Decimal("100"), tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC), tipo="received", status="confirmed",
    )
    inv_recibida_sin_nif.lines = [_line()]
    inv_descuadrada = _inv(
        tenant.id, cli_ok.id,
        total=Decimal("999"), base=Decimal("100"), tax=Decimal("21"),
        fecha=datetime(2026, 2, 10, tzinfo=UTC), tipo="issued", status="confirmed",
    )
    inv_descuadrada.lines = [_line()]
    db.add_all([inv_recibida_sin_nif, inv_descuadrada])
    await db.commit()

    findings = await check_quarter(db, tenant.id, quarter=1, year=2026)
    severities = [f.severity for f in findings]
    # Todos los "high" preceden a "medium"/"low"
    rank = {"high": 0, "medium": 1, "low": 2}
    assert severities == sorted(severities, key=lambda s: rank.get(s, 9))


@pytest.mark.asyncio
async def test_quarter_invalido_raises(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    with pytest.raises(ValueError):
        await check_quarter(db, tenant.id, quarter=5, year=2026)
