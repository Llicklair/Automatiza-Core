"""Etiquetas de prenda/pedido para tintorería (PDF para imprimir).

Una etiqueta por prenda de un pedido de venta (SalesOrder), con el número de
pedido en código de barras (Code128, escaneable para localizar el pedido), el
cliente, la prenda y la fecha de recogida. Se imprime con el diálogo del sistema,
así que vale para impresoras normales y de etiquetas (igual que las de producto).
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
from sqlalchemy.orm import selectinload

from app.db.models.orders import SalesOrder

PAGE_W, PAGE_H = A4
MARGIN = 8 * mm
COLS = 3
ROWS = 8


def _draw_order_label(
    c: canvas.Canvas,
    x: float,
    y_top: float,
    w: float,
    h: float,
    *,
    order_number: str,
    customer: str,
    garment: str,
    pickup: str,
) -> None:
    cx = x + w / 2

    # Cliente y fecha de recogida arriba.
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(cx, y_top - 8, (customer or "Cliente")[:32])
    if pickup:
        c.setFont("Helvetica", 6)
        c.drawCentredString(cx, y_top - 15, f"Recogida: {pickup}")

    # Prenda.
    c.setFont("Helvetica", 7)
    c.drawCentredString(cx, y_top - 24, (garment or "")[:34])

    # Código de barras del número de pedido (para localizar el pedido al recoger).
    value = (order_number or "SIN-NUM").strip() or "SIN-NUM"
    bar_width = 0.32 * mm
    bc = code128.Code128(value, barHeight=8 * mm, barWidth=bar_width, humanReadable=True, quiet=False)
    max_w = w - 6 * mm
    if bc.width > max_w:
        bar_width = bar_width * (max_w / bc.width)
        bc = code128.Code128(value, barHeight=8 * mm, barWidth=bar_width, humanReadable=True, quiet=False)
    bc.drawOn(c, x + (w - bc.width) / 2, y_top - h + 3 * mm)

    # Borde tenue para recortar.
    c.setLineWidth(0.2)
    c.setStrokeGray(0.8)
    c.rect(x, y_top - h, w, h, stroke=1, fill=0)


def build_order_labels_pdf(*, order_number: str, customer: str, pickup: str, garments: list[str]) -> bytes:
    """`garments`: lista de descripciones; una etiqueta por elemento."""
    if not garments:
        raise ValueError("El pedido no tiene prendas que etiquetar")
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    label_w = (PAGE_W - 2 * MARGIN) / COLS
    label_h = (PAGE_H - 2 * MARGIN) / ROWS
    per_page = COLS * ROWS
    for i, garment in enumerate(garments):
        pos = i % per_page
        if i > 0 and pos == 0:
            c.showPage()
        col = pos % COLS
        row = pos // COLS
        x = MARGIN + col * label_w
        y_top = PAGE_H - MARGIN - row * label_h
        _draw_order_label(
            c,
            x,
            y_top,
            label_w,
            label_h,
            order_number=order_number,
            customer=customer,
            garment=garment,
            pickup=pickup,
        )
    c.showPage()
    c.save()
    return buf.getvalue()


async def generate_order_labels_pdf(db: AsyncSession, tenant_id: UUID, order_id: UUID) -> bytes:
    """Carga el pedido y genera el PDF de etiquetas (una por prenda, por cantidad)."""
    res = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.client))
        .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
    )
    order = res.scalar_one_or_none()
    if order is None:
        raise LookupError("Pedido no encontrado")

    customer = order.client.name if order.client else "Cliente"
    pickup = order.expected_delivery.strftime("%d-%m-%Y") if order.expected_delivery else ""
    garments: list[str] = []
    for line in order.lines:
        copies = max(1, int(line.quantity or 1))
        garments.extend([line.description] * copies)

    return build_order_labels_pdf(
        order_number=order.order_number or str(order.id)[:8],
        customer=customer,
        pickup=pickup,
        garments=garments,
    )
