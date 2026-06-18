"""Tests del mapeo de casillas clave del Modelo 100 (IRPF, Renta 2024/2025)."""
from decimal import Decimal

from app.services.aeat.casillas_100 import build_casillas_100


def _cmap(data: dict) -> dict:
    return {c.codigo: c for c in build_casillas_100(data)}


def test_set_completo():
    assert set(_cmap({})) == {
        "0224", "0500", "0519", "0595", "0596", "0604", "0670",
    }


def test_mapeo_de_la_liquidacion():
    data = {"rendimiento_neto": 40000.0, "base_liquidable": 35000.0,
            "minimo_personal": 5550.0, "cuota_integra": 8000.0,
            "retenciones_soportadas": 3000.0, "pagos_fraccionados_pagados": 2000.0,
            "resultado_declaracion": 3000.0}
    c = _cmap(data)
    assert c["0224"].valor == Decimal("40000.00")
    assert c["0500"].valor == Decimal("35000.00")
    assert c["0519"].valor == Decimal("5550.00")
    assert c["0595"].valor == Decimal("8000.00")
    assert c["0604"].valor == Decimal("2000.00")
    assert c["0670"].valor == Decimal("3000.00")


def test_editables_marcados():
    c = _cmap({})
    for cod in ("0519", "0595", "0596"):
        assert c[cod].editable, cod
    assert not c["0224"].editable
    assert not c["0500"].editable
    assert not c["0670"].editable


def test_tolera_datos_ausentes():
    c = _cmap({})
    assert c["0224"].valor == Decimal("0.00")
    assert c["0670"].valor == Decimal("0.00")
