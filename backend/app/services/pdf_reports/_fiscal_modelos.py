"""Generación de PDF borrador imprimible para los modelos AEAT 130/111/190/347/390.

Reutiliza los helpers de reportlab de `_fiscal_modelo303.py` / `_pdf_base.py`.
Cada PDF es un BORRADOR informativo (no válido para presentación), pensado para
descargar e imprimir con los datos del tenant. Defensivo: tolera campos ausentes.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
    _table_header_style,
)

_logger = logging.getLogger(__name__)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle

_QUARTER_LABELS = {
    1: "1T (Enero - Marzo)",
    2: "2T (Abril - Junio)",
    3: "3T (Julio - Septiembre)",
    4: "4T (Octubre - Diciembre)",
}


def _eur(v) -> str:
    try:
        return f"{float(v or 0):.2f} €"
    except (TypeError, ValueError):
        return "0.00 €"


def _header(title: str, subtitle: str, tenant: dict, period_label: str, year, s, C) -> list:
    """Cabecera común: título, badge BORRADOR y tabla informativa empresa/período."""
    elements = [
        Paragraph(title, s["title"]),
        Paragraph(subtitle, s["section"]),
        Spacer(1, 3 * mm),
    ]
    badge = Table(
        [[Paragraph(
            "BORRADOR — NO VÁLIDO PARA PRESENTACIÓN",
            ParagraphStyle("DraftBadge", parent=s["styles"]["Normal"], fontSize=10,
                           fontName="Helvetica-Bold", textColor=colors.HexColor(C["AMBER"])),
        )]],
        colWidths=[175 * mm],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(C["AMBER"])),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    elements += [badge, Spacer(1, 5 * mm)]

    info = [
        [Paragraph("Empresa:", s["header"]), Paragraph(tenant.get("name", "—"), s["body"]),
         Paragraph("NIF:", s["header"]), Paragraph(tenant.get("nif", "—"), s["body"])],
        [Paragraph("Período:", s["header"]), Paragraph(period_label, s["body"]),
         Paragraph("Ejercicio:", s["header"]), Paragraph(str(year), s["body"])],
    ]
    info_table = Table(info, colWidths=[22 * mm, 65 * mm, 22 * mm, 65 * mm])
    info_table.setStyle(TableStyle([
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements += [
        info_table, Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=2, color=colors.HexColor(C["INDIGO"])),
        Spacer(1, 5 * mm),
    ]
    return elements


def _footer(s, C) -> list:
    return [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])),
        Spacer(1, 3 * mm),
        Paragraph(
            "Documento informativo generado automáticamente. No sustituye la presentación oficial ante la AEAT.",
            ParagraphStyle("Foot", parent=s["styles"]["Normal"], fontSize=8,
                           fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                           alignment=TA_CENTER),
        ),
        Spacer(1, 2 * mm),
        Paragraph(f"Generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}", s["footer"]),
    ]


def _kv_table(rows: list[tuple[str, str, bool]], s, C) -> Table:
    """Tabla concepto→importe. rows = [(label, value, is_total)]."""
    data = []
    for label, value, _is_total in rows:
        data.append([Paragraph(label, s["body"]), Paragraph(value, s["right_bold"])])
    tbl = Table(data, colWidths=[130 * mm, 45 * mm])
    style = [
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor(C["LINE"])),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]
    for i, (_l, _v, is_total) in enumerate(rows):
        if is_total:
            style += [
                ("LINEABOVE", (0, i), (-1, i), 1.2, colors.HexColor(C["SLATE"])),
                ("BACKGROUND", (0, i), (-1, i), colors.HexColor(C["LIGHT"])),
                ("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"),
            ]
    tbl.setStyle(TableStyle(style))
    return tbl


def _build(elements) -> bytes:
    buf = io.BytesIO()
    doc = _make_doc(buf)
    doc.build(elements)
    return buf.getvalue()


# ── Modelo 130 — IRPF pago fraccionado ────────────────────────────────────────

def generate_modelo_130_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 130 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    q = data.get("periodo", "")
    el = _header("Modelo 130", "IRPF · Pago fraccionado (estimación directa)",
                 data.get("tenant", {}), _QUARTER_LABELS.get(_q(q), q), data.get("ejercicio", ""), s, C)
    el.append(Paragraph("Rendimiento de la actividad (acumulado del ejercicio)", s["section"]))
    el.append(_kv_table([
        ("Ingresos computables acumulados", _eur(data.get("ingresos_acumulados")), False),
        ("Gastos deducibles acumulados", _eur(data.get("gastos_acumulados")), False),
        ("Rendimiento neto (beneficio acumulado)", _eur(data.get("beneficio_acumulado")), True),
    ], s, C))
    el.append(Spacer(1, 6 * mm))
    el.append(Paragraph("Liquidación", s["section"]))
    el.append(_kv_table([
        ("Pago fraccionado (20% del rendimiento)", _eur(data.get("pago_fraccionado_bruto")), False),
        ("Retenciones soportadas", _eur(data.get("retenciones_soportadas")), False),
        ("Pagos fraccionados de períodos anteriores", _eur(data.get("pagos_fraccionados_anteriores")), False),
        ("RESULTADO A INGRESAR", _eur(data.get("resultado_a_ingresar")), True),
    ], s, C))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 111 — Retenciones del trabajo ──────────────────────────────────────

def generate_modelo_111_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 111 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    q = data.get("periodo", "")
    el = _header("Modelo 111", "Retenciones e ingresos a cuenta · IRPF rendimientos del trabajo",
                 data.get("tenant", {}), _QUARTER_LABELS.get(_q(q), q), data.get("ejercicio", ""), s, C)
    perceptores = data.get("perceptores_trabajo_personal", []) or []
    el.append(Paragraph(f"Perceptores ({len(perceptores)})", s["section"]))
    rows = [[Paragraph("Perceptor", s["header"]), Paragraph("NIF", s["header"]),
             Paragraph("Base retención", s["header"]), Paragraph("Retención", s["header"])]]
    for p in perceptores:
        rows.append([
            Paragraph(str(p.get("nombre") or "—"), s["body"]),
            Paragraph(str(p.get("nif") or "—"), s["body"]),
            Paragraph(_eur(p.get("base_retencion")), s["right"]),
            Paragraph(_eur(p.get("retencion_practicada")), s["right"]),
        ])
    if not perceptores:
        rows.append([Paragraph("Sin perceptores en el período", s["body"]), Paragraph("", s["body"]),
                     Paragraph("", s["body"]), Paragraph("", s["body"])])
    tbl = Table(rows, colWidths=[70 * mm, 35 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    el += [tbl, Spacer(1, 6 * mm)]
    el.append(_kv_table([
        ("Total base de retenciones", _eur(data.get("total_base_retenciones")), False),
        ("TOTAL A INGRESAR (retenciones practicadas)", _eur(data.get("total_retencion_practicada")), True),
    ], s, C))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 190 — Resumen anual de retenciones ─────────────────────────────────

def generate_modelo_190_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 190 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    el = _header("Modelo 190", "Resumen anual de retenciones e ingresos a cuenta",
                 data.get("tenant", {}), "Ejercicio anual", data.get("ejercicio", ""), s, C)
    perceptores = data.get("perceptores", []) or []
    el.append(Paragraph(f"Perceptores ({len(perceptores)})", s["section"]))
    rows = [[Paragraph("Clave", s["header"]), Paragraph("Perceptor", s["header"]),
             Paragraph("NIF", s["header"]), Paragraph("Percepción íntegra", s["header"]),
             Paragraph("Retención", s["header"])]]
    for p in perceptores:
        rows.append([
            Paragraph(str(p.get("clave_percepcion") or "—"), s["body"]),
            Paragraph(str(p.get("nombre") or "—"), s["body"]),
            Paragraph(str(p.get("nif") or "—"), s["body"]),
            Paragraph(_eur(p.get("percepcion_integra")), s["right"]),
            Paragraph(_eur(p.get("retencion_practicada")), s["right"]),
        ])
    if not perceptores:
        rows.append([Paragraph("—", s["body"])] * 5)
    tbl = Table(rows, colWidths=[15 * mm, 60 * mm, 32 * mm, 36 * mm, 32 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (3, 0), (-1, -1), "RIGHT")]))
    el += [tbl, Spacer(1, 6 * mm)]
    el.append(_kv_table([
        ("Total percepción íntegra", _eur(data.get("total_percepcion_integra")), False),
        ("TOTAL RETENCIONES", _eur(data.get("total_retencion_practicada")), True),
    ], s, C))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 347 — Operaciones con terceros ─────────────────────────────────────

def generate_modelo_347_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 347 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    el = _header("Modelo 347", "Declaración anual de operaciones con terceras personas",
                 data.get("tenant", {}), "Ejercicio anual", data.get("ejercicio", ""), s, C)
    declarables = data.get("declarables", []) or []
    el.append(Paragraph(
        f"Contrapartes declarables: {data.get('num_declarables', len(declarables))} "
        f"(umbral legal {_eur(data.get('umbral_legal'))})", s["section"]))
    rows = [[Paragraph("NIF", s["header"]), Paragraph("Nombre / Razón social", s["header"]),
             Paragraph("Emitidas", s["header"]), Paragraph("Recibidas", s["header"])]]
    for d in declarables:
        rows.append([
            Paragraph(str(d.get("nif") or "—"), s["body"]),
            Paragraph(str(d.get("nombre") or "—"), s["body"]),
            Paragraph(_eur(d.get("importe_emitidas")), s["right"]),
            Paragraph(_eur(d.get("importe_recibidas")), s["right"]),
        ])
    if not declarables:
        rows.append([Paragraph("Sin operaciones que superen el umbral", s["body"]),
                     Paragraph("", s["body"]), Paragraph("", s["body"]), Paragraph("", s["body"])])
    tbl = Table(rows, colWidths=[32 * mm, 73 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    el += [tbl]
    el += _footer(s, C)
    return _build(el)


# ── Modelo 390 — Resumen anual de IVA ─────────────────────────────────────────

def generate_modelo_390_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 390 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    el = _header("Modelo 390", "Resumen anual del Impuesto sobre el Valor Añadido",
                 data.get("tenant", {}), "Ejercicio anual", data.get("ejercicio", ""), s, C)

    def _vat_block(title: str, rows: list, total: float, bg: str) -> list:
        out = [Paragraph(title, s["section"])]
        table_rows = [[Paragraph("Tipo", s["header"]), Paragraph("Base", s["header"]),
                       Paragraph("Cuota", s["header"])]]
        for r in rows or []:
            table_rows.append([
                Paragraph(f"{float(r.get('rate', 0)):.0f}%", s["body"]),
                Paragraph(_eur(r.get("base")), s["right"]),
                Paragraph(_eur(r.get("quota")), s["right"]),
            ])
        table_rows.append([Paragraph("TOTAL", s["right_bold"]), Paragraph("", s["body"]),
                           Paragraph(_eur(total), s["right_bold"])])
        t = Table(table_rows, colWidths=[50 * mm, 62 * mm, 63 * mm])
        t.setStyle(TableStyle(_table_header_style() + [
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(bg)),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ]))
        return out + [t, Spacer(1, 6 * mm)]

    el += _vat_block("IVA devengado (ventas)", data.get("iva_devengado", []),
                     float(data.get("total_devengado", 0)), "#f0fdf4")
    el += _vat_block("IVA deducible (compras)", data.get("iva_deducible", []),
                     float(data.get("total_deducible", 0)), "#fef2f2")

    resultado = float(data.get("resultado_anual", 0))
    label = "RESULTADO ANUAL (A INGRESAR)" if resultado >= 0 else "RESULTADO ANUAL (A COMPENSAR)"
    el.append(_kv_table([(label, _eur(abs(resultado)), True)], s, C))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 115 — Retenciones por arrendamiento de inmuebles ───────────────────

def generate_modelo_115_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 115 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    q = data.get("periodo", "")
    el = _header("Modelo 115", "Retenciones e ingresos a cuenta · arrendamiento de inmuebles urbanos",
                 data.get("tenant", {}), _QUARTER_LABELS.get(_q(q), q), data.get("ejercicio", ""), s, C)
    arr = data.get("arrendadores", []) or []
    el.append(Paragraph(
        f"Arrendadores ({data.get('num_arrendadores', 0)}) · tipo de retención "
        f"{float(data.get('tipo_retencion_pct', 0)):.0f}%", s["section"]))
    rows = [[Paragraph("Arrendador", s["header"]), Paragraph("NIF", s["header"]),
             Paragraph("Base retención", s["header"]), Paragraph("Retención", s["header"])]]
    for a in arr:
        rows.append([
            Paragraph(str(a.get("nombre_arrendador") or "—"), s["body"]),
            Paragraph(str(a.get("nif_arrendador") or "—"), s["body"]),
            Paragraph(_eur(a.get("base_retencion")), s["right"]),
            Paragraph(_eur(a.get("retencion_practicada")), s["right"]),
        ])
    if not arr:
        rows.append([Paragraph("Sin arrendamientos con retención en el período", s["body"]),
                     Paragraph("", s["body"]), Paragraph("", s["body"]), Paragraph("", s["body"])])
    tbl = Table(rows, colWidths=[70 * mm, 35 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    el += [tbl, Spacer(1, 6 * mm)]
    el.append(_kv_table([
        ("Total base de retenciones", _eur(data.get("total_base_retenciones")), False),
        ("TOTAL A INGRESAR (retenciones practicadas)", _eur(data.get("total_retencion_practicada")), True),
    ], s, C))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 349 — Operaciones intracomunitarias ────────────────────────────────

def generate_modelo_349_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 349 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    q = data.get("periodo", "")
    el = _header("Modelo 349", "Declaración recapitulativa de operaciones intracomunitarias",
                 data.get("tenant", {}), _QUARTER_LABELS.get(_q(q), q), data.get("ejercicio", ""), s, C)
    ops = data.get("operaciones", []) or []
    el.append(Paragraph(f"Operadores intracomunitarios ({data.get('num_operadores', 0)})", s["section"]))
    rows = [[Paragraph("NIF-IVA", s["header"]), Paragraph("País", s["header"]),
             Paragraph("Contraparte", s["header"]), Paragraph("Clave", s["header"]),
             Paragraph("Base imponible", s["header"])]]
    for o in ops:
        rows.append([
            Paragraph(str(o.get("nif_intracomunitario") or "—"), s["body"]),
            Paragraph(str(o.get("pais_codigo") or "—"), s["body"]),
            Paragraph(str(o.get("nombre_contraparte") or "—"), s["body"]),
            Paragraph(str(o.get("tipo_operacion") or "—"), s["body"]),
            Paragraph(_eur(o.get("base_imponible")), s["right"]),
        ])
    if not ops:
        rows.append([Paragraph("Sin operaciones intracomunitarias en el período", s["body"])]
                    + [Paragraph("", s["body"])] * 4)
    tbl = Table(rows, colWidths=[34 * mm, 16 * mm, 56 * mm, 22 * mm, 47 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (4, 0), (-1, -1), "RIGHT")]))
    el += [tbl, Spacer(1, 6 * mm)]
    el.append(_kv_table([
        ("TOTAL BASE IMPONIBLE INTRACOMUNITARIA", _eur(data.get("total_base_imponible")), True),
    ], s, C))
    el += _footer(s, C)
    return _build(el)


def _q(periodo) -> int:
    """Extrae el número de trimestre de '1T'/'2T'... Devuelve 0 si no aplica."""
    try:
        return int(str(periodo).rstrip("Tt"))
    except (TypeError, ValueError):
        return 0
