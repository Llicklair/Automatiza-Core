"""Resguardo de depósito de tintorería (PDF).

El comprobante que se lleva el cliente para recoger su pedido: nombre del negocio,
número de pedido + QR (para localizarlo al recoger), cliente, prendas, fecha de
recogida e importe. A4 para que imprima en cualquier impresora.
"""

from __future__ import annotations

import io
from uuid import UUID

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.auth import Tenant
from app.db.models.orders import SalesOrder

PAGE_W, PAGE_H = A4
LEFT = 20 * mm
RIGHT = PAGE_W - 20 * mm


def _qr(value: str, size: float) -> Drawing:
    qr = QrCodeWidget(value or "SIN-NUM")
    b = qr.getBounds()
    w = b[2] - b[0]
    h = b[3] - b[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(qr)
    return d


def build_resguardo_pdf(
    *,
    business_name: str,
    order_number: str,
    customer: str,
    pickup: str,
    garments: list[tuple[str, int]],
    total: float,
) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # QR arriba a la derecha (encoda el número de pedido, escaneable al recoger).
    qsize = 30 * mm
    renderPDF.draw(_qr(order_number, qsize), c, RIGHT - qsize, PAGE_H - 20 * mm - qsize)

    y = PAGE_H - 22 * mm
    c.setFont("Helvetica-Bold", 16)
    c.drawString(LEFT, y, (business_name or "Mi Empresa")[:40])
    y -= 7 * mm
    c.setFont("Helvetica", 11)
    c.drawString(LEFT, y, "RESGUARDO DE DEPÓSITO")

    y -= 14 * mm
    c.setFont("Helvetica-Bold", 13)
    c.drawString(LEFT, y, f"Pedido: {order_number or '-'}")
    y -= 8 * mm
    c.setFont("Helvetica", 11)
    c.drawString(LEFT, y, f"Cliente: {customer or 'Cliente'}")
    if pickup:
        y -= 7 * mm
        c.drawString(LEFT, y, f"Fecha de recogida: {pickup}")

    y -= 12 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(LEFT, y, "Prendas")
    y -= 7 * mm
    c.setFont("Helvetica", 10)
    for desc, qty in garments:
        c.drawString(LEFT, y, f"·  {qty} x {(desc or '')[:52]}")
        y -= 6 * mm
        if y < 35 * mm:  # deja sitio al pie
            break

    y -= 4 * mm
    c.setLineWidth(0.5)
    c.setStrokeGray(0.6)
    c.line(LEFT, y, RIGHT, y)
    y -= 9 * mm
    c.setFont("Helvetica-Bold", 13)
    c.drawString(LEFT, y, f"Total: {total:.2f} EUR")

    c.setFont("Helvetica-Oblique", 8)
    c.drawString(LEFT, 18 * mm, "Conserve este resguardo para recoger su pedido.")

    c.showPage()
    c.save()
    return buf.getvalue()


async def generate_resguardo_pdf(db: AsyncSession, tenant_id: UUID, order_id: UUID) -> bytes:
    res = await db.execute(
        select(SalesOrder)
        .options(selectinload(SalesOrder.lines), selectinload(SalesOrder.client))
        .where(SalesOrder.id == order_id, SalesOrder.tenant_id == tenant_id)
    )
    order = res.scalar_one_or_none()
    if order is None:
        raise LookupError("Pedido no encontrado")

    tenant = await db.get(Tenant, tenant_id)
    business = tenant.name if tenant else "Mi Empresa"
    customer = order.client.name if order.client else "Cliente"
    pickup = order.expected_delivery.strftime("%d-%m-%Y") if order.expected_delivery else ""
    garments = [(line.description, max(1, int(line.quantity or 1))) for line in order.lines]

    return build_resguardo_pdf(
        business_name=business,
        order_number=order.order_number or str(order.id)[:8],
        customer=customer,
        pickup=pickup,
        garments=garments,
        total=float(order.amount_total or 0),
    )
