"""Tests de `build_casillas_130`: mapeo del cálculo a las casillas oficiales 130.

Protegen las reglas de cálculo del Modelo 130 (las que, si fallan, descuadran la
autoliquidación): 03 = 01−02, 04 = 20%·03 (nunca negativa), 07 = 04−05−06,
19 = resultado, y el marcado de casillas editables.
"""
from decimal import Decimal

from app.services.aeat.casillas_130 import build_casillas_130


def _cmap(data: dict) -> dict:
    return {c.codigo: c for c in build_casillas_130(data)}


def test_casilla_03_es_ingresos_menos_gastos():
    c = _cmap({"ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0})
    assert c["01"].valor == Decimal("12000.00")
    assert c["02"].valor == Decimal("4000.00")
    assert c["03"].valor == Decimal("8000.00")


def test_casilla_04_es_20_pct_del_rendimiento():
    c = _cmap({"ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0})
    assert c["04"].valor == Decimal("1600.00")  # 20% de 8000


def test_casilla_04_nunca_es_negativa():
    c = _cmap({"ingresos_acumulados": 1000.0, "gastos_acumulados": 4000.0})
    assert c["03"].valor == Decimal("-3000.00")
    assert c["04"].valor == Decimal("0.00")


def test_casilla_07_resta_pagos_y_retenciones():
    c = _cmap({
        "ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0,
        "pagos_fraccionados_anteriores": 400.0, "retenciones_soportadas": 200.0,
    })
    # 04 = 1600 ; 07 = 1600 − 400 − 200 = 1000
    assert c["07"].valor == Decimal("1000.00")


def test_casilla_19_resultado_final_sin_deducciones():
    c = _cmap({"ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0})
    # sin pagos previos ni deducciones: 19 == 04 == 1600
    assert c["19"].valor == Decimal("1600.00")


def test_casillas_editables_marcadas():
    c = _cmap({"ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0})
    for cod in ("05", "06", "13", "15", "16", "18"):
        assert c[cod].editable is True, f"la casilla {cod} debe ser editable"
    for cod in ("01", "02", "03", "04", "07", "12", "14", "17", "19"):
        assert c[cod].editable is False, f"la casilla {cod} no debe ser editable"


def test_set_completo_de_casillas():
    # Apartado I (01-07) + Apartado III (12-19). El Apartado II (08-11) se omite.
    c = _cmap({"ingresos_acumulados": 0.0, "gastos_acumulados": 0.0})
    assert set(c.keys()) == {
        "01", "02", "03", "04", "05", "06", "07",
        "12", "13", "14", "15", "16", "17", "18", "19",
    }


def test_tolera_datos_ausentes():
    # No debe reventar con dict mínimo (todas las casillas a 0).
    c = _cmap({})
    assert c["03"].valor == Decimal("0.00")
    assert c["19"].valor == Decimal("0.00")
