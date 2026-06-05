"""Tests del desglose de IVA por tipo (modelos 303 trimestral y 390 anual).

`vat_breakdown_by_rate` centraliza la aritmética del IVA de los modelos fiscales
con Decimal, para (a) no arrastrar el error de redondeo del float y (b) que el
303 y el 390 cuadren entre sí al usar exactamente la misma lógica. Es el camino
del dinero que se presenta a Hacienda, así que se valida con precisión.
"""

from decimal import Decimal

from app.services.reports.fiscal import _round2, vat_breakdown_by_rate


class _Line:
    def __init__(self, quantity, unit_price, tax_percentage, discount_percentage=0):
        self.quantity = quantity
        self.unit_price = unit_price
        self.tax_percentage = tax_percentage
        self.discount_percentage = discount_percentage


class _Invoice:
    def __init__(self, lines):
        self.lines = lines


def _rate(m, r):
    return m[Decimal(str(r))]


def test_linea_simple():
    m = vat_breakdown_by_rate([_Invoice([_Line(2, 100, 21)])])
    assert _round2(_rate(m, 21)["base"]) == Decimal("200.00")
    assert _round2(_rate(m, 21)["quota"]) == Decimal("42.00")


def test_descuento():
    m = vat_breakdown_by_rate([_Invoice([_Line(1, 100, 21, 10)])])
    assert _round2(_rate(m, 21)["base"]) == Decimal("90.00")
    assert _round2(_rate(m, 21)["quota"]) == Decimal("18.90")


def test_multitipo():
    m = vat_breakdown_by_rate([_Invoice([_Line(1, 100, 21), _Line(1, 50, 10)])])
    assert _round2(_rate(m, 21)["quota"]) == Decimal("21.00")
    assert _round2(_rate(m, 10)["quota"]) == Decimal("5.00")


def test_decimal_sin_arrastre_float():
    # 3 líneas de 0.10 al 21%: base 0.30, cuota 0.063 → 0.06 con ROUND_HALF_UP.
    m = vat_breakdown_by_rate(
        [_Invoice([_Line(1, Decimal("0.10"), 21) for _ in range(3)])]
    )
    assert _round2(_rate(m, 21)["base"]) == Decimal("0.30")
    assert _round2(_rate(m, 21)["quota"]) == Decimal("0.06")


def test_iva_por_defecto_21_si_falta():
    m = vat_breakdown_by_rate([_Invoice([_Line(1, 100, None)])])
    assert _round2(_rate(m, 21)["quota"]) == Decimal("21.00")


def test_tipo_cero_no_genera_cuota():
    m = vat_breakdown_by_rate([_Invoice([_Line(1, 100, 0)])])
    assert _round2(_rate(m, 0)["base"]) == Decimal("100.00")
    assert _round2(_rate(m, 0)["quota"]) == Decimal("0.00")


def test_303_y_390_usan_la_misma_logica():
    # El 390 anual debe ser la suma de los trimestres: misma función, mismo
    # resultado para el mismo conjunto de facturas.
    facturas = [_Invoice([_Line(2, 100, 21), _Line(1, 50, 10)])]
    a = vat_breakdown_by_rate(facturas)
    b = vat_breakdown_by_rate(facturas)
    assert {k: (_round2(v["base"]), _round2(v["quota"])) for k, v in a.items()} == {
        k: (_round2(v["base"]), _round2(v["quota"])) for k, v in b.items()
    }


def test_agrega_varias_facturas_por_tipo():
    facturas = [
        _Invoice([_Line(1, 100, 21)]),
        _Invoice([_Line(1, 200, 21)]),
        _Invoice([_Line(1, 50, 10)]),
    ]
    m = vat_breakdown_by_rate(facturas)
    assert _round2(_rate(m, 21)["base"]) == Decimal("300.00")
    assert _round2(_rate(m, 21)["quota"]) == Decimal("63.00")
    assert _round2(_rate(m, 10)["base"]) == Decimal("50.00")
