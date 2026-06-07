"""Generación de etiquetas de producto con código de barras (PDF para imprimir).

Usa reportlab (Code128) para que los códigos sean legibles por cualquier lector.
El PDF se imprime con el diálogo del sistema, así que vale para impresoras
normales y de etiquetas.
"""

from __future__ import annotations

import io
from uuid import UUID

from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.inventory import Product

PAGE_W, PAGE_H = A4
MARGIN = 8 * mm
COLS = 3
ROWS = 8


def _draw_label(c: canvas.Canvas, label: dict, x: float, y_top: float, w: float, h: float, show_price: bool) -> None:
    name = (label.get("name") or "")[:34]
    value = (label.get("value") or "").strip() or "SIN-CODIGO"

    # Nombre arriba.
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + w / 2, y_top - 9, name)

    # Código de barras Code128, ajustado al ancho de la etiqueta.
    bar_width = 0.34 * mm
    bc = code128.Code128(value, barHeight=9 * mm, barWidth=bar_width, humanReadable=True, quiet=False)
    max_w = w - 6 * mm
    if bc.width > max_w:
        bar_width = bar_width * (max_w / bc.width)
        bc = code128.Code128(value, barHeight=9 * mm, barWidth=bar_width, humanReadable=True, quiet=False)
    bx = x + (w - bc.width) / 2
    by = y_top - h + (10 * mm if show_price else 6 * mm)
    bc.drawOn(c, bx, by)

    # Precio abajo.
    if show_price and label.get("price") is not None:
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x + w / 2, y_top - h + 3 * mm, f"{float(label['price']):.2f} EUR")

    # Borde tenue para recortar.
    c.setLineWidth(0.2)
    c.setStrokeGray(0.8)
    c.rect(x, y_top - h, w, h, stroke=1, fill=0)


def build_labels_pdf(labels: list[dict], show_price: bool = True) -> bytes:
    """`labels`: lista de dicts con name/value/price. Una etiqueta por elemento."""
    if not labels:
        raise ValueError("No hay etiquetas que generar")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    label_w = (PAGE_W - 2 * MARGIN) / COLS
    label_h = (PAGE_H - 2 * MARGIN) / ROWS
    per_page = COLS * ROWS
    for i, label in enumerate(labels):
        pos = i % per_page
        if i > 0 and pos == 0:
            c.showPage()
        col = pos % COLS
        row = pos // COLS
        x = MARGIN + col * label_w
        y_top = PAGE_H - MARGIN - row * label_h
        _draw_label(c, label, x, y_top, label_w, label_h, show_price)
    c.showPage()
    c.save()
    return buf.getvalue()


async def generate_labels_pdf(db: AsyncSession, tenant_id: UUID, items: list[dict], show_price: bool = True) -> bytes:
    """`items`: lista de {product_id, copies}. Genera el PDF de etiquetas."""
    ids = [it["product_id"] for it in items]
    res = await db.execute(select(Product).where(Product.tenant_id == tenant_id, Product.id.in_(ids)))
    by_id = {p.id: p for p in res.scalars().all()}

    labels: list[dict] = []
    for it in items:
        product = by_id.get(it["product_id"])
        if product is None:
            continue
        copies = max(1, int(it.get("copies") or 1))
        label = {
            "name": product.name,
            "value": (product.barcode or product.sku or str(product.id)[:12]),
            "price": float(product.price) if product.price is not None else None,
        }
        labels.extend([label] * copies)

    if not labels:
        raise ValueError("Ningún producto válido para etiquetar")
    return build_labels_pdf(labels, show_price=show_price)
