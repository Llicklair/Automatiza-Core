"""Ticket-resguardo 80 mm del albarán (vertical tintorería, T2 de la spec).

El cliente deposita sus prendas → el empleado genera el albarán → este ticket
es el RESGUARDO que se lleva el cliente. Incluye un QR con el número de albarán
para localizarlo al instante cuando vuelva (lector USB o cámara). Mismo patrón
autocontenido que el ticket del TPV: imprime igual en térmica de 80 mm que en
impresora normal.
"""

from __future__ import annotations

import html
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.auth import Tenant
from app.db.models.billing import DeliveryNote
from app.services.sales.ticket_html import _fmt_eur, _qr_svg_data_uri

_ESTADOS = {
    "draft": "Borrador",
    "confirmed": "Confirmado",
    "recibido": "Recibido",
    "en_proceso": "En proceso",
    "listo": "Listo para recoger",
    "delivered": "Entregado",
    "anulado": "Anulado",
}


def render_albaran_ticket_html(
    *,
    emisor: dict,
    note,
    lines: list,
    cliente: dict | None,
) -> str:
    """HTML autocontenido del resguardo (función pura, testeable)."""
    e = html.escape
    esc = lambda v: e(str(v)) if v else ""  # noqa: E731

    numero = note.albaran_number or str(note.id)[:8]
    fecha = note.date or datetime.utcnow()
    fecha_str = fecha.strftime("%d/%m/%Y") if hasattr(fecha, "strftime") else str(fecha)
    estado = _ESTADOS.get(note.status or "", note.status or "")

    cab = [f'<div class="biz">{esc(emisor.get("name") or "")}</div>']
    if emisor.get("nif"):
        cab.append(f'<div class="sub">NIF: {esc(emisor["nif"])}</div>')
    if emisor.get("address"):
        cab.append(f'<div class="sub">{esc(emisor["address"])}</div>')
    if emisor.get("phone"):
        cab.append(f'<div class="sub">Tel: {esc(emisor["phone"])}</div>')

    cli = ""
    if cliente and (cliente.get("name") or cliente.get("phone")):
        partes = [esc(cliente.get("name") or "")]
        if cliente.get("phone"):
            partes.append(f"Tel: {esc(cliente['phone'])}")
        cli = f'<div class="cli">{" · ".join(p for p in partes if p)}</div>'

    filas = []
    for ln in lines:
        qty = Decimal(str(ln.quantity or 0))
        filas.append(
            '<tr><td class="q">{q:g}x</td><td class="d">{d}</td><td class="t">{t}</td></tr>'.format(
                q=qty,
                d=esc(ln.description),
                t=_fmt_eur(getattr(ln, "total", None) or 0),
            )
        )

    notas = f'<div class="notas">{esc(note.notes)}</div>' if note.notes else ""

    # QR con el NÚMERO del albarán: al volver el cliente, se escanea (lector USB
    # o cámara) y el buscador lo localiza al instante.
    qr = _qr_svg_data_uri(numero, px=120)

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
  .doc {{ text-align: center; font-weight: bold; letter-spacing: 1px; }}
  .num {{ text-align: center; font-size: 18px; font-weight: bold; margin: 2px 0; }}
  .meta {{ text-align: center; font-size: 10px; }}
  .cli {{ font-size: 10px; margin-top: 4px; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 2px; }}
  td {{ vertical-align: top; padding: 1px 0; }}
  td.q {{ width: 24px; }}
  td.t {{ text-align: right; white-space: nowrap; }}
  .notas {{ font-size: 10px; margin-top: 4px; font-style: italic; }}
  .tot {{ display: flex; justify-content: space-between; font-size: 13px; font-weight: bold; margin-top: 4px; }}
  .qr {{ text-align: center; margin-top: 6px; }}
  .aviso {{ text-align: center; font-size: 9px; margin-top: 6px; }}
</style></head>
<body>
  {"".join(cab)}
  <div class="hr"></div>
  <div class="doc">RESGUARDO DE DEPÓSITO</div>
  <div class="num">{e(str(numero))}</div>
  <div class="meta">{e(fecha_str)} · {e(estado)}</div>
  {cli}
  <div class="hr"></div>
  <table>{"".join(filas)}</table>
  {notas}
  <div class="tot"><span>TOTAL</span><span>{_fmt_eur(note.amount_total)}</span></div>
  <div class="qr"><img src="{qr}" width="120" height="120" alt="QR" /></div>
  <div class="aviso">Conserve este resguardo — es necesario para recoger su encargo.</div>
</body></html>"""


async def build_albaran_ticket_html(albaran_id: UUID, tenant_id, db: AsyncSession) -> str:
    """Carga albarán (con líneas y cliente) + emisor y devuelve el HTML.
    Lanza LookupError si no existe en el tenant."""
    result = await db.execute(
        select(DeliveryNote)
        .options(selectinload(DeliveryNote.lines), selectinload(DeliveryNote.client))
        .where(DeliveryNote.id == albaran_id, DeliveryNote.tenant_id == tenant_id)
    )
    note = result.scalar_one_or_none()
    if note is None:
        raise LookupError("Albarán no encontrado")

    tenant = await db.get(Tenant, tenant_id)
    emisor = {
        "name": getattr(tenant, "name", None) or "Mi Empresa",
        "nif": getattr(tenant, "nif", None),
        "address": getattr(tenant, "address", None),
        "phone": getattr(tenant, "phone", None),
    }
    cliente = None
    if note.client is not None:
        cliente = {"name": note.client.name, "phone": getattr(note.client, "phone", None)}

    return render_albaran_ticket_html(emisor=emisor, note=note, lines=list(note.lines or []), cliente=cliente)
