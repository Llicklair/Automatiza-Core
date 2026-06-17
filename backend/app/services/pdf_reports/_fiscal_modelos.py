"""Generación de PDF borrador imprimible para los modelos AEAT 130/111/190/347/390.

Reutiliza los helpers de reportlab de `_fiscal_modelo303.py` / `pdf_base.py`.
Cada PDF es un BORRADOR informativo (no válido para presentación), pensado para
descargar e imprimir con los datos del tenant. Defensivo: tolera campos ausentes.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

from app.services.aeat.casillas_111 import build_casillas_111
from app.services.aeat.casillas_115 import build_casillas_115
from app.services.aeat.casillas_130 import build_casillas_130
from app.services.aeat.casillas_390 import build_casillas_390
from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
    _table_header_style,
)
from app.services.pdf_reports._aeat_layout import (
    _casillas_table,
    _draft_badge,
    _identificacion_table,
    _resultado_badge,
    _section_banner,
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
        Paragraph(f"Generado por AutomatizaCore · {datetime.now().strftime('%d/%m/%Y %H:%M')}", s["footer"]),
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
    """Genera el PDF borrador del Modelo 130 con las casillas oficiales AEAT.

    Replica la estructura del formulario oficial (Apartado I, casillas 01-07, y
    Apartado III, casillas 12-19) manteniendo el marcado de BORRADOR. NO genera
    número de justificante, CSV ni código de barras: solo nacen al presentar de
    verdad en la Sede Electrónica de la AEAT.
    """
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 130 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    quarter = _q(data.get("periodo", ""))
    year = data.get("ejercicio", "")
    casillas = build_casillas_130(data)
    cmap = {c.codigo: c for c in casillas}

    el: list = [
        Paragraph("Modelo 130 · Pago fraccionado del IRPF", s["title"]),
        Paragraph("Actividades económicas en estimación directa", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), quarter, year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Liquidación · Actividades económicas en estimación directa (Apartado I)", s),
        Spacer(1, 2 * mm),
    ]
    tbl_i = _casillas_table(cmap, ["01", "02", "03", "04", "05", "06", "07"], s, C,
                            emphasis=("03", "07"))
    if tbl_i is not None:
        el.append(tbl_i)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("3. Total liquidación (Apartado III)", s),
        Spacer(1, 2 * mm),
    ]
    tbl_iii = _casillas_table(cmap, ["12", "13", "14", "15", "16", "17", "18", "19"], s, C,
                              emphasis=("19",))
    if tbl_iii is not None:
        el.append(tbl_iii)

    resultado_19 = float(cmap["19"].valor) if "19" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado_19, s, neg_label="DECLARACIÓN NEGATIVA")]

    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(
        "Las casillas 05, 06, 13, 15, 16 y 18 dependen de datos del contribuyente "
        "(retenciones, pagos previos, deducciones) y se muestran a 0 por defecto: "
        "revísalas y ajústalas antes de presentar.",
        s["body"],
    ))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 111 — Retenciones del trabajo ──────────────────────────────────────

def generate_modelo_111_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 111 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    quarter = _q(data.get("periodo", ""))
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_111(data)}
    el: list = [
        Paragraph("Modelo 111 · Retenciones del trabajo", s["title"]),
        Paragraph("Retenciones e ingresos a cuenta · trabajo y actividades económicas", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), quarter, year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Liquidación · Retenciones e ingresos a cuenta", s),
        Spacer(1, 2 * mm),
    ]
    t1 = _casillas_table(cmap, ["01", "02", "03", "07", "08", "09"], s, C, emphasis=("03", "09"))
    if t1 is not None:
        el.append(t1)
    el += [Spacer(1, 5 * mm), _section_banner("3. Total liquidación", s), Spacer(1, 2 * mm)]
    t2 = _casillas_table(cmap, ["28", "29", "30"], s, C, emphasis=("30",))
    if t2 is not None:
        el.append(t2)
    resultado = float(cmap["30"].valor) if "30" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado, s)]
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(
        "Las casillas 07-09 (actividades económicas/profesionales) son editables y se "
        "muestran a 0 por defecto. Los bloques de retribución en especie, premios y otros "
        "se omiten en este borrador. Revisa antes de presentar.", s["body"]))
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
    cmap = {c.codigo: c for c in build_casillas_390(data)}
    el: list = [
        Paragraph("Modelo 390 · Resumen anual del IVA", s["title"]),
        Paragraph("Impuesto sobre el Valor Añadido", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), "Anual", data.get("ejercicio", ""), s),
        Spacer(1, 5 * mm),
        _section_banner("2. IVA devengado", s),
        Spacer(1, 2 * mm),
    ]
    t1 = _casillas_table(cmap, ["01", "02", "03", "04", "05", "06", "33", "34", "47"], s, C,
                         emphasis=("34", "47"))
    if t1 is not None:
        el.append(t1)
    el += [Spacer(1, 5 * mm), _section_banner("3. IVA deducible", s), Spacer(1, 2 * mm)]
    t2 = _casillas_table(cmap, ["48", "49", "64"], s, C, emphasis=("64",))
    if t2 is not None:
        el.append(t2)
    el += [Spacer(1, 5 * mm), _section_banner("4. Resultado de la liquidación anual", s), Spacer(1, 2 * mm)]
    t3 = _casillas_table(cmap, ["65", "84", "86"], s, C, emphasis=("86",))
    if t3 is not None:
        el.append(t3)
    resultado = float(cmap["86"].valor) if "86" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado, s, neg_label="RESULTADO A COMPENSAR")]
    el.append(Spacer(1, 4 * mm))
    el.append(Paragraph(
        "Resumen de las casillas clave del Modelo 390 (régimen general). Recargo de "
        "equivalencia, ISP, bienes de inversión, importaciones y prorrata se omiten o van "
        "a 0. Revisa antes de presentar.", s["body"]))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 115 — Retenciones por arrendamiento de inmuebles ───────────────────

def generate_modelo_115_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 115 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    quarter = _q(data.get("periodo", ""))
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_115(data)}
    el: list = [
        Paragraph("Modelo 115 · Retenciones de alquileres", s["title"]),
        Paragraph("Retenciones e ingresos a cuenta · arrendamiento de inmuebles urbanos", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), quarter, year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Liquidación", s),
        Spacer(1, 2 * mm),
    ]
    t = _casillas_table(cmap, ["01", "02", "03", "04", "05"], s, C, emphasis=("03", "05"))
    if t is not None:
        el.append(t)
    resultado = float(cmap["05"].valor) if "05" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado, s)]
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


# ── Modelo 200 — Impuesto sobre Sociedades ─────────────────────────────────────

def generate_modelo_200_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 200 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    el = _header("Modelo 200", "Impuesto sobre Sociedades · Declaración (preview)",
                 data.get("tenant", {}), "Ejercicio anual", data.get("ejercicio", ""), s, C)
    el.append(Paragraph("Resultado contable", s["section"]))
    el.append(_kv_table([
        ("Cifra de negocio (facturas emitidas)", _eur(data.get("cifra_negocio")), False),
        ("Gastos (facturas recibidas)", _eur(data.get("gastos_facturas")), False),
        ("Coste de personal (nóminas + SS empresa)", _eur(data.get("coste_nominas")), False),
        ("Resultado contable", _eur(data.get("resultado_contable")), True),
    ], s, C))
    el.append(Spacer(1, 6 * mm))
    el.append(Paragraph("Liquidación", s["section"]))
    el.append(_kv_table([
        ("Ajustes fiscales", _eur(data.get("ajustes_fiscales")), False),
        ("Base imponible", _eur(data.get("base_imponible")), True),
        ("Tipo impositivo", f"{float(data.get('tipo_impositivo_pct', 0) or 0):.2f} %", False),
        ("Cuota íntegra", _eur(data.get("cuota_integra")), True),
        ("Pagos fraccionados (Modelo 202)", _eur(data.get("pagos_fraccionados_pagados")), False),
        ("RESULTADO DE LA DECLARACIÓN", _eur(data.get("resultado_declaracion")), True),
    ], s, C))
    warning = data.get("_warning")
    if warning:
        el.append(Spacer(1, 5 * mm))
        el.append(Paragraph(
            str(warning),
            ParagraphStyle("Warn200", parent=s["styles"]["Normal"], fontSize=8,
                           fontName="Helvetica-Oblique", textColor=colors.HexColor(C["AMBER"])),
        ))
    el += _footer(s, C)
    return _build(el)


# ── Modelo 100 — IRPF (Declaración de la Renta, preview) ───────────────────────

def generate_modelo_100_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 100 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles(); C = s["C"]
    el = _header("Modelo 100", "IRPF · Declaración de la Renta (preview)",
                 data.get("tenant", {}), "Ejercicio anual", data.get("ejercicio", ""), s, C)
    el.append(Paragraph("Rendimiento de actividad económica", s["section"]))
    el.append(_kv_table([
        ("Ingresos (facturas emitidas)", _eur(data.get("ingresos")), False),
        ("Gastos (facturas recibidas)", _eur(data.get("gastos_facturas")), False),
        ("Coste de personal (nóminas + SS empresa)", _eur(data.get("coste_nominas")), False),
        ("Rendimiento neto", _eur(data.get("rendimiento_neto")), True),
    ], s, C))
    el.append(Spacer(1, 6 * mm))
    el.append(Paragraph("Liquidación", s["section"]))
    el.append(_kv_table([
        ("Mínimo personal y familiar", _eur(data.get("minimo_personal")), False),
        ("Base liquidable", _eur(data.get("base_liquidable")), True),
        ("Cuota íntegra (escala IRPF)", _eur(data.get("cuota_integra")), True),
        ("Retenciones soportadas", _eur(data.get("retenciones_soportadas")), False),
        ("Pagos fraccionados (Modelo 130)", _eur(data.get("pagos_fraccionados_pagados")), False),
        ("RESULTADO DE LA DECLARACIÓN", _eur(data.get("resultado_declaracion")), True),
    ], s, C))
    warning = data.get("_warning")
    if warning:
        el.append(Spacer(1, 5 * mm))
        el.append(Paragraph(
            str(warning),
            ParagraphStyle("Warn100", parent=s["styles"]["Normal"], fontSize=8,
                           fontName="Helvetica-Oblique", textColor=colors.HexColor(C["AMBER"])),
        ))
    el += _footer(s, C)
    return _build(el)
