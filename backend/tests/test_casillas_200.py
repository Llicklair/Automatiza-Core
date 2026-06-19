"""Tests del mapeo de casillas clave del Modelo 200 (Impuesto sobre Sociedades)."""
from decimal import Decimal

from app.services.aeat.casillas_200 import build_casillas_200


def _cmap(data: dict) -> dict:
    return {c.codigo: c for c in build_casillas_200(data)}


def test_set_completo():
    assert set(_cmap({})) == {
        "00500", "00552", "00558", "00562", "00592", "00601", "00621",
    }


def test_mapeo_de_la_liquidacion():
    data = {"resultado_contable": 100000.0, "base_imponible": 90000.0,
            "tipo_impositivo_pct": 25.0, "cuota_integra": 22500.0,
            "pagos_fraccionados_pagados": 5000.0, "resultado_declaracion": 17500.0}
    c = _cmap(data)
    assert c["00500"].valor == Decimal("100000.00")
    assert c["00552"].valor == Decimal("90000.00")
    assert c["00558"].valor == Decimal("25.00")
    assert c["00562"].valor == Decimal("22500.00")
    assert c["00621"].valor == Decimal("17500.00")


def test_tipo_de_gravamen_es_porcentaje():
    assert _cmap({})["00558"].formato == "porcentaje"


def test_cuota_liquida_coincide_con_integra_y_es_editable():
    c = _cmap({"cuota_integra": 22500.0})
    assert c["00592"].valor == Decimal("22500.00")
    assert c["00592"].editable
    assert c["00601"].editable


def test_tolera_datos_ausentes():
    c = _cmap({})
    assert c["00500"].valor == Decimal("0.00")
    assert c["00621"].valor == Decimal("0.00")
