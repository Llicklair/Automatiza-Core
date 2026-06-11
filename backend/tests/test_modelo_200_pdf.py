"""Test del PDF del Modelo 200 (Impuesto sobre Sociedades, preview)."""
from app.services.pdf_reports import generate_modelo_200_pdf


def _data() -> dict:
    return {
        "modelo": "200",
        "ejercicio": 2025,
        "tenant": {"name": "ACME SL", "nif": "B12345678"},
        "cifra_negocio": 100000.0,
        "gastos_facturas": 40000.0,
        "coste_nominas": 30000.0,
        "resultado_contable": 30000.0,
        "ajustes_fiscales": 0.0,
        "base_imponible": 30000.0,
        "tipo_impositivo_pct": 23.0,
        "cuota_integra": 6900.0,
        "pagos_fraccionados_pagados": 2000.0,
        "resultado_declaracion": 4900.0,
        "signo": "ingresar",
        "_warning": "Preview no oficial. Revísalo con tu asesor.",
    }


def test_modelo_200_pdf_renders_valid_pdf():
    pdf = generate_modelo_200_pdf(_data())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 1500


def test_modelo_200_pdf_tolerates_missing_fields():
    pdf = generate_modelo_200_pdf({"modelo": "200", "ejercicio": 2025, "tenant": {}})
    assert pdf[:4] == b"%PDF"
