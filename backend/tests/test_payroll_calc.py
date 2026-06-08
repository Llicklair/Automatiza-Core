"""Tests del cálculo de nómina: tope de base máxima y cuota de solidaridad.

Lógica pura (sin BD). ``calc_payroll`` es la ÚNICA fuente de verdad del cálculo
de SS, IRPF y cuota de solidaridad; la usan tanto la API como los agentes IA.

Cubre:
  - Tope de base máxima mensual: la SS no cotiza por encima del tope.
  - IRPF retenido sobre el salario íntegro (sin topar).
  - Cuota de solidaridad (desde 2025): cotización extra del trabajador sobre el
    exceso del tope, por tramos.

Topes (BOE): 2024 = 4.720,50 · 2025 = 4.909,50 · 2026 = 5.101,20 €/mes.
"""

from app.services.hr.queries import (
    base_maxima_cotizacion,
    calc_payroll,
    cuota_solidaridad_trabajador,
)

# Tasas empleado (Régimen General).
_CC, _DES, _FP, _MEI = 0.0470, 0.0155, 0.0010, 0.0010
# Proporción trabajador de la cuota de solidaridad (= proporción de CC).
_FRAC_TRAB = 0.0470 / 0.2830


# ─── Tope de base máxima ──────────────────────────────────────────────────────


def test_topes_por_ano():
    assert base_maxima_cotizacion(2024) == 4720.50
    assert base_maxima_cotizacion(2025) == 4909.50
    assert base_maxima_cotizacion(2026) == 5101.20
    assert base_maxima_cotizacion(None) == base_maxima_cotizacion(2026)
    assert base_maxima_cotizacion(1999) == base_maxima_cotizacion(2026)


def test_por_debajo_del_tope_no_cambia_la_cotizacion():
    c = calc_payroll(2000, 15, year=2025)
    assert c["base_cotizacion"] == 2000.0
    assert c["ss_contingencias_comunes"] == round(2000 * _CC, 2)
    assert c["irpf"] == round(2000 * 0.15, 2)
    assert c["cuota_solidaridad"] == 0.0


def test_por_encima_del_tope_cotiza_sobre_el_tope():
    c = calc_payroll(6000, 15, year=2025)
    assert c["base_cotizacion"] == 4909.50
    assert c["ss_contingencias_comunes"] == round(4909.50 * _CC, 2)
    assert c["ss_desempleo"] == round(4909.50 * _DES, 2)
    assert c["total_ss"] < round(6000 * (_CC + _DES + _FP + _MEI), 2)


def test_irpf_no_se_topa():
    c = calc_payroll(6000, 15, year=2025)
    assert c["irpf"] == round(6000 * 0.15, 2)


def test_tope_depende_del_ano():
    c25 = calc_payroll(6000, 15, year=2025)
    c26 = calc_payroll(6000, 15, year=2026)
    assert c25["base_cotizacion"] == 4909.50
    assert c26["base_cotizacion"] == 5101.20
    assert c26["total_ss"] > c25["total_ss"]


def test_exactamente_en_el_tope():
    c = calc_payroll(4909.50, 15, year=2025)
    assert c["base_cotizacion"] == 4909.50
    assert c["cuota_solidaridad"] == 0.0


def test_base_cero_todo_cero():
    c = calc_payroll(0, 15, year=2025)
    for k in (
        "ss_contingencias_comunes",
        "ss_desempleo",
        "ss_formacion_profesional",
        "ss_mei",
        "total_ss",
        "irpf",
        "cuota_solidaridad",
        "net_salary",
        "base_cotizacion",
    ):
        assert c[k] == 0.0, f"{k} debería ser 0"


def test_mei_trabajador_por_ano():
    """El MEI del trabajador sube por año (RD-ley 2/2023): no es fijo."""
    from app.services.hr.queries import mei_trabajador

    assert mei_trabajador(2023) == 0.0010
    assert mei_trabajador(2024) == 0.0012
    assert mei_trabajador(2025) == 0.0013
    assert mei_trabajador(2026) == 0.0015
    # Año desconocido → usa el más reciente conocido.
    assert mei_trabajador(2099) == mei_trabajador(2026)


def test_ss_mei_usa_tipo_del_ano():
    """calc_payroll aplica el MEI del año, no un 0,10 % fijo."""
    c25 = calc_payroll(2000, 15, year=2025)
    c26 = calc_payroll(2000, 15, year=2026)
    assert c25["ss_mei"] == round(2000 * 0.0013, 2)
    assert c26["ss_mei"] == round(2000 * 0.0015, 2)


def test_acepta_year_none_por_defecto():
    c = calc_payroll(2000, 15)
    assert c["base_cotizacion"] == 2000.0


# ─── Cuota de solidaridad ─────────────────────────────────────────────────────


def test_solidaridad_cero_por_debajo_del_tope():
    assert cuota_solidaridad_trabajador(2000, 2025) == 0.0
    assert cuota_solidaridad_trabajador(4909.50, 2025) == 0.0


def test_solidaridad_no_existia_antes_de_2025():
    assert cuota_solidaridad_trabajador(6000, 2024) == 0.0


def test_solidaridad_solo_primer_tramo_2026():
    # 5.300 € está entre la base máxima (5.101,20) y el +10% (5.611,32): tramo 1.
    tope = 5101.20
    portion = 5300 - tope
    esperado = round(portion * 0.0115 * _FRAC_TRAB, 2)
    assert cuota_solidaridad_trabajador(5300, 2026) == esperado
    assert esperado > 0


def test_solidaridad_multitramo_2026():
    # 6.000 € abarca tramo 1 completo (hasta 5.611,32) y parte del tramo 2.
    tope = 5101.20
    t1 = (tope * 1.10 - tope) * 0.0115
    t2 = (6000 - tope * 1.10) * 0.0125
    esperado = round((t1 + t2) * _FRAC_TRAB, 2)
    assert cuota_solidaridad_trabajador(6000, 2026) == esperado
    assert esperado > 0


def test_net_incluye_ss_irpf_y_solidaridad():
    c = calc_payroll(6000, 15, year=2026)
    assert c["cuota_solidaridad"] > 0
    assert c["deductions"] == round(c["total_ss"] + c["irpf"] + c["cuota_solidaridad"], 2)
    assert c["net_salary"] == round(6000 - c["deductions"], 2)
