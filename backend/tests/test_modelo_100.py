"""Tests del Modelo 100 (IRPF Renta, preview) — datos + escala + PDF."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.services.pdf_reports import generate_modelo_100_pdf
from app.services.reports.modelos_aeat import _irpf_cuota, build_modelo_100_data


def test_irpf_cuota_escala_progresiva():
    assert _irpf_cuota(Decimal("0")) == Decimal("0.00")
    assert _irpf_cuota(Decimal("-100")) == Decimal("0.00")
    assert _irpf_cuota(Decimal("10000")) == Decimal("1900.00")  # 10000 × 19%
    assert _irpf_cuota(Decimal("20200")) == Decimal("4225.50")  # 12450×19 + 7750×24
    assert _irpf_cuota(Decimal("50000")) == Decimal("14201.50")


@pytest.mark.asyncio
async def test_build_modelo_100_preview(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, name="Cliente", nif="B12345678")
    db.add(cli)
    await db.flush()
    # Ingreso 30.000 con retención 4.500; gasto 5.000
    db.add(Invoice(
        tenant_id=tenant.id, client_id=cli.id, date=datetime(2025, 6, 1, tzinfo=UTC),
        amount_base=Decimal("30000"), amount_total=Decimal("36300"),
        invoice_type="issued", retencion_irpf_amount=Decimal("4500"),
    ))
    db.add(Invoice(
        tenant_id=tenant.id, client_id=cli.id, date=datetime(2025, 3, 1, tzinfo=UTC),
        amount_base=Decimal("5000"), amount_total=Decimal("6050"), invoice_type="received",
    ))
    await db.commit()

    data = await build_modelo_100_data(db, tenant.id, 2025)
    assert data["modelo"] == "100"
    assert data["ingresos"] == 30000.0
    assert data["gastos_facturas"] == 5000.0
    assert data["rendimiento_neto"] == 25000.0
    assert data["base_liquidable"] == 19450.0  # 25000 − 5550 mínimo
    assert data["cuota_integra"] == 4045.50  # 12450×19 + 7000×24
    assert data["retenciones_soportadas"] == 4500.0
    assert data["resultado_declaracion"] == -454.5
    assert data["signo"] == "devolver"


@pytest.mark.asyncio
async def test_build_modelo_100_sin_actividad(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    data = await build_modelo_100_data(db, tenant.id, 2025)
    assert data["rendimiento_neto"] == 0.0
    assert data["cuota_integra"] == 0.0
    assert data["signo"] == "cero"


def test_modelo_100_pdf_renders():
    data = {
        "modelo": "100", "ejercicio": 2025, "tenant": {"name": "X", "nif": "B1"},
        "ingresos": 30000.0, "gastos_facturas": 5000.0, "coste_nominas": 0.0,
        "rendimiento_neto": 25000.0, "minimo_personal": 5550.0, "base_liquidable": 19450.0,
        "cuota_integra": 4045.50, "retenciones_soportadas": 4500.0,
        "pagos_fraccionados_pagados": 0.0, "resultado_declaracion": -454.5,
        "signo": "devolver", "_warning": "Preview no oficial.",
    }
    pdf = generate_modelo_100_pdf(data)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1500
