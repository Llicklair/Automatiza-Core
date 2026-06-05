"""Tests unitarios de los validadores deterministas de facturación.

Lógica pura (sin BD ni LLM): NIF/CIF/NIE, IBAN módulo-97, tipos de IVA,
importes, fechas y la validación completa de factura.

Cubre especialmente entradas *stringly-typed* que los agentes IA y el parseo de
lenguaje natural pueden entregar (p.ej. ``vat_rate="21"`` o
``amount="1.500,00"``): el validador es el guardián determinista que se ejecuta
ANTES de cualquier LLM, así que no debe reventar ni rechazar valores correctos
por culpa del tipo de dato.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.agents.shared.validators.billing import (
    validate_amount,
    validate_iban,
    validate_invoice_data,
    validate_invoice_date,
    validate_nif,
    validate_vat_rate,
)

# ─── NIF / CIF / NIE ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "nif",
    [
        "12345678Z",  # DNI
        "12345678z",  # minúscula -> se normaliza
        " 12345678Z ",  # espacios -> se recortan
        "X1234567L",  # NIE
        "A58818501",  # CIF (control por dígito)
    ],
)
def test_nif_validos(nif):
    ok, msg = validate_nif(nif)
    assert ok, msg


@pytest.mark.parametrize(
    "nif",
    [
        "12345678A",  # letra de control DNI incorrecta
        "1234567Z",  # longitud incorrecta
        "X1234567Z",  # letra de control NIE incorrecta
        "B12345678",  # dígito de control CIF incorrecto
        "ABCDEFGHI",  # formato CIF inválido
        "ÑØ#@!",  # basura
        "",  # vacío
    ],
)
def test_nif_invalidos(nif):
    ok, _ = validate_nif(nif)
    assert not ok


def test_nif_none_no_revienta():
    ok, _ = validate_nif(None)
    assert not ok


# ─── IBAN ─────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "iban",
    [
        "ES9121000418450200051332",
        "es91 2100 0418 4502 0005 1332",  # minúsculas + espacios
        "GB82WEST12345698765432",  # IBAN genérico (no español) válido
    ],
)
def test_iban_validos(iban):
    ok, msg = validate_iban(iban)
    assert ok, msg


@pytest.mark.parametrize(
    "iban",
    [
        "ES0021000418450200051332",  # dígitos de control mal
        "ES12",  # demasiado corto
        "1234567890123456",  # sin prefijo de país
    ],
)
def test_iban_invalidos(iban):
    ok, _ = validate_iban(iban)
    assert not ok


# ─── IVA ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "rate",
    [0, 4, 10, 21, 21.0, Decimal("21"), "21", "21%", " 10 ", "0"],
)
def test_vat_rate_validos(rate):
    ok, msg = validate_vat_rate(rate)
    assert ok, f"{rate!r} debería ser válido: {msg}"


@pytest.mark.parametrize(
    "rate",
    [5, 7, 22, -21, 21.5, "abc", "", None],
)
def test_vat_rate_invalidos(rate):
    ok, _ = validate_vat_rate(rate)
    assert not ok


def test_vat_rate_normaliza_float_entero():
    # 21.0 debe mostrarse como '21', no '21.0'.
    ok, msg = validate_vat_rate(21.0)
    assert ok and "21%" in msg and "21.0" not in msg


# ─── Importes ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "amount",
    [Decimal("100"), 100, 100.0, "100", "1.500,00", "0.01", Decimal("999999")],
)
def test_amount_validos(amount):
    ok, msg = validate_amount(amount)
    assert ok, f"{amount!r} debería ser válido: {msg}"


def test_amount_formato_espanol_se_interpreta_bien():
    # '1.500,00' son mil quinientos euros, no uno coma cinco.
    from app.agents.shared.validators.billing import _coerce_number

    assert _coerce_number("1.500,00") == Decimal("1500.00")


@pytest.mark.parametrize(
    "amount",
    [Decimal("0"), Decimal("0.005"), Decimal("2000000")],
)
def test_amount_fuera_de_rango(amount):
    ok, _ = validate_amount(amount)
    assert not ok


def test_amount_negativo_mensaje_claro():
    ok, msg = validate_amount(Decimal("-50"))
    assert not ok
    assert "negativo" in msg.lower()


@pytest.mark.parametrize("amount", ["abc", "", None, "1.2.3"])
def test_amount_no_numerico_no_revienta(amount):
    # Antes 'amount' tipo str lanzaba TypeError al comparar con Decimal.
    ok, msg = validate_amount(amount)
    assert not ok
    assert "no numérico" in msg.lower()


# ─── Fechas ───────────────────────────────────────────────────────────────────


def test_fecha_hoy_valida():
    ok, _ = validate_invoice_date(date.today())
    assert ok


@pytest.mark.parametrize(
    "delta_days",
    [-400, 400],  # más de 1 año en pasado / futuro
)
def test_fecha_fuera_de_rango(delta_days):
    ok, _ = validate_invoice_date(date.today() + timedelta(days=delta_days))
    assert not ok


def test_fecha_limite_un_ano_pasado_valida():
    ok, _ = validate_invoice_date(date.today() - timedelta(days=300))
    assert ok


# ─── Validación completa de factura ───────────────────────────────────────────


def test_invoice_data_valida_sin_errores_ni_avisos():
    res = validate_invoice_data(
        client_nif="A58818501",  # CIF válido -> sin aviso NIF
        amount_base=Decimal("1000"),
        vat_rate=21,
        invoice_date=date.today(),
    )
    assert res.is_valid
    assert res.errors == []
    assert res.warnings == []


def test_invoice_data_nif_malo_es_aviso_no_error():
    # Un NIF incorrecto no bloquea: se registra como advertencia.
    res = validate_invoice_data(
        client_nif="B12345678",
        amount_base=Decimal("1000"),
        vat_rate=21,
        invoice_date=date.today(),
    )
    assert res.is_valid
    assert any("NIF" in w for w in res.warnings)


def test_invoice_data_iva_invalido_es_error():
    res = validate_invoice_data(
        client_nif="A58818501",
        amount_base=Decimal("1000"),
        vat_rate=7,
        invoice_date=date.today(),
    )
    assert not res.is_valid
    assert any("IVA" in e for e in res.errors)


def test_invoice_data_importe_negativo_es_error():
    res = validate_invoice_data(
        client_nif="A58818501",
        amount_base=Decimal("-50"),
        vat_rate=21,
        invoice_date=date.today(),
    )
    assert not res.is_valid


def test_invoice_data_iban_malo_es_error():
    res = validate_invoice_data(
        client_nif="A58818501",
        amount_base=Decimal("1000"),
        vat_rate=21,
        invoice_date=date.today(),
        iban="ES0021000418450200051332",
    )
    assert not res.is_valid
    assert any("IBAN" in e for e in res.errors)


def test_invoice_data_importe_elevado_avisa_pero_es_valido():
    res = validate_invoice_data(
        client_nif="A58818501",
        amount_base=Decimal("60000"),
        vat_rate=21,
        invoice_date=date.today(),
    )
    assert res.is_valid
    assert any("elevado" in w.lower() for w in res.warnings)
