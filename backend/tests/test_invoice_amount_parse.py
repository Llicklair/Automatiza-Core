"""Tests del parseo de importes de factura (formato español).

`parse_amount_str` convierte cadenas de importe a Decimal aceptando formato
español ('1.500,00') e inglés ('1500.00'). Es lógica pura del camino del dinero
y no tenía test unitario: un fallo aquí significa facturas con importes
incorrectos.
"""

from decimal import Decimal

from app.agents.billing._invoice_validators import parse_amount_str


def test_formato_ingles_simple():
    val, err = parse_amount_str("1500.00")
    assert err is None and val == Decimal("1500.00")


def test_formato_espanol_miles_y_decimales():
    val, err = parse_amount_str("1.500,00")
    assert err is None and val == Decimal("1500.00")


def test_formato_espanol_solo_decimales():
    val, err = parse_amount_str("1500,50")
    assert err is None and val == Decimal("1500.50")


def test_formato_espanol_millones():
    val, err = parse_amount_str("1.234.567,89")
    assert err is None and val == Decimal("1234567.89")


def test_miles_sin_decimales():
    val, err = parse_amount_str("1.500")
    assert err is None and val == Decimal("1500")


def test_entero_simple():
    val, err = parse_amount_str("500")
    assert err is None and val == Decimal("500")


def test_con_espacios():
    val, err = parse_amount_str("  250,5  ")
    assert err is None and val == Decimal("250.5")


def test_no_numerico_devuelve_error_y_cero():
    val, err = parse_amount_str("abc")
    assert err is not None and val == Decimal("0")


def test_vacio_devuelve_error():
    val, err = parse_amount_str("")
    assert err is not None and val == Decimal("0")
