"""Render de ticket de venta (TPV) como HTML autocontenido de 80 mm.

El mismo HTML sirve para imprimir en una impresora térmica de tickets (rollo
72/80 mm) o en una impresora normal (columna estrecha en A4): el frontend lo
manda al diálogo de impresión del sistema (o a impresión silenciosa en Electron).

Fuente única de verdad del ticket — se usa tanto al cobrar en el TPV como al
reimprimir desde la factura. El QR Verifactu se incrusta como SVG (data-URI)
generado con reportlab (`QrCodeWidget` + `renderSVG`), sin dependencias nuevas
y consistente con el QR del PDF de factura.
"""

from __future__ import annotations

import base64
import html
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.auth import Tenant
from app.db.models.billing import Invoice
from app.db.models.pos import PosSession
from app.services.billing.queries import load_verifactu_qr

_PAGO_LABEL = {"cash": "Efectivo", "card": "Tarjeta"}


def _fmt_eur(value) -> str:
    """2 decimales con coma decimal (formato España) + símbolo euro."""
    return f"{Decimal(str(value or 0)):.2f}".replace(".", ",") + " €"


def _qr_svg_data_uri(verify_url: str, px: int = 150) -> str:
    """QR del `verify_url` como SVG en data-URI base64.

    Usa el QR nativo de reportlab (mismo motor que el PDF) renderizado a SVG,
    así el HTML queda autocontenido y se imprime en cualquier impresora."""
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing

    widget = QrCodeWidget(verify_url)
    bounds = widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    drawing = Drawing(px, px, transform=[px / w, 0, 0, px / h, 0, 0])
    drawing.add(widget)
    svg = renderSVG.drawToString(drawing)
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _line_net(line) -> Decimal:
    """Base imponible de la línea (sin IVA, con descuento aplicado)."""
    qty = Decimal(str(line.quantity or 0))
    price = Decimal(str(line.unit_price or 0))
    disc = Decimal(str(getattr(line, "discount_percentage", 0) or 0))
    return qty * price * (Decimal("1") - disc / Decimal("100"))


def render_ticket_html(
    *,
    emisor: dict,
    invoice: Invoice,
    lines: list,
    qr: dict | None,
    payment_method: str | None,
) -> str:
    """Construye el HTML del ticket a partir de datos ya cargados (función pura)."""
    e = html.escape
    esc = lambda v: e(str(v)) if v else ""  # noqa: E731

    titulo = "FACTURA SIMPLIFICADA" if invoice.is_simplified else "FACTURA"
    numero = invoice.invoice_number or str(invoice.id)[:8]
    fecha = invoice.date or datetime.utcnow()
    fecha_str = fecha.strftime("%d/%m/%Y %H:%M")

    # Cabecera del negocio (emisor).
    cab = [f'<div class="biz">{esc(emisor.get("name") or "")}</div>']
    if emisor.get("nif"):
        cab.append(f'<div class="sub">NIF: {esc(emisor["nif"])}</div>')
    if emisor.get("address"):
        cab.append(f'<div class="sub">{esc(emisor["address"])}</div>')
    if emisor.get("phone"):
        cab.append(f'<div class="sub">Tel: {esc(emisor["phone"])}</div>')

    # Líneas.
    filas = []
    for ln in lines:
        qty = Decimal(str(ln.quantity or 0))
        price = Decimal(str(ln.unit_price or 0))
        filas.append(
            '<tr class="ln">'
            f'<td class="d" colspan="2">{esc(ln.description)}</td>'
            "</tr>"
            '<tr class="ln">'
            f'<td class="q">{qty:g} x {_fmt_eur(price)}</td>'
            f'<td class="t">{_fmt_eur(ln.total)}</td>'
            "</tr>"
        )

    # Desglose de IVA por tipo.
    por_tipo: dict[str, list[Decimal]] = {}
    for ln in lines:
        rate = f"{Decimal(str(ln.tax_percentage or 0)):g}"
        net = _line_net(ln)
        cuota = net * Decimal(str(ln.tax_percentage or 0)) / Decimal("100")
        acc = por_tipo.setdefault(rate, [Decimal("0"), Decimal("0")])
        acc[0] += net
        acc[1] += cuota
    iva_rows = "".join(
        '<tr class="iva">' f"<td>IVA {rate}% (base {_fmt_eur(base)})</td>" f"<td>{_fmt_eur(cuota)}</td>" "</tr>"
        for rate, (base, cuota) in sorted(por_tipo.items())
    )

    # Bloque Verifactu (QR + leyendas oficiales) o nota si no hay registro.
    if qr and qr.get("verify_url"):
        verify_url = qr["verify_url"]
        huella = qr.get("huella") or ""
        img = _qr_svg_data_uri(verify_url)
        verifactu = (
            '<div class="vf">'
            '<div class="vf-leg">VERI*FACTU</div>'
            '<div class="vf-leg2">QR tributario:</div>'
            f'<img class="qr" src="{img}" width="150" height="150" alt="QR" />'
            f'<div class="vf-url">{e(verify_url)}</div>'
            + (f'<div class="vf-h">{e(huella[:16])}…</div>' if huella else "")
            + "</div>"
        )
    else:
        verifactu = '<div class="vf"><div class="vf-leg2">Sin registro Verifactu</div></div>'

    pago = _PAGO_LABEL.get(payment_method or "", "")
    pago_row = f'<div class="pago">Forma de pago: {esc(pago)}</div>' if pago else ""

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"/>
<style>
  @page {{ size: 72mm auto; margin: 0; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{
    width: 72mm; padding: 4mm 3mm; color: #000; background: #fff;
    font-family: "Courier New", "Consolas", monospace; font-size: 11px; line-height: 1.35;
  }}
  .biz {{ font-size: 14px; font-weight: bold; text-align: center; }}
  .sub {{ text-align: center; font-size: 10px; }}
  .hr {{ border-top: 1px dashed #000; margin: 6px 0; }}
  .doc {{ text-align: center; font-weight: bold; margin: 2px 0; }}
  .meta {{ font-size: 10px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ vertical-align: top; }}
  td.d {{ padding-top: 3px; }}
  td.q {{ font-size: 10px; }}
  td.t {{ text-align: right; white-space: nowrap; }}
  .iva td {{ font-size: 10px; }}
  .iva td:last-child {{ text-align: right; }}
  .tot {{ display: flex; justify-content: space-between; font-size: 15px; font-weight: bold; margin-top: 4px; }}
  .pago {{ font-size: 10px; margin-top: 2px; }}
  .vf {{ text-align: center; margin-top: 8px; }}
  .vf-leg {{ font-weight: bold; letter-spacing: 1px; }}
  .vf-leg2 {{ font-size: 10px; }}
  .qr {{ margin: 4px auto; display: block; }}
  .vf-url {{ font-size: 7px; word-break: break-all; }}
  .vf-h {{ font-size: 8px; margin-top: 2px; }}
  .foot {{ text-align: center; font-size: 10px; margin-top: 8px; }}
</style></head>
<body>
  {"".join(cab)}
  <div class="hr"></div>
  <div class="doc">{e(titulo)}</div>
  <div class="meta">Nº {e(str(numero))}<br/>{e(fecha_str)}</div>
  <div class="hr"></div>
  <table>{"".join(filas)}</table>
  <div class="hr"></div>
  <table>{iva_rows}</table>
  <div class="tot"><span>TOTAL</span><span>{_fmt_eur(invoice.amount_total)}</span></div>
  {pago_row}
  {verifactu}
  <div class="foot">Gracias por su compra</div>
</body></html>"""


async def build_ticket_html(invoice_id: UUID, tenant_id, db: AsyncSession) -> str:
    """Carga la factura (con líneas), el emisor, el QR y la forma de pago, y
    devuelve el HTML del ticket. Lanza ValueError si la factura no existe en el
    tenant."""
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    )
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise ValueError("Factura no encontrada")

    tenant = await db.get(Tenant, tenant_id)
    emisor = {
        "name": getattr(tenant, "name", None) or "Mi Empresa",
        "nif": getattr(tenant, "nif", None),
        "address": getattr(tenant, "address", None),
        "phone": getattr(tenant, "phone", None),
    }

    qr = await load_verifactu_qr(invoice.id, db)

    payment_method = (
        await db.execute(select(PosSession.payment_method).where(PosSession.invoice_id == invoice.id))
    ).scalar_one_or_none()

    return render_ticket_html(
        emisor=emisor,
        invoice=invoice,
        lines=list(invoice.lines or []),
        qr=qr,
        payment_method=payment_method,
    )
