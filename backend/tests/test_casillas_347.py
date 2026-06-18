"""Tests del mapeo de casillas del Modelo 347 (hoja-resumen: 01-04)."""
from decimal import Decimal

from app.services.aeat.casillas_347 import build_casillas_347


def _cmap(data: dict) -> dict:
    return {c.codigo: c for c in build_casillas_347(data)}


def test_set_completo():
    assert set(_cmap({})) == {"01", "02", "03", "04"}


def test_recuento_e_importe_desde_lista():
    data = {"declarables": [
        {"importe_emitidas": 5000.0, "importe_recibidas": 0.0},
        {"importe_emitidas": 0.0, "importe_recibidas": 4000.0},
    ]}
    c = _cmap(data)
    assert c["01"].valor == Decimal("2")
    assert c["02"].valor == Decimal("9000.00")      # 5000 + 4000


def test_num_declarables_explicito_prioriza():
    c = _cmap({"declarables": [{}], "num_declarables": 7})
    assert c["01"].valor == Decimal("7")


def test_arrendamientos_local_negocio_editables_a_cero():
    c = _cmap({})
    assert c["03"].editable and c["04"].editable
    assert c["03"].valor == Decimal("0.00")
    assert c["04"].valor == Decimal("0.00")
    assert c["03"].formato == "numero"


def test_recuento_se_formatea_como_numero():
    c = _cmap({})
    assert c["01"].formato == "numero"
    assert c["02"].formato == "euro"
