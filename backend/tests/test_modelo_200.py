"""Tests del Modelo 200 — Impuesto sobre Sociedades (F2.8)."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.reports.modelos_aeat import (
    TIPO_IS_GENERAL,
    TIPO_IS_REDUCIDO,
    UMBRAL_ERD,
    build_modelo_200_data,
)


def _inv(tenant_id, client_id, *, base: Decimal, tax: Decimal, total: Decimal, tipo: str, year: int = 2025):
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=f"X-{base}",
        date=datetime(year, 6, 15, tzinfo=UTC),
        amount_base=base,
        tax_amount=tax,
        amount_total=total,
        invoice_type=tipo,
        status="sent",
    )


@pytest.mark.asyncio
async def test_modelo_200_estructura_minima(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    result = await build_modelo_200_data(db, tenant.id, 2025)
    for key in (
        "modelo",
        "ejercicio",
        "tenant",
        "cifra_negocio",
        "gastos_facturas",
        "coste_nominas",
        "resultado_contable",
        "base_imponible",
        "tipo_impositivo_pct",
        "cuota_integra",
        "resultado_declaracion",
        "signo",
        "_warning",
    ):
        assert key in result, f"falta {key}"
    assert result["modelo"] == "200"
    assert result["ejercicio"] == 2025


@pytest.mark.asyncio
async def test_modelo_200_calculo_basico_sin_nominas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()

    # Ingresos 100.000 base, Gastos 60.000 base → Resultado 40.000
    db.add_all([
        _inv(tenant.id, cli.id, base=Decimal("100000"), tax=Decimal("21000"), total=Decimal("121000"), tipo="issued"),
        _inv(tenant.id, cli.id, base=Decimal("60000"), tax=Decimal("12600"), total=Decimal("72600"), tipo="received"),
    ])
    await db.commit()

    result = await build_modelo_200_data(db, tenant.id, 2025)
    assert result["cifra_negocio"] == 100000.0
    assert result["gastos_facturas"] == 60000.0
    assert result["coste_nominas"] == 0.0
    assert result["resultado_contable"] == 40000.0
    # ERD (cifra <1M) → tipo reducido 23%
    assert result["tipo_impositivo_pct"] == float(TIPO_IS_REDUCIDO)
    # 40000 × 23% = 9200
    assert result["cuota_integra"] == 9200.0
    assert result["resultado_declaracion"] == 9200.0
    assert result["signo"] == "ingresar"


@pytest.mark.asyncio
async def test_modelo_200_aplica_tipo_general_cuando_cifra_supera_umbral(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()

    # Cifra negocio 1.500.000 > 1M umbral ERD
    big_base = Decimal(str(UMBRAL_ERD + Decimal("500000")))  # 1.500.000
    db.add(_inv(tenant.id, cli.id, base=big_base, tax=Decimal("0"), total=big_base, tipo="issued"))
    await db.commit()

    result = await build_modelo_200_data(db, tenant.id, 2025)
    assert result["cifra_negocio"] == 1500000.0
    assert result["tipo_impositivo_pct"] == float(TIPO_IS_GENERAL)
    assert result["cuota_integra"] == 1500000.0 * 0.25  # 375000


@pytest.mark.asyncio
async def test_modelo_200_resultado_negativo_da_cuota_cero(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()

    # Más gasto que ingreso → resultado contable negativo → cuota 0
    db.add_all([
        _inv(tenant.id, cli.id, base=Decimal("10000"), tax=Decimal("0"), total=Decimal("10000"), tipo="issued"),
        _inv(tenant.id, cli.id, base=Decimal("50000"), tax=Decimal("0"), total=Decimal("50000"), tipo="received"),
    ])
    await db.commit()

    result = await build_modelo_200_data(db, tenant.id, 2025)
    assert result["resultado_contable"] == -40000.0
    assert result["cuota_integra"] == 0.0
    assert result["signo"] == "cero"


@pytest.mark.asyncio
async def test_modelo_200_descuenta_pagos_fraccionados(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()

    db.add(_inv(tenant.id, cli.id, base=Decimal("100000"), tax=Decimal("0"), total=Decimal("100000"), tipo="issued"))
    await db.commit()

    # Cuota = 100000 × 23% = 23000. Pagos fraccionados ya hechos = 10000.
    result = await build_modelo_200_data(
        db, tenant.id, 2025, pagos_fraccionados_pagados=10000,
    )
    assert result["cuota_integra"] == 23000.0
    assert result["pagos_fraccionados_pagados"] == 10000.0
    assert result["resultado_declaracion"] == 13000.0


@pytest.mark.asyncio
async def test_modelo_200_acepta_tipo_impositivo_override(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, nif="B12345678", name="X")
    db.add(cli)
    await db.flush()
    db.add(_inv(tenant.id, cli.id, base=Decimal("100000"), tax=Decimal("0"), total=Decimal("100000"), tipo="issued"))
    await db.commit()

    # Sobrescribir al 15% (entidad de nueva creación)
    result = await build_modelo_200_data(
        db, tenant.id, 2025, tipo_impositivo_pct=15,
    )
    assert result["tipo_impositivo_pct"] == 15.0
    assert result["cuota_integra"] == 15000.0
