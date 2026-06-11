"""Tests del PDF oficial del Modelo 303 (casillas numeradas AEAT)."""
from app.services.pdf_reports import generate_modelo_303_pdf


def _data() -> dict:
    return {
        "tenant": {"name": "ACME SL", "nif": "B12345678"},
        "quarter": 2,
        "year": 2026,
        "vat_collected": [
            {"rate": 21.0, "base": 1000.0, "quota": 210.0},
            {"rate": 10.0, "base": 500.0, "quota": 50.0},
        ],
        "vat_deducted": [{"rate": 21.0, "base": 400.0, "quota": 84.0}],
        "vat_intra": [],
        "vat_isp": [],
        "recargo_equivalencia": [],
    }


def test_modelo_303_pdf_renders_valid_pdf():
    pdf = generate_modelo_303_pdf(_data())
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000  # un PDF con secciones, no un stub


def test_modelo_303_pdf_with_recargo_and_intra():
    d = _data()
    d["recargo_equivalencia"] = [
        {"rate": 21.0, "recargo_rate": 5.2, "base": 1000.0, "quota": 52.0}
    ]
    d["vat_intra"] = [{"rate": 21.0, "base": 300.0, "quota": 63.0}]
    pdf = generate_modelo_303_pdf(d)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 2000


def test_modelo_303_pdf_empty_quarter():
    d = _data()
    d["vat_collected"] = []
    d["vat_deducted"] = []
    pdf = generate_modelo_303_pdf(d)
    assert pdf[:4] == b"%PDF"
