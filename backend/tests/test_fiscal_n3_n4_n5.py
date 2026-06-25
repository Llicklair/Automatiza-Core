"""Regresión de la tanda fiscal N3/N4/N5 (auditoría 2026-06-25).

- N3: el asiento de nómina incluye la cuota patronal de SS (642) y la 476 recoge
      worker + empresa; el coste real de personal deja de estar infravalorado.
- N4: el Modelo 130 resta las retenciones de IRPF soportadas (casilla 06) en vez
      de forzarlas a 0; el autónomo no paga de más.
- N5: el DesgloseIVA del registro VeriFactu resta el descuento de línea, igual que
      compute_invoice_totals / vat_breakdown_by_rate (antes usaba la base bruta).
"""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import select

from app.db.models.accounting import JournalLine
from app.db.models.billing import Invoice
from app.db.models.crm import Client
from app.db.models.hr import Employee, Payroll
from app.services.aeat.casillas_130 import build_casillas_130
from app.services.billing.auto_accounting import create_payroll_journal_entry
from app.services.billing.registro_facturacion import _detalles
from app.services.reports.modelos_aeat import build_modelo_130_data

# ─── N3: cuota patronal de SS (642) en el asiento de nómina ───────────────────


async def test_asiento_nomina_incluye_cuota_patronal_642(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    emp = Employee(tenant_id=tenant.id, name="Ana Pérez")
    db.add(emp)
    await db.flush()
    payroll = Payroll(
        tenant_id=tenant.id,
        employee=emp,  # en memoria → evita lazy-load async en la función
        period_start=datetime(2026, 5, 1, tzinfo=UTC),
        period_end=datetime(2026, 5, 31, tzinfo=UTC),
        issue_date=datetime(2026, 5, 31, tzinfo=UTC),
        base_salary=Decimal("2000"),
        gross_salary=Decimal("2000"),
        ss_contingencias_comunes=Decimal("100"),
        ss_desempleo=Decimal("30"),
        ss_formacion_profesional=Decimal("2"),
        ss_mei=Decimal("2"),  # SS trabajador = 134
        irpf=Decimal("300"),
        net_salary=Decimal("1566"),  # 2000 - 134 - 300
        cuotas_empresa_json={"cc": 500, "desempleo": 100, "fp": 6, "mei": 10, "at_ep": 40, "fogasa": 4},
    )
    db.add(payroll)
    await db.commit()

    entry = await create_payroll_journal_entry(db, tenant.id, payroll)
    assert entry is not None

    res = await db.execute(select(JournalLine).where(JournalLine.entry_id == entry.id))
    lines = {ln.account_code: ln for ln in res.scalars().all()}

    assert "642" in lines  # SS a cargo de la empresa (antes no existía)
    assert float(lines["642"].debit) == 660.0  # suma de cuotas_empresa_json
    assert float(lines["476"].credit) == 794.0  # SS trabajador 134 + empresa 660
    total_debit = sum(float(ln.debit or 0) for ln in lines.values())
    total_credit = sum(float(ln.credit or 0) for ln in lines.values())
    assert total_debit == total_credit == 2660.0  # el asiento cuadra


# ─── N4: el Modelo 130 resta las retenciones soportadas ───────────────────────


async def test_modelo_130_resta_retenciones_soportadas(db, seed_tenant_and_user):
    tenant, _u, _t = seed_tenant_and_user
    cli = Client(tenant_id=tenant.id, name="Cliente", nif="B12345678")
    db.add(cli)
    await db.flush()
    db.add(Invoice(
        tenant_id=tenant.id, client_id=cli.id, date=datetime(2026, 5, 1, tzinfo=UTC),
        amount_base=Decimal("10000"), amount_total=Decimal("12100"), invoice_type="issued",
        status="pending", retencion_irpf_amount=Decimal("1500"),
    ))
    db.add(Invoice(
        tenant_id=tenant.id, client_id=cli.id, date=datetime(2026, 4, 1, tzinfo=UTC),
        amount_base=Decimal("2000"), amount_total=Decimal("2420"), invoice_type="received",
        status="pending",
    ))
    await db.commit()

    data = await build_modelo_130_data(db, tenant.id, quarter=2, year=2026)
    # beneficio 8000 → 20% = 1600 bruto ; retenciones 1500 → resultado 100
    assert data["retenciones_soportadas"] == 1500.0
    assert data["pago_fraccionado_bruto"] == 1600.0
    assert data["resultado_a_ingresar"] == 100.0

    cas = {c.codigo: float(c.valor) for c in build_casillas_130(data)}
    assert cas["06"] == 1500.0  # retenciones soportadas
    assert cas["07"] == 100.0   # casilla 04 − 05 − 06 = 1600 − 0 − 1500


# ─── N5: el desglose VeriFactu resta el descuento de línea ─────────────────────


def test_detalles_verifactu_resta_descuento_de_linea():
    inv = SimpleNamespace(amount_base=Decimal("90"), tax_amount=Decimal("18.90"))
    lines = [SimpleNamespace(
        tax_percentage=Decimal("21"), quantity=Decimal("1"),
        unit_price=Decimal("100"), discount_percentage=Decimal("10"),
    )]
    dets = _detalles(inv, lines)

    assert len(dets) == 1
    assert dets[0].tipo == "21"
    assert dets[0].base == "90.00"   # 100 − 10% (antes daba 100.00 = base inflada)
    assert dets[0].cuota == "18.90"  # 90 × 21%
