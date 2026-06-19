"""Tests deterministas del cálculo del Modelo 303 (liquidación trimestral IVA).

El 303 ya está implementado (services/reports/fiscal.build_modelo_303_data →
services/aeat/casillas_303.build_casillas_303 → expediente_303). Es un cálculo
fiscal legalmente sensible y NO tenía tests. Estos fijan la matemática de las
casillas (régimen general) contra facturas de ejemplo, para detectar regresiones.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Invoice, InvoiceLine, Tenant
from app.services.aeat import build_expediente_303
from app.services.aeat.casillas_303 import build_casillas_303
from app.services.reports.fiscal import build_modelo_303_data


async def _add_invoice(db, tenant_id, client_id, number, inv_type, lines):
    """lines: list of (unit_price, tax_percentage)."""
    inv = Invoice(
        id=uuid4(),
        tenant_id=tenant_id,
        client_id=client_id,
        invoice_number=number,
        date=datetime(2026, 5, 15, tzinfo=UTC),  # Q2 2026
        amount_base=Decimal("0"),
        tax_amount=Decimal("0"),
        amount_total=Decimal("0"),
        status="draft",
        invoice_type=inv_type,
    )
    db.add(inv)
    await db.flush()
    for desc, (unit_price, rate) in enumerate(lines):
        db.add(
            InvoiceLine(
                invoice_id=inv.id,
                description=f"L{desc}",
                quantity=1,
                unit_price=Decimal(str(unit_price)),
                tax_percentage=Decimal(str(rate)),
                total=Decimal(str(unit_price)) * (1 + Decimal(str(rate)) / 100),
            )
        )


async def _seed_quarter() -> str:
    """Q2 2026: emitidas 1000€@21% + 500€@10%; recibida 200€@21%."""
    async with AsyncSessionLocal() as db:
        tenant = Tenant(
            id=uuid4(), name="IVA Test S.L.", nif=f"B{str(uuid4().int)[:8]}", plan="starter"
        )
        db.add(tenant)
        await db.flush()
        client = Client(id=uuid4(), tenant_id=tenant.id, name="Cliente X", nif="B12345678")
        db.add(client)
        await db.flush()
        await _add_invoice(db, tenant.id, client.id, "FAC-1", "issued", [(1000, 21), (500, 10)])
        await _add_invoice(db, tenant.id, client.id, "REC-1", "received", [(200, 21)])
        await db.commit()
        return str(tenant.id)


async def test_modelo_303_casillas_regimen_general():
    tenant_id = await _seed_quarter()
    async with AsyncSessionLocal() as db:
        data = await build_modelo_303_data(db, UUID(tenant_id), quarter=2, year=2026)
    cas = {c.codigo: float(c.valor) for c in build_casillas_303(data)}

    # IVA devengado (emitidas)
    assert cas["07"] == 1000.0  # base 21%
    assert cas["09"] == 210.0   # cuota 21%
    assert cas["04"] == 500.0   # base 10%
    assert cas["06"] == 50.0    # cuota 10%
    assert cas["01"] == 0.0     # base 4% (sin operaciones)
    assert cas["27"] == 260.0   # total cuota devengada = 210 + 50

    # IVA deducible (recibidas)
    assert cas["28"] == 200.0   # base soportada
    assert cas["29"] == 42.0    # cuota soportada (200 * 21%)
    assert cas["45"] == 42.0    # total a deducir

    # Resultado
    assert cas["46"] == 218.0   # 260 - 42
    assert cas["71"] == 218.0   # resultado de la autoliquidación


async def test_modelo_303_empty_quarter_is_zero():
    tenant_id = await _seed_quarter()  # facturas en Q2 → Q1 vacío
    async with AsyncSessionLocal() as db:
        data = await build_modelo_303_data(db, UUID(tenant_id), quarter=1, year=2026)
    cas = {c.codigo: float(c.valor) for c in build_casillas_303(data)}
    assert cas["27"] == 0.0
    assert cas["45"] == 0.0
    assert cas["71"] == 0.0


async def test_expediente_303_bundle():
    tenant_id = await _seed_quarter()
    async with AsyncSessionLocal() as db:
        exp = await build_expediente_303(db, UUID(tenant_id), quarter=2, year=2026)

    assert exp["resumen"]["resultado"] == 218.0
    assert exp["resumen"]["signo"] == "ingresar"  # resultado > 0
    assert exp["periodo"] == "2T 2026"
    assert exp["casillas"]            # no vacío
    assert "<" in exp["xml"]          # XML generado
    assert len(exp["checklist"]) >= 1


def test_303_tipo_no_estandar_no_se_pierde_en_la_27():
    """Regresión C2: la cuota de un tipo fuera de 4/10/21 (p.ej. IVA reducido
    temporal al 5%) NO debe desaparecer del total devengado (casilla 27).

    El 303 oficial no tiene fila para el 5%, así que NO se inventa casilla: la
    cuota se suma a la 27 y se avisa por nota para revisión manual.
    """
    data = {
        "tenant": {},
        "quarter": 2,
        "year": 2026,
        "vat_collected": [
            {"rate": 21.0, "base": 1000.0, "quota": 210.0},
            {"rate": 5.0, "base": 1000.0, "quota": 50.0},  # tipo reducido temporal
        ],
        "vat_deducted": [],
    }
    casillas = build_casillas_303(data)
    cas = {c.codigo: c for c in casillas}

    # La cuota del 21% sigue en su casilla; el 5% no inventa casilla nueva.
    assert float(cas["09"].valor) == 210.0
    assert not any(c.codigo in {"03", "06"} and float(c.valor) == 50.0 for c in casillas)

    # Pero la 27 incluye AMBAS cuotas (210 + 50) y lleva nota de aviso.
    assert float(cas["27"].valor) == 260.0
    assert cas["27"].nota is not None and "5%" in cas["27"].nota


def test_303_tipos_estandar_sin_nota_en_la_27():
    """Sin tipos atípicos, la 27 no debe arrastrar ninguna nota de aviso."""
    data = {
        "tenant": {},
        "quarter": 2,
        "year": 2026,
        "vat_collected": [{"rate": 21.0, "base": 1000.0, "quota": 210.0}],
        "vat_deducted": [],
    }
    cas = {c.codigo: c for c in build_casillas_303(data)}
    assert float(cas["27"].valor) == 210.0
    assert cas["27"].nota is None
