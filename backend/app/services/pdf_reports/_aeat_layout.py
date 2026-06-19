"""Helpers de maquetación tipo formulario AEAT (casillas numeradas).

Componentes reutilizables para PDFs "calcados" de modelos oficiales: badge de
borrador, banda de sección gris/naranja, tabla de identificación del declarante,
tabla de casillas (código | descripción | importe) y badge de resultado.

Hogar canónico compartido. NOTA: `_fiscal_modelo303.py` mantiene de momento copias
propias equivalentes de estos helpers; su migración a este módulo es un follow-up
aislado y verificable por separado (ver tasks/todo.md, F2.9b). El Modelo 130 ya usa
este módulo.

Las funciones son agnósticas del modelo: los importes se formatean en € por
defecto; las casillas que representan porcentajes se indican vía `pct_codes`
(en el 130 no hay ninguna; en el 303 sí).
"""

from __future__ import annotations

from app.services.pdf.pdf_base import REPORTLAB_AVAILABLE

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle

# Paleta característica de los formularios AEAT: gris + naranja.
_AEAT_ORANGE = "#c2410c"
_AEAT_GRAY_BG = "#f3f4f6"

_QUARTER_LABELS = {
    1: "1T (Enero – Marzo)",
    2: "2T (Abril – Junio)",
    3: "3T (Julio – Septiembre)",
    4: "4T (Octubre – Diciembre)",
}


def _draft_badge(s, C) -> "Table":
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


def _section_banner(text: str, s) -> "Table":
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


def _identificacion_table(tenant: dict, quarter: int, year, s) -> "Table":
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


def _fmt_casilla(c, pct_codes=frozenset()) -> str:
    """Formatea el valor de una casilla. Prioriza el atributo `formato` de la casilla
    ('numero'/'porcentaje'/'euro'); si no lo tiene, usa `pct_codes` para el '%'
    (compatibilidad con el Modelo 303, cuyas casillas no llevan `formato`)."""
    formato = getattr(c, "formato", None)
    if formato == "numero":
        return f"{int(round(float(c.valor)))}"
    if formato == "porcentaje" or c.codigo in pct_codes:
        return f"{float(c.valor):.2f} %"
    return f"{float(c.valor):.2f} €"


def _casillas_table(cmap: dict, codes: list, s, C, emphasis: tuple = (),
                    pct_codes=frozenset()) -> "Table | None":
    """Tabla de casillas: [código (naranja)] | descripción | valor. `emphasis`
    resalta filas de totales (fondo gris + negrita). `pct_codes` marca las casillas
    que se formatean como porcentaje en lugar de importe."""
    code_style = _casilla_code_style(s)
    rows: list = []
    emph_idx: list = []
    for cod in codes:
        c = cmap.get(cod)
        if c is None:
            continue
        if cod in emphasis:
            emph_idx.append(len(rows))
        rows.append([
            Paragraph(cod, code_style),
            Paragraph(c.descripcion, s["body"]),
            Paragraph(_fmt_casilla(c, pct_codes), s["right"]),
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


def _resultado_badge(resultado: float, s, pos_label: str = "RESULTADO A INGRESAR",
                     neg_label: str = "RESULTADO A COMPENSAR") -> "Table":
    a_ingresar = resultado >= 0
    label = pos_label if a_ingresar else neg_label
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
