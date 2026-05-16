"""Tests para los modelos AEAT 130, 347 y 390 (MOD.* sprint 4)."""
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.db.models.billing import Invoice, InvoiceLine
from app.db.models.crm import Client
from app.services.reports.modelos_aeat import (
    MODELO_347_THRESHOLD,
    build_modelo_130_data,
    build_modelo_347_data,
    build_modelo_390_data,
)


def _make_invoice(tenant_id, client_id, *, total: Decimal, base: Decimal, tax: Decimal, fecha: datetime, tipo: str) -> Invoice:
    return Invoice(
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=f"X-{fecha.month:02d}-{int(total):06d}",
        date=fecha,
        amount_base=base,
        tax_amount=tax,
        amount_total=total,
        invoice_type=tipo,
    )


def _make_line(*, qty: int, price: Decimal, tax_pct: float = 21.0, description: str = "Servicio") -> InvoiceLine:
    return InvoiceLine(
        description=description,
        quantity=qty,
        unit_price=price,
        tax_percentage=tax_pct,
    )


@pytest.mark.asyncio
class TestModelo130:
    async def test_pago_fraccionado_20_pct_del_beneficio(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()

        # 1T 2026: 1000€ ingresos, 200€ gastos → beneficio 800 → pago 160
        inv_ingreso = _make_invoice(
            tenant.id, client.id,
            total=Decimal("1210"), base=Decimal("1000"), tax=Decimal("210"),
            fecha=datetime(2026, 2, 15, tzinfo=UTC),
            tipo="issued",
        )
        inv_gasto = _make_invoice(
            tenant.id, client.id,
            total=Decimal("242"), base=Decimal("200"), tax=Decimal("42"),
            fecha=datetime(2026, 2, 20, tzinfo=UTC),
            tipo="received",
        )
        db.add_all([inv_ingreso, inv_gasto])
        await db.commit()

        result = await build_modelo_130_data(db, tenant.id, quarter=1, year=2026)
        assert result["modelo"] == "130"
        assert result["periodo"] == "1T"
        assert result["ingresos_acumulados"] == 1000.0
        assert result["gastos_acumulados"] == 200.0
        assert result["beneficio_acumulado"] == 800.0
        assert result["pago_fraccionado_bruto"] == 160.0

    async def test_pago_fraccionado_no_negativo(self, db, seed_tenant_and_user):
        tenant, _user, _token = seed_tenant_and_user
        client = Client(tenant_id=tenant.id, nif="B12345678", name="Cliente")
        db.add(client)
        await db.flush()

        # Solo gastos, sin ingresos → beneficio negativo → pago fraccionado = 0
        inv_gasto = _make_invoice(
            tenant.id, client.id,
            total=Decimal("605"), base=Decimal("500"), tax=Decimal("105"),
            fecha=datetime(2026, 2, 1, tzinfo=UTC),
            tipo="received",
        )
        db.add(inv_gasto)
        await db.commit()

        result = await build_modelo_130_data(db, tenant.id, quarter=1, year=2026)
        assert result["beneficio_acumulado"] == -500.0
        assert result["pago_fraccionado_bruto"] == 0.0

    async def test_quarter_invalido_raises(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        with pytest.raises(ValueError):
            await build_modelo_130_data(db, tenant.id, quarter=5, year=2026)


@pytest.mark.asyncio
class TestModelo347:
    async def test_solo_se_declaran_los_que_superan_umbral(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        c1 = Client(tenant_id=tenant.id, nif="B11111111", name="Big Client")
        c2 = Client(tenant_id=tenant.id, nif="B22222222", name="Small Client")
        db.add_all([c1, c2])
        await db.flush()

        # c1: 4000€ → supera umbral
        # c2: 1000€ → NO supera umbral
        invs = [
            _make_invoice(tenant.id, c1.id, total=Decimal("4000"), base=Decimal("3306"), tax=Decimal("694"),
                          fecha=datetime(2026, 6, 1, tzinfo=UTC), tipo="issued"),
            _make_invoice(tenant.id, c2.id, total=Decimal("1000"), base=Decimal("826"), tax=Decimal("174"),
                          fecha=datetime(2026, 6, 1, tzinfo=UTC), tipo="issued"),
        ]
        db.add_all(invs)
        await db.commit()

        result = await build_modelo_347_data(db, tenant.id, year=2026)
        assert result["modelo"] == "347"
        assert result["umbral_legal"] == float(MODELO_347_THRESHOLD)
        assert result["num_declarables"] == 1
        nifs_declarables = {d["nif"] for d in result["declarables"]}
        assert nifs_declarables == {"B11111111"}

    async def test_agrupa_emitidas_y_recibidas_por_nif(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cp = Client(tenant_id=tenant.id, nif="B33333333", name="Contraparte")
        db.add(cp)
        await db.flush()

        # Cuatro facturas de la misma contraparte mixtas (emitidas + recibidas)
        invs = [
            _make_invoice(tenant.id, cp.id, total=Decimal("2000"), base=Decimal("1653"), tax=Decimal("347"),
                          fecha=datetime(2026, 3, 1, tzinfo=UTC), tipo="issued"),
            _make_invoice(tenant.id, cp.id, total=Decimal("2000"), base=Decimal("1653"), tax=Decimal("347"),
                          fecha=datetime(2026, 9, 1, tzinfo=UTC), tipo="issued"),
            _make_invoice(tenant.id, cp.id, total=Decimal("1500"), base=Decimal("1240"), tax=Decimal("260"),
                          fecha=datetime(2026, 4, 1, tzinfo=UTC), tipo="received"),
            _make_invoice(tenant.id, cp.id, total=Decimal("2000"), base=Decimal("1653"), tax=Decimal("347"),
                          fecha=datetime(2026, 10, 1, tzinfo=UTC), tipo="received"),
        ]
        db.add_all(invs)
        await db.commit()

        result = await build_modelo_347_data(db, tenant.id, year=2026)
        assert result["num_declarables"] == 1
        entry = result["declarables"][0]
        assert entry["nif"] == "B33333333"
        assert entry["importe_emitidas"] == 4000.0
        assert entry["importe_recibidas"] == 3500.0


@pytest.mark.asyncio
class TestModelo390:
    async def test_agrega_iva_anual_por_tipo(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        c = Client(tenant_id=tenant.id, nif="B44444444", name="Cliente 390")
        db.add(c)
        await db.flush()

        # Una factura emitida con base 1000 al 21%
        inv = _make_invoice(
            tenant.id, c.id, total=Decimal("1210"), base=Decimal("1000"), tax=Decimal("210"),
            fecha=datetime(2026, 5, 1, tzinfo=UTC), tipo="issued",
        )
        db.add(inv)
        await db.flush()
        line = _make_line(qty=1, price=Decimal("1000"), tax_pct=21.0)
        line.invoice_id = inv.id
        db.add(line)
        await db.commit()

        result = await build_modelo_390_data(db, tenant.id, year=2026)
        assert result["modelo"] == "390"
        assert result["ejercicio"] == 2026
        # Debe haber al menos una entrada al 21% en devengado.
        assert any(e["rate"] == 21.0 for e in result["iva_devengado"])
        devengado_21 = next(e for e in result["iva_devengado"] if e["rate"] == 21.0)
        assert devengado_21["base"] == 1000.0
        assert devengado_21["quota"] == 210.0
        assert result["total_devengado"] == 210.0

    async def test_sin_facturas_devuelve_ceros(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        result = await build_modelo_390_data(db, tenant.id, year=2026)
        assert result["modelo"] == "390"
        assert result["iva_devengado"] == []
        assert result["iva_deducible"] == []
        assert result["total_devengado"] == 0
        assert result["total_deducible"] == 0
        assert result["resultado_anual"] == 0
