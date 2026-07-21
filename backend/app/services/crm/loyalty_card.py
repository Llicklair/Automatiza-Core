"""Tarjeta de fidelización del cliente (PDF).

Tarjeta imprimible (tamaño tarjeta bancaria, sobre A4 para que imprima en cualquier
impresora y se recorte) con el nombre del negocio, el cliente y un QR que encoda el
id del cliente para identificarlo al escanearla en el TPV.
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
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import Tenant
from app.db.models.crm import Client

PAGE_W, PAGE_H = A4
CARD_W = 85.6 * mm
CARD_H = 54 * mm


def _qr(value: str, size: float) -> Drawing:
    qr = QrCodeWidget(value or "-")
    b = qr.getBounds()
    w = b[2] - b[0]
    h = b[3] - b[1]
    d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
    d.add(qr)
    return d


def build_loyalty_card_pdf(*, business_name: str, customer_name: str, member_since: str, qr_value: str) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    x0 = 20 * mm
    y0 = PAGE_H - 20 * mm - CARD_H
    c.setLineWidth(0.8)
    c.setStrokeGray(0.5)
    c.roundRect(x0, y0, CARD_W, CARD_H, 4 * mm, stroke=1, fill=0)

    pad = 5 * mm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x0 + pad, y0 + CARD_H - pad - 3 * mm, (business_name or "Mi Empresa")[:26])
    c.setFont("Helvetica", 7)
    c.drawString(x0 + pad, y0 + CARD_H - pad - 9 * mm, "TARJETA DE CLIENTE")

    c.setFont("Helvetica-Bold", 12)
    c.drawString(x0 + pad, y0 + 16 * mm, (customer_name or "Cliente")[:26])
    if member_since:
        c.setFont("Helvetica", 7)
        c.drawString(x0 + pad, y0 + 9 * mm, f"Cliente desde: {member_since}")

    qsize = 26 * mm
    renderPDF.draw(_qr(qr_value, qsize), c, x0 + CARD_W - pad - qsize, y0 + (CARD_H - qsize) / 2)

    c.setFont("Helvetica-Oblique", 7)
    c.drawString(x0, y0 - 6 * mm, "Presente esta tarjeta en caja para identificarse.")

    c.showPage()
    c.save()
    return buf.getvalue()


async def generate_loyalty_card_pdf(db: AsyncSession, tenant_id: UUID, client_id: UUID) -> bytes:
    client = await db.get(Client, client_id)
    if client is None or client.tenant_id != tenant_id:
        raise LookupError("Cliente no encontrado")

    tenant = await db.get(Tenant, tenant_id)
    business = tenant.name if tenant else "Mi Empresa"
    member_since = client.created_at.strftime("%d-%m-%Y") if getattr(client, "created_at", None) else ""

    return build_loyalty_card_pdf(
        business_name=business,
        customer_name=client.name,
        member_since=member_since,
        qr_value=str(client.id),
    )
