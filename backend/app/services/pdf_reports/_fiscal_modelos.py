"""Generación de PDF borrador imprimible para los modelos AEAT 130/111/115/190/
347/349/390/200/100.

Reutiliza los helpers de maquetación "calcada" de `_aeat_layout.py` y los de
reportlab de `pdf_base.py`. Cada PDF es un BORRADOR informativo (no válido para
presentación), pensado para descargar e imprimir con los datos del tenant.
Defensivo: tolera campos ausentes.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime

from app.core.datetime_utils import BUSINESS_TZ
from app.services.aeat.casillas_100 import build_casillas_100
from app.services.aeat.casillas_111 import build_casillas_111
from app.services.aeat.casillas_115 import build_casillas_115
from app.services.aeat.casillas_130 import build_casillas_130
from app.services.aeat.casillas_190 import build_casillas_190
from app.services.aeat.casillas_200 import build_casillas_200
from app.services.aeat.casillas_347 import build_casillas_347
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


def _eur(v) -> str:
    try:
        return f"{float(v or 0):.2f} €"
    except (TypeError, ValueError):
        return "0.00 €"


def _footer(s, C) -> list:
    return [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])),
        Spacer(1, 3 * mm),
        Paragraph(
            "Documento informativo generado automáticamente. No sustituye la presentación oficial ante la AEAT.",
            ParagraphStyle(
                "Foot",
                parent=s["styles"]["Normal"],
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=colors.HexColor(C["RED"]),
                alignment=TA_CENTER,
            ),
        ),
        Spacer(1, 2 * mm),
        Paragraph(f"Generado por AutomatizaCore · {datetime.now(BUSINESS_TZ).strftime('%d/%m/%Y %H:%M')}", s["footer"]),
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
    s = _common_styles()
    C = s["C"]
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
    tbl_i = _casillas_table(cmap, ["01", "02", "03", "04", "05", "06", "07"], s, C, emphasis=("03", "07"))
    if tbl_i is not None:
        el.append(tbl_i)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("3. Total liquidación (Apartado III)", s),
        Spacer(1, 2 * mm),
    ]
    tbl_iii = _casillas_table(cmap, ["12", "13", "14", "15", "16", "17", "18", "19"], s, C, emphasis=("19",))
    if tbl_iii is not None:
        el.append(tbl_iii)

    resultado_19 = float(cmap["19"].valor) if "19" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado_19, s, neg_label="DECLARACIÓN NEGATIVA")]

    el.append(Spacer(1, 4 * mm))
    el.append(
        Paragraph(
            "Las casillas 05, 06, 13, 15, 16 y 18 dependen de datos del contribuyente "
            "(retenciones, pagos previos, deducciones) y se muestran a 0 por defecto: "
            "revísalas y ajústalas antes de presentar.",
            s["body"],
        )
    )
    el += _footer(s, C)
    return _build(el)


# ── Modelo 111 — Retenciones del trabajo ──────────────────────────────────────


def generate_modelo_111_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 111 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
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
    el.append(
        Paragraph(
            "Las casillas 07-09 (actividades económicas/profesionales) son editables y se "
            "muestran a 0 por defecto. Los bloques de retribución en especie, premios y otros "
            "se omiten en este borrador. Revisa antes de presentar.",
            s["body"],
        )
    )
    el += _footer(s, C)
    return _build(el)


# ── Modelo 190 — Resumen anual de retenciones ─────────────────────────────────


def generate_modelo_190_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 190 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_190(data)}
    perceptores = data.get("perceptores", []) or []
    el: list = [
        Paragraph("Modelo 190 · Resumen anual de retenciones", s["title"]),
        Paragraph("Retenciones e ingresos a cuenta del IRPF · trabajo y actividades económicas", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), "Anual", year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Resumen de los datos incluidos en la declaración", s),
        Spacer(1, 2 * mm),
    ]
    t = _casillas_table(cmap, ["01", "02", "03"], s, C, emphasis=("02", "03"))
    if t is not None:
        el.append(t)
    el += [
        Spacer(1, 5 * mm),
        _section_banner(f"3. Relación de perceptores ({len(perceptores)})", s),
        Spacer(1, 2 * mm),
    ]
    rows = [
        [
            Paragraph("Clave", s["header"]),
            Paragraph("Perceptor", s["header"]),
            Paragraph("NIF", s["header"]),
            Paragraph("Percepción íntegra", s["header"]),
            Paragraph("Retención", s["header"]),
        ]
    ]
    for p in perceptores:
        rows.append(
            [
                Paragraph(str(p.get("clave_percepcion") or "—"), s["body"]),
                Paragraph(str(p.get("nombre") or "—"), s["body"]),
                Paragraph(str(p.get("nif") or "—"), s["body"]),
                Paragraph(_eur(p.get("percepcion_integra")), s["right"]),
                Paragraph(_eur(p.get("retencion_practicada")), s["right"]),
            ]
        )
    if not perceptores:
        rows.append([Paragraph("Sin perceptores en el ejercicio", s["body"])] + [Paragraph("", s["body"])] * 4)
    tbl = Table(rows, colWidths=[15 * mm, 60 * mm, 32 * mm, 36 * mm, 32 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (3, 0), (-1, -1), "RIGHT")]))
    el += [tbl]
    el += _footer(s, C)
    return _build(el)


# ── Modelo 347 — Operaciones con terceros ─────────────────────────────────────


def generate_modelo_347_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 347 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_347(data)}
    declarables = data.get("declarables", []) or []
    el: list = [
        Paragraph("Modelo 347 · Operaciones con terceras personas", s["title"]),
        Paragraph("Declaración anual de operaciones con terceros (umbral 3.005,06 €, IVA incluido)", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), "Anual", year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Resumen de los datos declarados", s),
        Spacer(1, 2 * mm),
    ]
    t = _casillas_table(cmap, ["01", "02", "03", "04"], s, C, emphasis=("02", "04"))
    if t is not None:
        el.append(t)
    el += [
        Spacer(1, 5 * mm),
        _section_banner(
            f"3. Relación de operaciones con terceros " f"({data.get('num_declarables', len(declarables))})", s
        ),
        Spacer(1, 2 * mm),
    ]
    rows = [
        [
            Paragraph("NIF", s["header"]),
            Paragraph("Nombre / Razón social", s["header"]),
            Paragraph("Emitidas", s["header"]),
            Paragraph("Recibidas", s["header"]),
        ]
    ]
    for d in declarables:
        rows.append(
            [
                Paragraph(str(d.get("nif") or "—"), s["body"]),
                Paragraph(str(d.get("nombre") or "—"), s["body"]),
                Paragraph(_eur(d.get("importe_emitidas")), s["right"]),
                Paragraph(_eur(d.get("importe_recibidas")), s["right"]),
            ]
        )
    if not declarables:
        rows.append(
            [
                Paragraph("Sin operaciones que superen el umbral", s["body"]),
                Paragraph("", s["body"]),
                Paragraph("", s["body"]),
                Paragraph("", s["body"]),
            ]
        )
    tbl = Table(rows, colWidths=[32 * mm, 73 * mm, 35 * mm, 35 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (2, 0), (-1, -1), "RIGHT")]))
    el += [tbl]
    el += _footer(s, C)
    return _build(el)


# ── Modelo 390 — Resumen anual de IVA ─────────────────────────────────────────


def generate_modelo_390_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 390 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
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
    t1 = _casillas_table(cmap, ["01", "02", "03", "04", "05", "06", "33", "34", "47"], s, C, emphasis=("34", "47"))
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
    el.append(
        Paragraph(
            "Resumen de las casillas clave del Modelo 390 (régimen general). Recargo de "
            "equivalencia, ISP, bienes de inversión, importaciones y prorrata se omiten o van "
            "a 0. Revisa antes de presentar.",
            s["body"],
        )
    )
    el += _footer(s, C)
    return _build(el)


# ── Modelo 115 — Retenciones por arrendamiento de inmuebles ───────────────────


def generate_modelo_115_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 115 BORRADOR {data.get('periodo')}/{data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
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
    s = _common_styles()
    C = s["C"]
    q = data.get("periodo", "")
    year = data.get("ejercicio", "")
    ops = data.get("operaciones", []) or []
    num_op = data.get("num_operadores", len(ops))
    el: list = [
        Paragraph("Modelo 349 · Operaciones intracomunitarias", s["title"]),
        Paragraph("Declaración recapitulativa de operaciones intracomunitarias", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), _q(q), year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Resumen de la declaración", s),
        Spacer(1, 2 * mm),
    ]
    # La hoja-resumen del 349 no numera casillas: se rotulan los totales por etiqueta.
    el.append(
        _kv_table(
            [
                ("Número total de operadores intracomunitarios", str(num_op), False),
                ("Importe total de las operaciones intracomunitarias", _eur(data.get("total_base_imponible")), True),
            ],
            s,
            C,
        )
    )
    el += [
        Spacer(1, 5 * mm),
        _section_banner(f"3. Relación de operaciones intracomunitarias ({num_op})", s),
        Spacer(1, 2 * mm),
    ]
    rows = [
        [
            Paragraph("NIF-IVA", s["header"]),
            Paragraph("País", s["header"]),
            Paragraph("Contraparte", s["header"]),
            Paragraph("Clave", s["header"]),
            Paragraph("Base imponible", s["header"]),
        ]
    ]
    for o in ops:
        rows.append(
            [
                Paragraph(str(o.get("nif_intracomunitario") or "—"), s["body"]),
                Paragraph(str(o.get("pais_codigo") or "—"), s["body"]),
                Paragraph(str(o.get("nombre_contraparte") or "—"), s["body"]),
                Paragraph(str(o.get("tipo_operacion") or "—"), s["body"]),
                Paragraph(_eur(o.get("base_imponible")), s["right"]),
            ]
        )
    if not ops:
        rows.append(
            [Paragraph("Sin operaciones intracomunitarias en el período", s["body"])] + [Paragraph("", s["body"])] * 4
        )
    tbl = Table(rows, colWidths=[34 * mm, 16 * mm, 56 * mm, 22 * mm, 47 * mm])
    tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (4, 0), (-1, -1), "RIGHT")]))
    el += [tbl]
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
    s = _common_styles()
    C = s["C"]
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_200(data)}
    el: list = [
        Paragraph("Modelo 200 · Impuesto sobre Sociedades", s["title"]),
        Paragraph("Declaración del Impuesto sobre Sociedades (preview)", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), "Anual", year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Liquidación · Casillas clave", s),
        Spacer(1, 2 * mm),
    ]
    t = _casillas_table(
        cmap, ["00500", "00552", "00558", "00562", "00592", "00601", "00621"], s, C, emphasis=("00552", "00621")
    )
    if t is not None:
        el.append(t)
    resultado = float(cmap["00621"].valor) if "00621" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado, s, neg_label="RESULTADO A DEVOLVER")]
    el.append(Spacer(1, 4 * mm))
    el.append(
        Paragraph(
            f"Preview de las casillas clave del Impuesto sobre Sociedades. Las correcciones al "
            f"resultado contable (ajustes fiscales estimados {_eur(data.get('ajustes_fiscales'))}) no "
            f"tienen casilla-resumen única (van en el rango 00355–00414) y las retenciones e ingresos "
            f"a cuenta tampoco (rango 01785–01799); por eso no se detallan aquí. La cuota líquida "
            f"(00592) se muestra sin deducciones aplicadas. Revisa antes de presentar.",
            s["body"],
        )
    )
    warning = data.get("_warning")
    if warning:
        el.append(Spacer(1, 3 * mm))
        el.append(
            Paragraph(
                str(warning),
                ParagraphStyle(
                    "Warn200",
                    parent=s["styles"]["Normal"],
                    fontSize=8,
                    fontName="Helvetica-Oblique",
                    textColor=colors.HexColor(C["AMBER"]),
                ),
            )
        )
    el += _footer(s, C)
    return _build(el)


# ── Modelo 100 — IRPF (Declaración de la Renta, preview) ───────────────────────


def generate_modelo_100_pdf(data: dict) -> bytes:
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 100 BORRADOR {data.get('ejercicio')}\n".encode()
    s = _common_styles()
    C = s["C"]
    year = data.get("ejercicio", "")
    cmap = {c.codigo: c for c in build_casillas_100(data)}
    el: list = [
        Paragraph("Modelo 100 · IRPF (Declaración de la Renta)", s["title"]),
        Paragraph("Declaración de la Renta de las Personas Físicas (preview)", s["section"]),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), "Anual", year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Liquidación · Casillas clave", s),
        Spacer(1, 2 * mm),
    ]
    t = _casillas_table(cmap, ["0224", "0500", "0519", "0595", "0596", "0604", "0670"], s, C, emphasis=("0500", "0670"))
    if t is not None:
        el.append(t)
    resultado = float(cmap["0670"].valor) if "0670" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado, s, neg_label="RESULTADO A DEVOLVER")]
    el.append(Spacer(1, 4 * mm))
    el.append(
        Paragraph(
            "Preview de las casillas clave de la Renta (numeración válida para Renta 2024/2025). La "
            "cuota se muestra agregada —el modelo la desglosa en estatal (0545) y autonómica (0546)— y "
            "sin deducciones aplicadas. Las retenciones (0596) y el mínimo personal y familiar (0519) "
            "dependen de tus circunstancias: revísalos antes de presentar.",
            s["body"],
        )
    )
    warning = data.get("_warning")
    if warning:
        el.append(Spacer(1, 3 * mm))
        el.append(
            Paragraph(
                str(warning),
                ParagraphStyle(
                    "Warn100",
                    parent=s["styles"]["Normal"],
                    fontSize=8,
                    fontName="Helvetica-Oblique",
                    textColor=colors.HexColor(C["AMBER"]),
                ),
            )
        )
    el += _footer(s, C)
    return _build(el)
