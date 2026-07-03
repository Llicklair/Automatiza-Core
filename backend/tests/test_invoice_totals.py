"""Tests del cálculo de importes de factura (compute_invoice_totals).

Lógica pura del camino del dinero: valida el IVA por línea y calcula base, IVA
y total con Decimal (sin arrastre de float). Se usa para validar la factura
ANTES de consumir un número correlativo (evitando huecos/huérfanas).
"""

import pytest

from app.services.billing.queries import compute_invoice_totals


def test_linea_simple():
    r = compute_invoice_totals([{"quantity": 2, "unit_price": 100, "tax_percentage": 21}])
    assert r["amount_base"] == 200.0
    assert r["tax_amount"] == 42.0
    assert r["amount_total"] == 242.0


def test_descuento():
    r = compute_invoice_totals([{"quantity": 1, "unit_price": 100, "discount_percentage": 10, "tax_percentage": 21}])
    assert r["amount_base"] == 90.0
    assert r["tax_amount"] == 18.9
    assert r["amount_total"] == 108.9


# ── Validación de rango de línea (audit ERP 2026-07-03) ──────────────────


def test_descuento_fuera_de_rango_rechazado():
    with pytest.raises(ValueError, match="Descuento por línea fuera de rango"):
        compute_invoice_totals([{"quantity": 1, "unit_price": 100, "discount_percentage": 150}])
    with pytest.raises(ValueError, match="Descuento por línea fuera de rango"):
        compute_invoice_totals([{"quantity": 1, "unit_price": 100, "discount_percentage": -5}])


def test_linea_base_negativa_rechazada_en_factura_ordinaria():
    # Una línea con cantidad negativa que se camufla en un total positivo:
    # antes pasaba (solo se validaba el total agregado); ahora se rechaza.
    with pytest.raises(ValueError, match="base negativa"):
        compute_invoice_totals(
            [
                {"quantity": 1, "unit_price": 100, "tax_percentage": 21},
                {"quantity": -1, "unit_price": 50, "tax_percentage": 21},
            ]
        )


def test_linea_base_negativa_permitida_en_rectificativa():
    # allow_negative=True (abono): las líneas negativas son legítimas.
    r = compute_invoice_totals([{"quantity": 1, "unit_price": -100, "tax_percentage": 21}], allow_negative=True)
    assert r["amount_base"] == -100.0
    assert r["amount_total"] == -121.0


def test_multilinea_iva_mixto():
    r = compute_invoice_totals(
        [
            {"quantity": 1, "unit_price": 100, "tax_percentage": 21},
            {"quantity": 1, "unit_price": 50, "tax_percentage": 10},
        ]
    )
    assert r["amount_base"] == 150.0
    assert r["tax_amount"] == 26.0  # 21 + 5
    assert r["amount_total"] == 176.0


def test_redondeo_decimal_no_float():
    # round(1.005, 2) en float da 1.0 (1.005 no es representable); con Decimal
    # y ROUND_HALF_UP debe dar 1.01. Demuestra que se evita el bug de float.
    r = compute_invoice_totals([{"quantity": 1, "unit_price": 1.005, "tax_percentage": 0}])
    assert r["amount_base"] == 1.01


def test_iva_invalido_lanza():
    with pytest.raises(ValueError):
        compute_invoice_totals([{"quantity": 1, "unit_price": 100, "tax_percentage": 7}])


def test_total_negativo_lanza():
    with pytest.raises(ValueError):
        compute_invoice_totals([{"quantity": 1, "unit_price": -100, "tax_percentage": 21}])


def test_lineas_vacias():
    r = compute_invoice_totals([])
    assert r["amount_base"] == 0.0 and r["tax_amount"] == 0.0 and r["amount_total"] == 0.0


def test_total_por_linea_presente_y_redondeado():
    r = compute_invoice_totals([{"quantity": 3, "unit_price": 0.10, "tax_percentage": 21}])
    line = r["lines"][0]
    assert line["_line_base"] == 0.30  # 3 * 0.10 exacto con Decimal
    assert line["_line_total"] == 0.36  # 0.30 + 0.063 → 0.36
    assert r["amount_total"] == 0.36


def test_iva_por_defecto_21():
    r = compute_invoice_totals([{"quantity": 1, "unit_price": 100}])
    assert r["tax_amount"] == 21.0


def test_total_negativo_permitido_con_flag():
    # allow_negative=True habilita el abono/rectificativa: minora una factura
    # anterior con importes negativos sin tratarlos como error de captura.
    r = compute_invoice_totals(
        [{"quantity": 1, "unit_price": -100, "tax_percentage": 21}],
        allow_negative=True,
    )
    assert r["amount_base"] == -100.0
    assert r["tax_amount"] == -21.0
    assert r["amount_total"] == -121.0


def test_negativo_sigue_validando_iva():
    # El flag solo levanta la guarda de signo: un IVA inválido sigue fallando.
    with pytest.raises(ValueError):
        compute_invoice_totals(
            [{"quantity": 1, "unit_price": -100, "tax_percentage": 7}],
            allow_negative=True,
        )


def test_rectificativa_anula_factura_a_cero():
    # Una rectificativa por anulación (líneas negadas) debe dejar el neto a 0
    # al sumarse con la original: aquí comprobamos que la negación es exacta.
    original = compute_invoice_totals([{"quantity": 2, "unit_price": 100, "tax_percentage": 21}])
    abono = compute_invoice_totals(
        [{"quantity": 2, "unit_price": -100, "tax_percentage": 21}],
        allow_negative=True,
    )
    assert original["amount_total"] + abono["amount_total"] == 0.0
    assert original["amount_base"] + abono["amount_base"] == 0.0
    assert original["tax_amount"] + abono["tax_amount"] == 0.0
