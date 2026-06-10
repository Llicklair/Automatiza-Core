"""Tests M1: regímenes especiales 303 (intra/ISP/recargo), retención Art.95
en el 111, 390 con autoliquidación y validación XSD pre-firma."""
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.db.models.billing import Invoice, InvoiceLine
from app.db.models.crm import Client
from app.services.aeat.casillas_303 import build_casillas_303
from app.services.aeat.xsd_validation import validate_xml_pre_signature
from app.services.reports.fiscal import build_modelo_303_data
from app.services.reports.modelos_aeat import (
    build_modelo_111_data,
    build_modelo_390_data,
)


async def _mk_client(db, tenant_id, name="Proveedor SA", nif="B11111111"):
    cli = Client(tenant_id=tenant_id, name=name, nif=nif)
    db.add(cli)
    await db.flush()
    return cli


async def _mk_invoice(
    db,
    tenant_id,
    client_id,
    *,
    inv_type: str,
    base: str,
    rate: str,
    fiscal_regime: str | None = None,
    retencion_rate: str | None = None,
    number: str | None = None,
    when: datetime = datetime(2026, 5, 15, tzinfo=UTC),  # Q2 2026
) -> Invoice:
    base_d = Decimal(base)
    quota = base_d * Decimal(rate) / 100
    ret = (base_d * Decimal(retencion_rate) / 100) if retencion_rate else None
    inv = Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number or f"T-{uuid4().hex[:8]}",
        date=when,
        amount_base=base_d,
        tax_amount=quota,
        amount_total=base_d + quota,
        status="paid",
        invoice_type=inv_type,
        fiscal_regime=fiscal_regime,
        retencion_irpf_rate=Decimal(retencion_rate) if retencion_rate else None,
        retencion_irpf_amount=ret,
    )
    db.add(inv)
    await db.flush()
    db.add(
        InvoiceLine(
            invoice_id=inv.id,
            description="L1",
            quantity=1,
            unit_price=base_d,
            tax_percentage=Decimal(rate),
            total=base_d + quota,
        )
    )
    return inv


def _casilla(casillas, codigo) -> float:
    return next(float(c.valor) for c in casillas if c.codigo == codigo)


@pytest.mark.asyncio
class TestModelo303Regimenes:
    async def test_intracomunitario_casillas_10_11_36_37(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="1000", rate="21", fiscal_regime="intracomunitario")
        await db.commit()

        data = await build_modelo_303_data(db, tenant.id, quarter=2, year=2026)
        assert data["vat_intra"] == [{"rate": 21.0, "base": 1000.0, "quota": 210.0}]
        assert data["vat_deducted"] == []  # no va al deducible interior

        casillas = build_casillas_303(data)
        assert _casilla(casillas, "10") == 1000.0
        assert _casilla(casillas, "11") == 210.0
        assert _casilla(casillas, "36") == 1000.0
        assert _casilla(casillas, "37") == 210.0
        # Autoliquidación: devengado 210 (27) y deducible 210 (45) → resultado 0
        assert _casilla(casillas, "27") == 210.0
        assert _casilla(casillas, "45") == 210.0
        assert _casilla(casillas, "46") == 0.0

    async def test_isp_casillas_12_13_y_deducible_interior(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="500", rate="21", fiscal_regime="isp")
        await db.commit()

        data = await build_modelo_303_data(db, tenant.id, quarter=2, year=2026)
        assert data["vat_isp"] == [{"rate": 21.0, "base": 500.0, "quota": 105.0}]
        # ISP deducible en operaciones interiores (28/29)
        assert data["vat_deducted"] == [{"rate": 21.0, "base": 500.0, "quota": 105.0}]

        casillas = build_casillas_303(data)
        assert _casilla(casillas, "12") == 500.0
        assert _casilla(casillas, "13") == 105.0
        assert _casilla(casillas, "29") == 105.0
        assert _casilla(casillas, "27") == 105.0
        assert _casilla(casillas, "45") == 105.0
        assert _casilla(casillas, "46") == 0.0

    async def test_recargo_equivalencia_casillas_22_24(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="issued",
                          base="1000", rate="21", fiscal_regime="recargo_equivalencia")
        await db.commit()

        data = await build_modelo_303_data(db, tenant.id, quarter=2, year=2026)
        assert data["recargo_equivalencia"] == [
            {"rate": 21.0, "recargo_rate": 5.2, "base": 1000.0, "quota": 52.0}
        ]

        casillas = build_casillas_303(data)
        # IVA general de la venta sigue en 07/09
        assert _casilla(casillas, "07") == 1000.0
        assert _casilla(casillas, "09") == 210.0
        # Recargo 5.2% en 22/24
        assert _casilla(casillas, "22") == 1000.0
        assert _casilla(casillas, "24") == 52.0
        assert _casilla(casillas, "27") == 262.0  # 210 + 52

    async def test_regresion_sin_regimenes_casillas_nuevas_a_cero(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="issued",
                          base="1000", rate="21")
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="200", rate="21")
        await db.commit()

        data = await build_modelo_303_data(db, tenant.id, quarter=2, year=2026)
        assert data["vat_intra"] == [] and data["vat_isp"] == []
        assert data["recargo_equivalencia"] == []

        casillas = build_casillas_303(data)
        for codigo in ("10", "11", "12", "13", "16", "18", "22", "24", "36", "37"):
            assert _casilla(casillas, codigo) == 0.0
        assert _casilla(casillas, "27") == 210.0
        assert _casilla(casillas, "45") == 42.0
        assert _casilla(casillas, "46") == 168.0


@pytest.mark.asyncio
class TestModelo111Profesionales:
    async def test_retencion_profesional_art95(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id, name="Abogado SLP", nif="B22222222")
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="1000", rate="21", retencion_rate="15")
        await db.commit()

        result = await build_modelo_111_data(db, tenant.id, quarter=2, year=2026)
        assert len(result["perceptores_profesionales"]) == 1
        prof = result["perceptores_profesionales"][0]
        assert prof["nombre"] == "Abogado SLP"
        assert prof["base_retencion"] == 1000.0
        assert prof["retencion_practicada"] == 150.0
        assert result["total_base_profesionales"] == 1000.0
        assert result["total_retencion_profesionales"] == 150.0
        assert result["total_retencion_practicada"] == 150.0
        assert result["num_perceptores"] == 1

    async def test_sin_retencion_no_aparece(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="1000", rate="21")
        await db.commit()

        result = await build_modelo_111_data(db, tenant.id, quarter=2, year=2026)
        assert result["perceptores_profesionales"] == []
        assert result["total_retencion_profesionales"] == 0.0


@pytest.mark.asyncio
class TestModelo390Autoliquidacion:
    async def test_390_incluye_intra_e_isp(self, db, seed_tenant_and_user):
        tenant, _, _ = seed_tenant_and_user
        cli = await _mk_client(db, tenant.id)
        await _mk_invoice(db, tenant.id, cli.id, inv_type="issued",
                          base="1000", rate="21")
        await _mk_invoice(db, tenant.id, cli.id, inv_type="received",
                          base="500", rate="21", fiscal_regime="intracomunitario")
        await db.commit()

        result = await build_modelo_390_data(db, tenant.id, year=2026)
        assert result["iva_intracomunitario"] == [
            {"rate": 21.0, "base": 500.0, "quota": 105.0}
        ]
        # Devengado: 210 (ventas) + 105 (AIB) = 315; deducible: 105 (AIB)
        assert result["total_devengado"] == 315.0
        assert result["total_deducible"] == 105.0
        assert result["resultado_anual"] == 210.0


class TestXsdValidation:
    def test_xml_bien_formado_sin_xsd_pasa(self):
        assert validate_xml_pre_signature("<Modelo303><Casilla/></Modelo303>", "303") == []

    def test_xml_mal_formado_devuelve_error(self):
        errors = validate_xml_pre_signature("<Modelo303><sin_cerrar>", "303")
        assert len(errors) == 1
        assert "mal formado" in errors[0]
