"""Tests de los builders de casillas oficiales: 111, 115, 390.

Blindan la aritmética que, si falla, descuadra la autoliquidación.
"""
from decimal import Decimal

from app.services.aeat.casillas_111 import build_casillas_111
from app.services.aeat.casillas_115 import build_casillas_115
from app.services.aeat.casillas_390 import build_casillas_390


def _m(builder, data: dict) -> dict:
    return {c.codigo: c for c in builder(data)}


# ── Modelo 111 ────────────────────────────────────────────────────────────────

def test_111_total_liquidacion():
    c = _m(build_casillas_111, {"num_perceptores": 3, "total_base_retenciones": 9000.0,
                                "total_retencion_practicada": 1350.0})
    assert c["01"].valor == Decimal("3.00") and c["01"].formato == "numero"
    assert c["03"].valor == Decimal("1350.00")
    assert c["28"].valor == Decimal("1350.00")   # 03 + 09(0)
    assert c["30"].valor == Decimal("1350.00")   # 28 - 29(0)


def test_111_complementaria_resta():
    c = _m(build_casillas_111, {"num_perceptores": 1, "total_base_retenciones": 1000.0,
                                "total_retencion_practicada": 150.0, "a_deducir_complementaria": 50.0})
    assert c["30"].valor == Decimal("100.00")    # 150 - 50


# ── Modelo 115 ────────────────────────────────────────────────────────────────

def test_115_resultado_es_casilla_03():
    c = _m(build_casillas_115, {"num_arrendadores": 1, "total_base_retenciones": 1000.0,
                                "total_retencion_practicada": 190.0})
    assert c["01"].formato == "numero"
    assert c["03"].valor == Decimal("190.00")
    assert c["05"].valor == Decimal("190.00")    # 03 - 04(0)


# ── Modelo 390 ────────────────────────────────────────────────────────────────

def test_390_devengado_deducible_resultado():
    data = {
        "iva_devengado": [{"rate": 21.0, "base": 10000.0, "quota": 2100.0}],
        "iva_deducible": [{"rate": 21.0, "base": 4000.0, "quota": 840.0}],
        "total_devengado": 2100.0, "total_deducible": 840.0, "resultado_anual": 1260.0,
    }
    c = _m(build_casillas_390, data)
    assert c["05"].valor == Decimal("10000.00")  # base 21%
    assert c["06"].valor == Decimal("2100.00")   # cuota 21%
    assert c["47"].valor == Decimal("2100.00")   # total cuota devengada
    assert c["64"].valor == Decimal("840.00")    # total a deducir
    assert c["65"].valor == Decimal("1260.00")   # 47 - 64
    assert c["86"].valor == Decimal("1260.00")   # resultado anual
