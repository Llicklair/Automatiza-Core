"""Tests de los generadores de PDF borrador de modelos AEAT.

Cubre 130/111/115/190/347/349/390/200/100. Verifican que cada generador produce
bytes no vacíos con datos realistas y que no revienta con listas vacías (sin
perceptores / sin declarables / sin operaciones).
"""
from app.services.pdf_reports import (
    generate_modelo_100_pdf,
    generate_modelo_111_pdf,
    generate_modelo_115_pdf,
    generate_modelo_130_pdf,
    generate_modelo_190_pdf,
    generate_modelo_200_pdf,
    generate_modelo_347_pdf,
    generate_modelo_349_pdf,
    generate_modelo_390_pdf,
)

_TENANT = {"name": "Empresa Test S.L.", "nif": "B12345678"}


def _is_pdf(b: bytes) -> bool:
    assert isinstance(b, bytes) and len(b) > 0
    # Con reportlab disponible empieza por %PDF; sin él, el fallback es texto.
    return b[:4] == b"%PDF" or b"BORRADOR" in b


def test_modelo_130_pdf():
    data = {
        "modelo": "130", "ejercicio": 2026, "periodo": "1T", "tenant": _TENANT,
        "ingresos_acumulados": 12000.0, "gastos_acumulados": 4000.0,
        "beneficio_acumulado": 8000.0, "pago_fraccionado_bruto": 1600.0,
        "retenciones_soportadas": 0.0, "pagos_fraccionados_anteriores": 0.0,
        "resultado_a_ingresar": 1600.0,
    }
    assert _is_pdf(generate_modelo_130_pdf(data))


def test_modelo_111_pdf_con_perceptores():
    data = {
        "modelo": "111", "ejercicio": 2026, "periodo": "1T", "tenant": _TENANT,
        "perceptores_trabajo_personal": [
            {"nombre": "Ana López", "nif": "12345678Z", "base_retencion": 3000.0,
             "retencion_practicada": 450.0, "num_nominas": 3},
        ],
        "total_base_retenciones": 3000.0, "total_retencion_practicada": 450.0,
        "num_perceptores": 1,
    }
    assert _is_pdf(generate_modelo_111_pdf(data))


def test_modelo_111_pdf_sin_perceptores():
    data = {"modelo": "111", "ejercicio": 2026, "periodo": "2T", "tenant": _TENANT,
            "perceptores_trabajo_personal": [], "total_base_retenciones": 0.0,
            "total_retencion_practicada": 0.0, "num_perceptores": 0}
    assert _is_pdf(generate_modelo_111_pdf(data))


def test_modelo_190_pdf():
    data = {
        "modelo": "190", "ejercicio": 2026, "tenant": _TENANT,
        "perceptores": [
            {"clave_percepcion": "A", "nombre": "Ana López", "nif": "12345678Z",
             "percepcion_integra": 12000.0, "retencion_practicada": 1800.0, "num_nominas": 12},
        ],
        "total_percepcion_integra": 12000.0, "total_retencion_practicada": 1800.0,
        "num_perceptores": 1,
    }
    assert _is_pdf(generate_modelo_190_pdf(data))


def test_modelo_347_pdf():
    data = {
        "modelo": "347", "ejercicio": 2026, "tenant": _TENANT,
        "umbral_legal": 3005.06, "num_declarables": 1,
        "declarables": [
            {"nif": "B87654321", "nombre": "Proveedor S.A.",
             "importe_emitidas": 0.0, "importe_recibidas": 9000.0},
        ],
        "total_contrapartes_analizadas": 5,
    }
    assert _is_pdf(generate_modelo_347_pdf(data))


def test_modelo_347_pdf_sin_declarables():
    data = {"modelo": "347", "ejercicio": 2026, "tenant": _TENANT,
            "umbral_legal": 3005.06, "num_declarables": 0, "declarables": [],
            "total_contrapartes_analizadas": 0}
    assert _is_pdf(generate_modelo_347_pdf(data))


def test_modelo_390_pdf():
    data = {
        "modelo": "390", "ejercicio": 2026, "tenant": _TENANT,
        "iva_devengado": [{"rate": 21.0, "base": 10000.0, "quota": 2100.0}],
        "iva_deducible": [{"rate": 21.0, "base": 4000.0, "quota": 840.0}],
        "total_devengado": 2100.0, "total_deducible": 840.0, "resultado_anual": 1260.0,
    }
    assert _is_pdf(generate_modelo_390_pdf(data))


def test_modelo_115_pdf():
    data = {
        "modelo": "115", "ejercicio": 2026, "periodo": "1T", "tenant": _TENANT,
        "tipo_retencion_pct": 19.0,
        "arrendadores": [
            {"nombre_arrendador": "Inmobiliaria X", "nif_arrendador": "B11111111",
             "base_retencion": 1000.0, "retencion_practicada": 190.0},
        ],
        "num_arrendadores": 1, "total_base_retenciones": 1000.0,
        "total_retencion_practicada": 190.0,
    }
    assert _is_pdf(generate_modelo_115_pdf(data))


def test_modelo_349_pdf():
    data = {
        "modelo": "349", "ejercicio": 2026, "periodo": "1T", "tenant": _TENANT,
        "operaciones": [
            {"nif_intracomunitario": "DE123456789", "pais_codigo": "DE",
             "nombre_contraparte": "Muster GmbH", "tipo_operacion": "E", "base_imponible": 5000.0},
        ],
        "num_operadores": 1, "total_base_imponible": 5000.0,
    }
    assert _is_pdf(generate_modelo_349_pdf(data))


def test_modelo_349_pdf_sin_operaciones():
    data = {"modelo": "349", "ejercicio": 2026, "periodo": "2T", "tenant": _TENANT,
            "operaciones": [], "num_operadores": 0, "total_base_imponible": 0.0}
    assert _is_pdf(generate_modelo_349_pdf(data))


def test_modelo_200_pdf():
    data = {
        "modelo": "200", "ejercicio": 2026, "tenant": _TENANT,
        "cifra_negocio": 250000.0, "gastos_facturas": 150000.0, "coste_nominas": 40000.0,
        "resultado_contable": 60000.0, "ajustes_fiscales": 0.0, "base_imponible": 60000.0,
        "tipo_impositivo_pct": 25.0, "cuota_integra": 15000.0,
        "pagos_fraccionados_pagados": 5000.0, "resultado_declaracion": 10000.0,
    }
    assert _is_pdf(generate_modelo_200_pdf(data))


def test_modelo_100_pdf():
    data = {
        "modelo": "100", "ejercicio": 2026, "tenant": _TENANT,
        "ingresos": 80000.0, "gastos_facturas": 30000.0, "coste_nominas": 0.0,
        "rendimiento_neto": 50000.0, "minimo_personal": 5550.0, "base_liquidable": 44450.0,
        "cuota_integra": 12000.0, "retenciones_soportadas": 4000.0,
        "pagos_fraccionados_pagados": 6000.0, "resultado_declaracion": 2000.0,
    }
    assert _is_pdf(generate_modelo_100_pdf(data))
