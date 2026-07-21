"""Tests del render del ticket de venta (80 mm) — `services/sales/ticket_html`."""

from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

from app.services.sales.ticket_html import _qr_svg_data_uri, render_ticket_html


def _line(desc, qty, price, tax, total, discount=0):
    return SimpleNamespace(
        description=desc,
        quantity=qty,
        unit_price=price,
        discount_percentage=discount,
        tax_percentage=tax,
        total=total,
    )


def _invoice(simplified=True, number="T-0001", total="24.20"):
    return SimpleNamespace(
        id=uuid4(),
        invoice_number=number,
        is_simplified=simplified,
        date=datetime(2026, 7, 21, 10, 30),
        amount_total=total,
    )


def _emisor():
    return {
        "name": "Tintorería Pascual SL",
        "nif": "B12345678",
        "address": "Calle Mayor 1, Madrid",
        "phone": "600123456",
    }


def test_render_ticket_basic_content():
    html = render_ticket_html(
        emisor=_emisor(),
        invoice=_invoice(),
        lines=[_line("Limpieza traje", 1, "20.00", 21, "24.20")],
        qr={
            "verify_url": "https://prewww2.aeat.es/wlpl/TIKE-CONT/ValidarQR?nif=B12345678",
            "huella": "ABCDEF0123456789FF",
        },
        payment_method="card",
    )
    assert "Tintorería Pascual SL" in html
    assert "B12345678" in html
    assert "FACTURA SIMPLIFICADA" in html
    assert "Limpieza traje" in html
    # Total con coma decimal (formato España).
    assert "24,20 €" in html
    # Desglose de IVA por tipo.
    assert "IVA 21%" in html
    # Forma de pago mapeada.
    assert "Tarjeta" in html
    # Bloque Verifactu con leyendas oficiales + QR incrustado.
    assert "VERI*FACTU" in html
    assert "QR tributario:" in html
    assert "data:image/svg+xml;base64," in html


def test_render_ticket_sin_verifactu():
    html = render_ticket_html(
        emisor=_emisor(),
        invoice=_invoice(),
        lines=[_line("Camisa", 2, "3.00", 21, "7.26")],
        qr=None,
        payment_method="cash",
    )
    assert "Sin registro Verifactu" in html
    assert "VERI*FACTU" not in html
    assert "Efectivo" in html


def test_render_ticket_escapa_html():
    html = render_ticket_html(
        emisor={"name": "A & B <script>", "nif": None, "address": None, "phone": None},
        invoice=_invoice(),
        lines=[_line("<b>x</b>", 1, "1.00", 0, "1.00")],
        qr=None,
        payment_method=None,
    )
    assert "<script>" not in html
    assert "&amp;" in html
    assert "&lt;b&gt;x&lt;/b&gt;" in html


def test_qr_svg_data_uri_es_svg_valido():
    uri = _qr_svg_data_uri("https://example.com/qr")
    assert uri.startswith("data:image/svg+xml;base64,")
    import base64

    svg = base64.b64decode(uri.split(",", 1)[1]).decode("utf-8")
    assert "<svg" in svg
