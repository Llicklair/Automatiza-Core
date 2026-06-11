"""
Generación de PDF: Modelo 303 — Autoliquidación IVA trimestral.

Replica el formato oficial de la AEAT con casillas numeradas: identificación del
declarante, devengo (ejercicio/período) y liquidación con las casillas oficiales
(régimen general 01-09, intra/ISP 10-13, recargo de equivalencia 16-24, total
devengada 27, deducible 28-45 y resultado 46-71). Se marca como BORRADOR — no
sustituye la presentación telemática ante la AEAT.
"""

import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

from app.services.aeat.casillas_303 import build_casillas_303
from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle


# Paleta característica de los formularios AEAT: gris + naranja.
_AEAT_ORANGE = "#c2410c"
_AEAT_GRAY_BG = "#f3f4f6"

# Casillas cuyo valor es un porcentaje (tipo impositivo), no un importe.
_PCT_CASILLAS = {"02", "05", "08", "17", "20", "23", "65"}

_QUARTER_LABELS = {
    1: "1T (Enero – Marzo)",
    2: "2T (Abril – Junio)",
    3: "3T (Julio – Septiembre)",
    4: "4T (Octubre – Diciembre)",
}


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _draft_badge(s, C) -> Table:
    badge = Table(
        [[Paragraph(
            "BORRADOR — NO VÁLIDO PARA PRESENTACIÓN ANTE LA AEAT",
            ParagraphStyle(
                "DraftBadge", parent=s["styles"]["Normal"], fontSize=9,
                fontName="Helvetica-Bold", textColor=colors.HexColor(C["AMBER"]),
            ),
        )]],
        colWidths=[175 * mm],
    )
    badge.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(C["AMBER"])),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    return badge


def _section_banner(text: str, s) -> Table:
    """Banda de sección con el estilo administrativo gris/naranja de la AEAT."""
    banner = Table(
        [[Paragraph(
            text,
            ParagraphStyle(
                "AeatSection", parent=s["styles"]["Normal"], fontSize=10,
                fontName="Helvetica-Bold", textColor=colors.white,
            ),
        )]],
        colWidths=[175 * mm],
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(_AEAT_ORANGE)),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return banner


def _identificacion_table(tenant: dict, quarter: int, year: int, s) -> Table:
    data = [
        [Paragraph("NIF", s["header"]), Paragraph(tenant.get("nif", "—"), s["body"]),
         Paragraph("Apellidos y nombre / Razón social", s["header"]),
         Paragraph(tenant.get("name", "—"), s["body"])],
        [Paragraph("Ejercicio", s["header"]), Paragraph(str(year), s["body"]),
         Paragraph("Período", s["header"]),
         Paragraph(_QUARTER_LABELS.get(quarter, str(quarter)), s["body"])],
    ]
    tbl = Table(data, colWidths=[22 * mm, 45 * mm, 60 * mm, 48 * mm])
    tbl.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(_AEAT_GRAY_BG)),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor(_AEAT_GRAY_BG)),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    return tbl


def _casilla_code_style(s) -> "ParagraphStyle":
    return ParagraphStyle(
        "CasillaCod", parent=s["styles"]["Normal"], fontSize=8,
        fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_CENTER,
    )


def _fmt_casilla(c) -> str:
    if c.codigo in _PCT_CASILLAS:
        return f"{float(c.valor):.2f} %"
    return f"{float(c.valor):.2f} €"


def _casillas_table(cmap: dict, codes: list[str], s, C, emphasis: tuple = ()) -> "Table | None":
    """Tabla de casillas: [código (naranja)] | descripción | valor. `emphasis`
    resalta filas de totales (fondo gris + negrita)."""
    code_style = _casilla_code_style(s)
    rows: list = []
    emph_idx: list[int] = []
    for cod in codes:
        c = cmap.get(cod)
        if c is None:
            continue
        if cod in emphasis:
            emph_idx.append(len(rows))
        rows.append([
            Paragraph(cod, code_style),
            Paragraph(c.descripcion, s["body"]),
            Paragraph(_fmt_casilla(c), s["right"]),
        ])
    if not rows:
        return None
    tbl = Table(rows, colWidths=[12 * mm, 123 * mm, 40 * mm])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(_AEAT_ORANGE)),
        ("LEFTPADDING", (0, 0), (0, -1), 2),
        ("RIGHTPADDING", (0, 0), (0, -1), 2),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor(C["LINE"])),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
    ]
    for i in emph_idx:
        style.append(("BACKGROUND", (1, i), (-1, i), colors.HexColor(_AEAT_GRAY_BG)))
        style.append(("FONTNAME", (1, i), (-1, i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(style))
    return tbl


def _resultado_badge(resultado: float, s) -> Table:
    a_ingresar = resultado >= 0
    label = "RESULTADO A INGRESAR" if a_ingresar else "RESULTADO A COMPENSAR"
    color = "#b91c1c" if a_ingresar else "#047857"
    tbl = Table(
        [[Paragraph(
            label,
            ParagraphStyle("ResLbl", parent=s["styles"]["Normal"], fontSize=11,
                           fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_RIGHT),
        ),
          Paragraph(
            f"{abs(resultado):.2f} €",
            ParagraphStyle("ResVal", parent=s["styles"]["Normal"], fontSize=13,
                           fontName="Helvetica-Bold", textColor=colors.white, alignment=TA_RIGHT),
        )]],
        colWidths=[120 * mm, 55 * mm],
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(color)),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return tbl


# ---------------------------------------------------------------------------
# Modelo 303 — Autoliquidación IVA (formato oficial AEAT)
# ---------------------------------------------------------------------------


def generate_modelo_303_pdf(data: dict) -> bytes:
    """Genera el PDF borrador del Modelo 303 con las casillas oficiales AEAT.

    `data` es el dict de `build_modelo_303_data` (tenant, quarter, year,
    vat_collected, vat_deducted, vat_intra, vat_isp, recargo_equivalencia).
    """
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 303 BORRADOR Q{data.get('quarter')}/{data.get('year')}\n".encode()

    s = _common_styles()
    C = s["C"]
    quarter = int(data.get("quarter", 1))
    year = int(data.get("year", datetime.now().year))

    casillas = build_casillas_303(data)
    cmap = {c.codigo: c for c in casillas}

    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    el: list = [
        Paragraph(
            "Modelo 303 · Impuesto sobre el Valor Añadido · Autoliquidación",
            s["title"],
        ),
        Spacer(1, 3 * mm),
        _draft_badge(s, C),
        Spacer(1, 5 * mm),
        _section_banner("1. Identificación (Declarante)", s),
        Spacer(1, 2 * mm),
        _identificacion_table(data.get("tenant", {}), quarter, year, s),
        Spacer(1, 5 * mm),
        _section_banner("2. Devengo · Liquidación — IVA devengado", s),
        Spacer(1, 2 * mm),
    ]

    # IVA devengado: régimen general (01-09), intra/ISP (10-13), recargo (16-24
    # solo si hay), total cuota devengada (27).
    devengado_codes = ["01", "02", "03", "04", "05", "06", "07", "08", "09",
                       "10", "11", "12", "13"]
    for cod_b, cod_c in (("16", "18"), ("19", "21"), ("22", "24")):
        cb, cc = cmap.get(cod_b), cmap.get(cod_c)
        if (cb and float(cb.valor)) or (cc and float(cc.valor)):
            base, tipo = cod_b, str(int(cod_b) + 1)
            devengado_codes += [base, tipo, cod_c]
    devengado_codes.append("27")
    dev_tbl = _casillas_table(cmap, devengado_codes, s, C, emphasis=("27",))
    if dev_tbl is not None:
        el.append(dev_tbl)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("3. Liquidación — IVA deducible", s),
        Spacer(1, 2 * mm),
    ]
    ded_tbl = _casillas_table(
        cmap, ["28", "29", "30", "31", "36", "37", "45"], s, C, emphasis=("45",)
    )
    if ded_tbl is not None:
        el.append(ded_tbl)

    el += [
        Spacer(1, 5 * mm),
        _section_banner("Resultado de la autoliquidación", s),
        Spacer(1, 2 * mm),
    ]
    res_tbl = _casillas_table(
        cmap, ["46", "64", "65", "66", "67", "69", "71"], s, C, emphasis=("46", "71"),
    )
    if res_tbl is not None:
        el.append(res_tbl)

    resultado_71 = float(cmap["71"].valor) if "71" in cmap else 0.0
    el += [Spacer(1, 5 * mm), _resultado_badge(resultado_71, s)]

    # Pie legal
    el += [
        Spacer(1, 8 * mm),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])),
        Spacer(1, 3 * mm),
        Paragraph(
            "Documento informativo (borrador) generado automáticamente. No sustituye "
            "la presentación oficial ante la AEAT. Las casillas marcadas como editables "
            "(p. ej. 28, 30, 67) pueden requerir ajuste manual antes de presentar.",
            ParagraphStyle(
                "AEATFooter", parent=s["styles"]["Normal"], fontSize=8,
                fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                alignment=TA_CENTER,
            ),
        ),
        Spacer(1, 2 * mm),
        Paragraph(
            f"Generado por AutomatizaCore · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            s["footer"],
        ),
    ]

    doc.build(el)
    return buffer.getvalue()
