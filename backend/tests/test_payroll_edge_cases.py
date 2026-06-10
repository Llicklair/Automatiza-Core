"""Edge cases de nómina: jornada parcial, pagas extra, horas extra, baja IT y finiquito.

Lógica pura (sin BD). Complementa test_payroll_calc.py (casos base).
"""

from datetime import date

import pytest

from app.services.hr.finiquito import calc_finiquito
from app.services.hr.queries import calc_payroll, it_days_overlap

approx = pytest.approx


# ── Retrocompatibilidad ───────────────────────────────────────────────────────


def test_defaults_reproduce_classic_calc():
    c = calc_payroll(2000, 15, year=2025)
    assert c["gross_salary"] == 2000.0
    assert c["base_cotizacion"] == 2000.0
    assert c["ss_horas_extra"] == 0.0
    assert c["devengos"]["dias_baja_it"] == 0
    # Mismos números que el cálculo clásico
    assert c["ss_contingencias_comunes"] == approx(2000 * 0.047)
    assert c["irpf"] == approx(300.0)


# ── Jornada parcial ───────────────────────────────────────────────────────────


def test_jornada_parcial_prorratea_base():
    c = calc_payroll(2000, 15, year=2025, jornada_pct=50)
    assert c["gross_salary"] == approx(1000.0)
    assert c["base_cotizacion"] == approx(1000.0)
    assert c["ss_contingencias_comunes"] == approx(47.0)
    assert c["irpf"] == approx(150.0)


# ── Pagas extra (12/14) ───────────────────────────────────────────────────────


def test_14_pagas_sin_prorratear_cotiza_prorrata_pero_no_la_devenga():
    c = calc_payroll(1800, 15, year=2025, num_pagas=14, prorratear_pagas=False)
    # Devengo mensual: solo la mensualidad
    assert c["gross_salary"] == approx(1800.0)
    # Base de cotización: mensualidad + prorrata de 2 extras (art. 147 LGSS)
    assert c["base_cotizacion"] == approx(1800 + 300)
    assert c["ss_contingencias_comunes"] == approx(2100 * 0.047)


def test_14_pagas_prorrateadas_suman_al_devengo():
    c = calc_payroll(1800, 15, year=2025, num_pagas=14, prorratear_pagas=True)
    assert c["gross_salary"] == approx(2100.0)
    assert c["base_cotizacion"] == approx(2100.0)
    assert c["devengos"]["prorrata_pagas_extra"] == approx(300.0)
    assert c["irpf"] == approx(2100 * 0.15)


# ── Horas extra ───────────────────────────────────────────────────────────────


def test_horas_extra_cotizan_aparte_y_tributan():
    c = calc_payroll(2000, 15, year=2025, horas_extra_importe=200)
    assert c["gross_salary"] == approx(2200.0)
    assert c["ss_horas_extra"] == approx(200 * 0.047)
    assert c["irpf"] == approx(2200 * 0.15)
    # La base mensual no incluye las horas extra
    assert c["base_cotizacion"] == approx(2000.0)


def test_horas_extra_fuerza_mayor_tipo_reducido():
    c = calc_payroll(2000, 15, year=2025, horas_extra_importe=200, horas_extra_fuerza_mayor=True)
    assert c["ss_horas_extra"] == approx(200 * 0.02)


# ── Baja IT ───────────────────────────────────────────────────────────────────


def test_it_tramos_60_pct():
    # Baja de 10 días que empieza con la nómina: días 1-3 al 0%, 4-10 al 60%
    c = calc_payroll(3000, 15, year=2025, dias_baja_it=10, it_dia_inicio=1)
    # base reguladora diaria = 100; prestación = 7 días * 60 = 420
    assert c["devengos"]["prestacion_it"] == approx(420.0)
    # salario por 20 días trabajados = 2000
    assert c["devengos"]["salario_base"] == approx(2000.0)
    assert c["gross_salary"] == approx(2420.0)
    # La cotización se mantiene sobre la base mensual normal
    assert c["base_cotizacion"] == approx(3000.0)


def test_it_tramo_75_pct_dia_21():
    # Baja que ya va por el día 21: todo el mes al 75%
    c = calc_payroll(3000, 15, year=2025, dias_baja_it=30, it_dia_inicio=21)
    assert c["devengos"]["prestacion_it"] == approx(30 * 100 * 0.75)
    assert c["devengos"]["salario_base"] == approx(0.0)


def test_it_days_overlap_baja_anterior_al_periodo():
    dias, dia_inicio = it_days_overlap(
        date(2026, 5, 20), None, date(2026, 6, 1), date(2026, 6, 30)
    )
    assert dias == 30
    assert dia_inicio == 13  # 1 jun es el día 13 de la baja


def test_it_days_overlap_sin_solape():
    dias, dia_inicio = it_days_overlap(
        date(2026, 7, 5), date(2026, 7, 10), date(2026, 6, 1), date(2026, 6, 30)
    )
    assert dias == 0


# ── Finiquito ─────────────────────────────────────────────────────────────────


def test_finiquito_baja_voluntaria_sin_indemnizacion():
    calc = calc_finiquito(
        base_salary=1800,
        irpf_rate=15,
        num_pagas=12,
        fecha_alta=date(2024, 1, 1),
        fecha_baja=date(2026, 6, 30),
        causa="baja_voluntaria",
        vacaciones_pendientes_dias=10,
        year=2026,
    )
    assert calc["indemnizacion"] == 0.0
    assert calc["vacaciones_pendientes_importe"] == approx(10 * 1800 / 30)
    assert calc["total_liquido"] == approx(
        calc["total_percepciones"] - calc["total_deducciones"]
    )
    # Las vacaciones cotizan y tributan
    assert calc["deduccion_irpf"] == approx(600 * 0.15)
    assert calc["deduccion_ss"] > 0


def test_finiquito_despido_objetivo_20_dias_por_anio():
    calc = calc_finiquito(
        base_salary=2000,
        irpf_rate=15,
        num_pagas=12,
        fecha_alta=date(2021, 6, 30),
        fecha_baja=date(2026, 6, 30),
        causa="despido_objetivo",
        year=2026,
    )
    # ~5 años * 20 días * (24000/365) diario ≈ 6575
    assert calc["indemnizacion"] == approx(5 * 20 * (2000 * 12 / 365), rel=0.01)
    # La indemnización está exenta: no genera IRPF ni SS
    assert calc["deduccion_irpf"] == 0.0
    assert calc["deduccion_ss"] == 0.0


def test_finiquito_improcedente_aplica_tope_24_mensualidades():
    calc = calc_finiquito(
        base_salary=3000,
        irpf_rate=15,
        fecha_alta=date(1990, 1, 1),
        fecha_baja=date(2026, 1, 1),
        causa="despido_improcedente",
        year=2026,
    )
    # 36 años * 33 días superaría con creces el tope de 24 mensualidades
    assert calc["indemnizacion"] == approx(24 * 3000)


def test_finiquito_prorrata_extras_devengada():
    # 14 pagas sin prorratear: a mitad de año hay prorrata pendiente
    calc = calc_finiquito(
        base_salary=1800,
        irpf_rate=15,
        num_pagas=14,
        prorratear_pagas=False,
        fecha_alta=date(2025, 1, 1),
        fecha_baja=date(2026, 7, 1),
        causa="fin_contrato",
        year=2026,
    )
    dia = date(2026, 7, 1).timetuple().tm_yday
    assert calc["prorrata_paga_extra"] == approx(1800 * 2 * dia / 365, rel=0.001)
    assert calc["indemnizacion"] > 0  # 12 días/año en temporales
