"""Tests del mapeo de casillas del Modelo 190 (hoja-resumen: 01/02/03)."""
from decimal import Decimal

from app.services.aeat.casillas_190 import build_casillas_190


def _cmap(data: dict) -> dict:
    return {c.codigo: c for c in build_casillas_190(data)}


def test_set_completo():
    assert set(_cmap({})) == {"01", "02", "03"}


def test_recuento_y_totales_desde_lista():
    data = {"perceptores": [
        {"percepcion_integra": 1000.0, "retencion_practicada": 150.0},
        {"percepcion_integra": 2000.0, "retencion_practicada": 300.0},
    ]}
    c = _cmap(data)
    assert c["01"].valor == Decimal("2")            # nº perceptores
    assert c["02"].valor == Decimal("3000.00")      # Σ percepción íntegra
    assert c["03"].valor == Decimal("450.00")       # Σ retención


def test_totales_explicitos_priorizan_sobre_la_lista():
    data = {"perceptores": [{"percepcion_integra": 1.0}],
            "num_perceptores": 5, "total_percepcion_integra": 9999.0,
            "total_retencion_practicada": 100.0}
    c = _cmap(data)
    assert c["01"].valor == Decimal("5")
    assert c["02"].valor == Decimal("9999.00")
    assert c["03"].valor == Decimal("100.00")


def test_recuento_se_formatea_como_numero():
    c = _cmap({})
    assert c["01"].formato == "numero"
    assert c["02"].formato == "euro"


def test_tolera_datos_ausentes():
    c = _cmap({})
    assert c["01"].valor == Decimal("0.00")
    assert c["02"].valor == Decimal("0.00")
    assert c["03"].valor == Decimal("0.00")
