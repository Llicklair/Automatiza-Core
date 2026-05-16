"""
Renderer de informes PDF generados por agentes IA.

El agente devuelve un objeto Report (JSON validado con Pydantic) y este
módulo lo convierte en un PDF profesional con la paleta corporativa
definida en _pdf_base.py.

Soporta: KPIs, tablas, callouts (info/warning/success/danger) y gráficos
(bar/line/pie) por sección.
"""

from __future__ import annotations

import io
import os
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
)

if REPORTLAB_AVAILABLE:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.legends import Legend
    from reportlab.graphics.charts.linecharts import HorizontalLineChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Image,
        KeepTogether,
        PageBreak,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )


# ─── Schema ──────────────────────────────────────────────────────────────────


class Kpi(BaseModel):
    label: str
    value: str
    trend: Literal["up", "down", "flat", "none"] = "none"
    delta: str | None = None


class TableData(BaseModel):
    columns: list[str]
    rows: list[list[str]]
    caption: str | None = None


class Callout(BaseModel):
    type: Literal["info", "warning", "success", "danger"]
    text: str


class ChartSeries(BaseModel):
    name: str
    values: list[float]


class ChartData(BaseModel):
    type: Literal["bar", "line", "pie"]
    title: str
    labels: list[str]
    series: list[ChartSeries]


class Section(BaseModel):
    heading: str
    body: str = ""
    kpis: list[Kpi] = Field(default_factory=list)
    table: TableData | None = None
    callouts: list[Callout] = Field(default_factory=list)
    chart: ChartData | None = None


class Report(BaseModel):
    title: str
    subtitle: str | None = None
    author: str = "Asistente IA"
    sections: list[Section]
    conclusions: str | None = None


# ─── Render helpers ──────────────────────────────────────────────────────────


_CALLOUT_COLORS = {
    "info": "#3b82f6",
    "warning": "#f59e0b",
    "success": "#10b981",
    "danger": "#ef4444",
}

_TREND_GLYPHS = {"up": "▲", "down": "▼", "flat": "▬", "none": ""}


def _logo_flowable(logo_path: str | None, max_w_mm: float, max_h_mm: float) -> Image | None:
    """Crea un flowable Image escalado para encajar en max_w x max_h (mm)."""
    if not logo_path or not os.path.exists(logo_path):
        return None
    try:
        from reportlab.lib.utils import ImageReader

        reader = ImageReader(logo_path)
        iw, ih = reader.getSize()
        if iw <= 0 or ih <= 0:
            return None
        ratio = iw / ih
        max_w = max_w_mm * mm
        max_h = max_h_mm * mm
        # Encaja respetando aspecto: ata la dimensión más restrictiva
        if max_w / ratio <= max_h:
            w, h = max_w, max_w / ratio
        else:
            w, h = max_h * ratio, max_h
        return Image(logo_path, width=w, height=h)
    except Exception:
        return None


def _build_cover(
    story: list, report: Report, st: dict, tenant_name: str, logo_path: str | None = None
) -> None:
    C = st["C"]
    title_style = ParagraphStyle(
        "RTitle",
        parent=st["styles"]["Normal"],
        fontSize=28,
        leading=34,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(C["SLATE"]),
        spaceAfter=10,
    )
    subtitle_style = ParagraphStyle(
        "RSubtitle",
        parent=st["styles"]["Normal"],
        fontSize=13,
        fontName="Helvetica",
        textColor=colors.HexColor(C["GRAY"]),
        spaceAfter=22,
    )
    meta_style = ParagraphStyle(
        "RMeta",
        parent=st["styles"]["Normal"],
        fontSize=9,
        fontName="Helvetica",
        textColor=colors.HexColor(C["GRAY"]),
    )

    logo = _logo_flowable(logo_path, max_w_mm=45, max_h_mm=22)
    if logo is not None:
        story.append(Spacer(1, 35 * mm))
        story.append(logo)
        story.append(Spacer(1, 15 * mm))
    else:
        story.append(Spacer(1, 60 * mm))
    story.append(Paragraph(report.title, title_style))
    if report.subtitle:
        story.append(Paragraph(report.subtitle, subtitle_style))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.2,
            color=colors.HexColor(C["INDIGO"]),
            spaceBefore=2,
            spaceAfter=12,
        )
    )
    today = datetime.now().strftime("%d/%m/%Y")
    story.append(Paragraph(f"<b>Empresa:</b> {tenant_name}", meta_style))
    story.append(Paragraph(f"<b>Autor:</b> {report.author}", meta_style))
    story.append(Paragraph(f"<b>Fecha:</b> {today}", meta_style))
    story.append(PageBreak())


def _build_kpis(kpis: list[Kpi], st: dict) -> Table | None:
    if not kpis:
        return None
    C = st["C"]
    cells = []
    for k in kpis:
        glyph = _TREND_GLYPHS.get(k.trend, "")
        delta_color = {
            "up": C["EMERALD"],
            "down": C["RED"],
            "flat": C["GRAY"],
            "none": C["GRAY"],
        }[k.trend]
        delta_html = (
            f'<font color="{delta_color}" size="7">{glyph} {k.delta}</font>'
            if k.delta
            else ""
        )
        block = [
            Paragraph(k.value, st["kpi_val"]),
            Paragraph(k.label.upper(), st["kpi_lbl"]),
        ]
        if delta_html:
            block.append(Paragraph(delta_html, st["kpi_lbl"]))
        cells.append(block)

    # Reparte en filas de hasta 4 columnas para que quepa
    per_row = 4 if len(cells) > 3 else len(cells)
    rows = [cells[i : i + per_row] for i in range(0, len(cells), per_row)]
    # Pad última fila
    if rows and len(rows[-1]) < per_row:
        rows[-1] += [""] * (per_row - len(rows[-1]))

    t = Table(rows, colWidths=[(180 / per_row) * mm] * per_row)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(C["LIGHT"])),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(C["LINE"])),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor(C["LINE"])),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def _build_table(td: TableData, st: dict) -> Table:
    C = st["C"]
    data = [td.columns] + td.rows
    t = Table(data, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C["LIGHT"])),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor(C["GRAY"])),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("LINEBELOW", (0, 0), (-1, 0), 1, colors.HexColor(C["LINE"])),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 9),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _build_callout(c: Callout, st: dict) -> Table:
    color_hex = _CALLOUT_COLORS[c.type]
    body_style = ParagraphStyle(
        f"RCallout-{c.type}",
        parent=st["styles"]["Normal"],
        fontSize=9,
        leading=13,
        fontName="Helvetica",
        textColor=colors.HexColor(st["C"]["SLATE"]),
        leftIndent=4,
        alignment=TA_LEFT,
    )
    t = Table([["", Paragraph(c.text, body_style)]], colWidths=[3 * mm, 175 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor(color_hex)),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fafafa")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (1, 0), (1, 0), 8),
                ("RIGHTPADDING", (1, 0), (1, 0), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _palette_colors(C: dict) -> list:
    return [
        colors.HexColor(C["INDIGO"]),
        colors.HexColor(C["EMERALD"]),
        colors.HexColor(C["AMBER"]),
        colors.HexColor(C["BLUE"]),
        colors.HexColor(C["RED"]),
        colors.HexColor(C["GRAY"]),
    ]


def _build_chart(ch: ChartData, st: dict) -> Drawing:
    C = st["C"]
    palette = _palette_colors(C)
    drawing = Drawing(440, 200)

    title = String(220, 180, ch.title, fontSize=10, fillColor=colors.HexColor(C["SLATE"]))
    title.fontName = "Helvetica-Bold"
    title.textAnchor = "middle"
    drawing.add(title)

    if ch.type == "pie":
        series = ch.series[0] if ch.series else ChartSeries(name="", values=[])
        pie = Pie()
        pie.x = 90
        pie.y = 20
        pie.width = 130
        pie.height = 130
        pie.data = series.values or [1]
        pie.labels = ch.labels
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        pie.simpleLabels = 1
        pie.sideLabels = 1
        for i in range(len(pie.data)):
            pie.slices[i].fillColor = palette[i % len(palette)]
        drawing.add(pie)
    elif ch.type == "line":
        chart = HorizontalLineChart()
        chart.x = 50
        chart.y = 30
        chart.width = 360
        chart.height = 130
        chart.data = [s.values for s in ch.series]
        chart.categoryAxis.categoryNames = ch.labels
        chart.valueAxis.valueMin = 0
        chart.lines.strokeWidth = 1.6
        for i in range(len(ch.series)):
            chart.lines[i].strokeColor = palette[i % len(palette)]
        drawing.add(chart)
    else:  # bar
        chart = VerticalBarChart()
        chart.x = 50
        chart.y = 30
        chart.width = 360
        chart.height = 130
        chart.data = [s.values for s in ch.series]
        chart.categoryAxis.categoryNames = ch.labels
        chart.valueAxis.valueMin = 0
        chart.barWidth = 8
        chart.bars.strokeWidth = 0
        for i in range(len(ch.series)):
            chart.bars[i].fillColor = palette[i % len(palette)]
        drawing.add(chart)

    if len(ch.series) > 1 or ch.type == "pie":
        legend = Legend()
        legend.x = 50
        legend.y = 12
        legend.fontName = "Helvetica"
        legend.fontSize = 7
        legend.alignment = "right"
        legend.boxAnchor = "sw"
        legend.dx = 6
        legend.dy = 6
        legend.deltax = 60
        legend.dxTextSpace = 4
        legend.colorNamePairs = [
            (palette[i % len(palette)], (s.name if ch.type != "pie" else ch.labels[i]))
            for i, s in enumerate(ch.series if ch.type != "pie" else ch.labels)
        ]
        drawing.add(legend)

    return drawing


def _build_section(section: Section, st: dict) -> list:
    C = st["C"]
    items: list = []
    heading_style = ParagraphStyle(
        "RHeading",
        parent=st["styles"]["Normal"],
        fontSize=14,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor(C["SLATE"]),
        spaceBefore=14,
        spaceAfter=8,
    )
    body_style = ParagraphStyle(
        "RBody",
        parent=st["styles"]["Normal"],
        fontSize=10,
        leading=15,
        fontName="Helvetica",
        textColor=colors.HexColor(C["SLATE"]),
        spaceAfter=8,
    )
    caption_style = ParagraphStyle(
        "RCaption",
        parent=st["styles"]["Normal"],
        fontSize=7,
        fontName="Helvetica-Oblique",
        textColor=colors.HexColor(C["GRAY"]),
        spaceBefore=2,
        spaceAfter=10,
    )

    items.append(Paragraph(section.heading, heading_style))

    if section.body.strip():
        for paragraph in section.body.split("\n\n"):
            if paragraph.strip():
                items.append(Paragraph(paragraph.strip().replace("\n", "<br/>"), body_style))

    kpi_table = _build_kpis(section.kpis, st)
    if kpi_table is not None:
        items.append(kpi_table)
        items.append(Spacer(1, 8))

    if section.table is not None:
        items.append(_build_table(section.table, st))
        if section.table.caption:
            items.append(Paragraph(section.table.caption, caption_style))
        else:
            items.append(Spacer(1, 8))

    if section.chart is not None:
        items.append(KeepTogether([_build_chart(section.chart, st), Spacer(1, 4)]))

    for c in section.callouts:
        items.append(_build_callout(c, st))
        items.append(Spacer(1, 4))

    return items


def _draw_footer(
    canvas, doc, tenant_name: str, author: str, st: dict, logo_path: str | None = None
) -> None:
    canvas.saveState()
    C = st["C"]
    page_w = A4[0]
    canvas.setStrokeColor(colors.HexColor(C["LINE"]))
    canvas.setLineWidth(0.3)
    canvas.line(15 * mm, 12 * mm, page_w - 15 * mm, 12 * mm)

    if logo_path and os.path.exists(logo_path):
        try:
            from reportlab.lib.utils import ImageReader

            reader = ImageReader(logo_path)
            iw, ih = reader.getSize()
            if iw > 0 and ih > 0:
                target_h = 6 * mm
                target_w = target_h * (iw / ih)
                canvas.drawImage(
                    logo_path,
                    15 * mm,
                    4 * mm,
                    width=target_w,
                    height=target_h,
                    mask="auto",
                    preserveAspectRatio=True,
                )
        except Exception:
            pass

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor(C["FOOTER"]))
    text = f"{tenant_name}  ·  Página {doc.page}  ·  Generado por {author}"
    canvas.drawCentredString(page_w / 2, 8 * mm, text)
    canvas.restoreState()


# ─── Entrypoint ──────────────────────────────────────────────────────────────


def render_agent_report(
    report: Report, tenant_name: str = "", logo_path: str | None = None
) -> bytes:
    """Renderiza un Report como bytes de PDF.

    Si logo_path apunta a una imagen existente, se dibuja en la portada
    y un thumbnail en el footer de cada página.
    """
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("ReportLab no está disponible — instala 'reportlab' para usar PDFs.")

    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    st = _common_styles()

    story: list = []
    _build_cover(story, report, st, tenant_name, logo_path=logo_path)

    for section in report.sections:
        story.extend(_build_section(section, st))

    if report.conclusions and report.conclusions.strip():
        C = st["C"]
        story.append(Spacer(1, 14))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.HexColor(C["LINE"]),
                spaceBefore=2,
                spaceAfter=8,
            )
        )
        conclusions_heading = ParagraphStyle(
            "RConclHeading",
            parent=st["styles"]["Normal"],
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor(C["INDIGO"]),
            spaceAfter=6,
        )
        conclusions_body = ParagraphStyle(
            "RConclBody",
            parent=st["styles"]["Normal"],
            fontSize=10,
            leading=15,
            fontName="Helvetica",
            textColor=colors.HexColor(C["SLATE"]),
        )
        story.append(Paragraph("Conclusiones", conclusions_heading))
        for paragraph in report.conclusions.split("\n\n"):
            if paragraph.strip():
                story.append(Paragraph(paragraph.strip().replace("\n", "<br/>"), conclusions_body))

    def _on_page(canvas, doc_):
        _draw_footer(canvas, doc_, tenant_name, report.author, st, logo_path=logo_path)

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buffer.getvalue()


# ─── Markdown report (xhtml2pdf — HTML+CSS para look profesional) ────────────
#
# Pipeline: el LLM emite markdown → markdown-it-py → HTML → xhtml2pdf → PDF.
# El stylesheet corporativo embebido replica el look de un whitepaper
# (cabecera con título grande + línea índigo, H2 con underline gris, tablas
# con header gris claro y zebra rows, blockquotes con barra ámbar).
#
# Sin dependencias nativas: xhtml2pdf usa ReportLab internamente pero la API
# de entrada es HTML+CSS, mucho más expresiva que construir flowables a mano.


import html as _html
import re as _re

_INLINE_BOLD = _re.compile(r"\*\*(.+?)\*\*")
_INLINE_ITALIC = _re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_INLINE_CODE = _re.compile(r"`([^`\n]+?)`")


def _md_inline(text: str) -> str:
    """Convierte markdown inline (**bold**, *italic*, `code`) a HTML mini de ReportLab."""
    # Escapa los caracteres XML primero
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = _INLINE_BOLD.sub(r"<b>\1</b>", text)
    text = _INLINE_ITALIC.sub(r"<i>\1</i>", text)
    text = _INLINE_CODE.sub(r'<font face="Courier">\1</font>', text)
    return text


def _md_styles(st: dict) -> dict:
    C = st["C"]
    sty = st["styles"]

    def s(name: str, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=sty["Normal"], **kw)

    return {
        "h1": s("MdH1", fontSize=22, fontName="Helvetica-Bold", textColor=colors.HexColor(C["SLATE"]),
                spaceBefore=18, spaceAfter=10, leading=26),
        "h2": s("MdH2", fontSize=15, fontName="Helvetica-Bold", textColor=colors.HexColor(C["SLATE"]),
                spaceBefore=22, spaceAfter=4, leading=18),
        "h3": s("MdH3", fontSize=11.5, fontName="Helvetica-Bold", textColor=colors.HexColor(C["INDIGO"]),
                spaceBefore=14, spaceAfter=4, leading=14),
        "p": s("MdP", fontSize=10.5, leading=16, fontName="Helvetica",
               textColor=colors.HexColor(C["SLATE"]), spaceAfter=8),
        "li": s("MdLi", fontSize=10.5, leading=15, fontName="Helvetica",
                textColor=colors.HexColor(C["SLATE"]),
                leftIndent=18, bulletIndent=4, spaceAfter=3),
        "quote": s("MdQ", fontSize=10.5, leading=15, fontName="Helvetica-Oblique",
                   textColor=colors.HexColor(C["GRAY"]),
                   leftIndent=14, spaceBefore=4, spaceAfter=10,
                   borderColor=colors.HexColor(C["INDIGO"]), borderWidth=0,
                   borderPadding=(0, 0, 0, 6)),
    }


def _md_table(rows: list[list[str]], st: dict) -> Table:
    C = st["C"]
    cell_style = ParagraphStyle("MdCell", parent=st["styles"]["Normal"],
                                fontSize=9.5, leading=13, fontName="Helvetica",
                                textColor=colors.HexColor(C["SLATE"]))
    head_style = ParagraphStyle("MdHead", parent=st["styles"]["Normal"],
                                fontSize=9, fontName="Helvetica-Bold",
                                textColor=colors.HexColor(C["GRAY"]))
    data = [[Paragraph(_md_inline(c), head_style) for c in rows[0]]]
    for r in rows[1:]:
        data.append([Paragraph(_md_inline(c), cell_style) for c in r])
    n_rows = len(data)
    style = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(C["LIGHT"])),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, colors.HexColor(C["GRAY"])),
        ("LINEABOVE", (0, 0), (-1, 0), 0.6, colors.HexColor(C["LINE"])),
        # Filas
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        # Línea inferior fina
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
        # Bordes externos
        ("LINEABOVE", (0, -1), (-1, -1), 0, colors.white),  # neutro
        ("BOX", (0, 0), (-1, -1), 0.3, colors.HexColor(C["LINE"])),
    ]
    # Zebra: filas pares con un gris muy claro
    for i in range(2, n_rows, 2):
        style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#fafbfc")))
    t = Table(data, repeatRows=1, hAlign="LEFT")
    t.setStyle(TableStyle(style))
    return t


def _parse_markdown(body: str, st: dict) -> list:
    """Convierte markdown plano en una lista de flowables ReportLab.

    Soporta:
      # / ## / ### headings
      Párrafos (separados por línea en blanco)
      Listas con `- ` o `* ` o `1. `
      Tablas markdown ( | col | col | con separator | --- | --- | )
      Blockquote `> texto`
      Línea horizontal `---`
      Inline: **bold**, *italic*, `code`
    """
    s = _md_styles(st)
    flow: list = []
    lines = body.replace("\r\n", "\n").split("\n")
    i = 0
    bullets: list[str] = []
    table_rows: list[list[str]] = []
    para_lines: list[str] = []

    def flush_para():
        nonlocal para_lines
        if para_lines:
            txt = " ".join(_md_inline(l.strip()) for l in para_lines if l.strip())
            if txt:
                flow.append(Paragraph(txt, s["p"]))
            para_lines = []

    def flush_bullets():
        nonlocal bullets
        for b in bullets:
            # Bullet manual con guion-em y sangría — más fiable que bulletText
            # cuando ReportLab tiene fuentes core sin glyph U+2022 visible.
            flow.append(Paragraph("•&nbsp;&nbsp;" + _md_inline(b), s["li"]))
        bullets = []

    def flush_table():
        nonlocal table_rows
        if len(table_rows) >= 2:
            flow.append(_md_table(table_rows, st))
            flow.append(Spacer(1, 6))
        table_rows = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Tabla markdown: la primera fila empieza con '|' y la segunda es separador
        if stripped.startswith("|") and stripped.endswith("|") and i + 1 < len(lines):
            sep = lines[i + 1].strip()
            if _re.match(r"^\|?\s*:?-{2,}", sep) and "|" in sep:
                flush_para(); flush_bullets()
                # Recoger filas
                rows: list[list[str]] = []
                rows.append([c.strip() for c in stripped.strip("|").split("|")])
                i += 2  # skip separator
                while i < len(lines) and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                    i += 1
                table_rows = rows
                flush_table()
                continue

        # Headings
        if stripped.startswith("### "):
            flush_para(); flush_bullets(); flush_table()
            flow.append(Paragraph(_md_inline(stripped[4:]), s["h3"]))
        elif stripped.startswith("## "):
            flush_para(); flush_bullets(); flush_table()
            flow.append(Paragraph(_md_inline(stripped[3:]), s["h2"]))
            # Línea separadora indigo fina debajo del H2 — refuerza jerarquía
            C = st["C"]
            flow.append(HRFlowable(
                width="100%", thickness=0.8,
                color=colors.HexColor(C["INDIGO"]),
                spaceBefore=0, spaceAfter=10,
            ))
        elif stripped.startswith("# "):
            flush_para(); flush_bullets(); flush_table()
            flow.append(Paragraph(_md_inline(stripped[2:]), s["h1"]))
        # HR
        elif stripped in ("---", "***", "___"):
            flush_para(); flush_bullets(); flush_table()
            C = st["C"]
            flow.append(HRFlowable(width="100%", thickness=0.5,
                                   color=colors.HexColor(C["LINE"]),
                                   spaceBefore=4, spaceAfter=8))
        # Blockquote
        elif stripped.startswith(">"):
            flush_para(); flush_bullets()
            flow.append(Paragraph(_md_inline(stripped.lstrip(">").strip()), s["quote"]))
        # Bullet list
        elif _re.match(r"^[-*]\s+", stripped):
            flush_para()
            bullets.append(_re.sub(r"^[-*]\s+", "", stripped))
        # Ordered list (los renderizamos como bullet también para simplificar)
        elif _re.match(r"^\d+\.\s+", stripped):
            flush_para()
            bullets.append(_re.sub(r"^\d+\.\s+", "", stripped))
        # Línea vacía → separador
        elif not stripped:
            flush_para(); flush_bullets()
        # Texto normal
        else:
            flush_bullets()
            para_lines.append(stripped)
        i += 1

    flush_para(); flush_bullets(); flush_table()
    return flow


class MarkdownReport(BaseModel):
    title: str
    subtitle: str | None = None
    author: str = "Asistente IA"


_PDF_STYLESHEET = """
@page {
  size: A4;
  margin: 28mm 18mm 22mm 18mm;
  @frame header_frame {
    -pdf-frame-content: header_content;
    left: 18mm; right: 18mm; top: 12mm; height: 10mm;
  }
  @frame footer_frame {
    -pdf-frame-content: footer_content;
    left: 18mm; right: 18mm; bottom: 8mm; height: 10mm;
  }
}
@page first_page {
  size: A4;
  margin: 22mm 18mm 22mm 18mm;
  @frame footer_frame_cover {
    -pdf-frame-content: footer_content;
    left: 18mm; right: 18mm; bottom: 8mm; height: 10mm;
  }
}
body { font-family: Helvetica, Arial, sans-serif; font-size: 10.5pt;
       line-height: 1.55; color: #1e293b; }

/* Portada */
.cover { -pdf-page-template: first_page; padding-top: 38mm;
         page-break-after: always; }
.cover .logo { margin-bottom: 14mm; }
.cover .logo img { max-width: 56mm; max-height: 24mm; }
.cover .badge { display: inline; color: #6366f1; font-size: 8.5pt;
                font-weight: bold; letter-spacing: 2pt;
                background: #eef2ff; padding: 4pt 10pt;
                border-radius: 2pt; }
.cover h1 { font-size: 28pt; color: #1e293b; font-weight: bold;
            margin: 14pt 0 6pt 0; padding-bottom: 10pt;
            border-bottom: 1.4pt solid #6366f1;
            line-height: 1.15; }
.cover .subtitle { color: #64748b; font-size: 14pt; font-style: italic;
                   margin: 0 0 30pt 0; }
.cover .meta { color: #64748b; font-size: 10pt; line-height: 1.8;
               background: #f8fafc; padding: 14pt 16pt;
               border-left: 2.5pt solid #6366f1; }
.cover .meta b { color: #1e293b; }
.cover .footnote { position: absolute; bottom: 0;
                   color: #94a3b8; font-size: 8pt; font-style: italic;
                   margin-top: 30mm; }

/* Header de páginas interiores */
.page-header { color: #94a3b8; font-size: 8pt;
               border-bottom: 0.3pt solid #e2e8f0;
               padding-bottom: 3pt; }
.page-header b { color: #6366f1; }

/* Cuerpo */
h1 { font-size: 19pt; color: #1e293b; margin-top: 14pt;
     margin-bottom: 6pt; }
h2 { font-size: 15pt; color: #1e293b; margin-top: 22pt;
     margin-bottom: 6pt; padding-bottom: 4pt;
     border-bottom: 0.6pt solid #e2e8f0; }
h3 { font-size: 12pt; color: #6366f1; margin-top: 14pt;
     margin-bottom: 4pt; }
p { margin: 0 0 8pt 0; text-align: justify; }
strong, b { color: #1e293b; }

/* Listas */
ul, ol { padding-left: 22pt; margin: 4pt 0 12pt 0; }
li { margin-bottom: 4pt; }

/* Tablas — xhtml2pdf no soporta border-collapse ni :nth-child;
   se usan padding y borders en cada celda. */
table { width: 100%; margin: 10pt 0 16pt 0; }
thead th { background: #f8fafc; color: #64748b; font-weight: bold;
           font-size: 9pt; padding: 8pt 10pt;
           border-bottom: 1.2pt solid #64748b;
           text-align: left; }
tbody td { padding: 7pt 10pt;
           border-bottom: 0.3pt solid #e2e8f0;
           font-size: 9.5pt; vertical-align: middle; }

/* Blockquotes — callouts coloreados según prefijo del primer párrafo:
   "Nota:" → azul info, "Aviso:" → ámbar warning, "Recomendación:" → verde,
   "Importante:" → rojo. Default → ámbar. */
blockquote { border-left: 3pt solid #f59e0b; background: #fffbeb;
             padding: 8pt 12pt; margin: 10pt 0;
             color: #92400e; font-style: italic; }
blockquote.info { border-left-color: #3b82f6; background: #eff6ff;
                  color: #1e40af; }
blockquote.success { border-left-color: #10b981; background: #ecfdf5;
                     color: #065f46; }
blockquote.danger { border-left-color: #ef4444; background: #fef2f2;
                    color: #991b1b; }
blockquote p { margin: 0; }

/* Línea horizontal */
hr { background-color: #e2e8f0; height: 0.4pt; margin: 16pt 0;
     border: none; }

/* Code inline */
code { font-family: Courier; background: #f1f5f9;
       padding: 1pt 3pt; font-size: 9pt; }

/* Footer */
.footer-content { padding-top: 4pt;
                  border-top: 0.3pt solid #e2e8f0;
                  text-align: center;
                  color: #94a3b8; font-size: 7.5pt; }
.footer-content .accent { color: #6366f1; font-weight: bold; }
"""


def _classify_blockquotes(html_body: str) -> str:
    """Detecta el tipo de callout en cada blockquote según el prefijo del texto.
    Añade class="info|warning|success|danger" para que el CSS lo coloree.
    """
    pattern = _re.compile(r"<blockquote>(.*?)</blockquote>", _re.DOTALL)

    def repl(m: _re.Match) -> str:
        body = m.group(1)
        plain = _re.sub(r"<[^>]+>", "", body).strip().lower()
        if plain.startswith(("nota:", "info:", "información:", "informacion:")):
            cls = "info"
        elif plain.startswith(("aviso:", "atención:", "atencion:", "warning:")):
            cls = ""  # default ámbar ya
        elif plain.startswith(("recomendación:", "recomendacion:", "consejo:", "tip:")):
            cls = "success"
        elif plain.startswith(("importante:", "peligro:", "riesgo:", "alerta:")):
            cls = "danger"
        else:
            cls = ""
        if cls:
            return f'<blockquote class="{cls}">{body}</blockquote>'
        return m.group(0)

    return pattern.sub(repl, html_body)


def render_markdown_report(
    title: str,
    body: str,
    author: str = "Asistente IA",
    subtitle: str | None = None,
    tenant_name: str = "",
    logo_path: str | None = None,
) -> bytes:
    """Renderiza un PDF a partir de un body en markdown usando xhtml2pdf + CSS.

    Args:
        title: título del informe (aparece en portada).
        body: cuerpo en markdown estándar (CommonMark).
        author: firma del informe.
        subtitle: subtítulo opcional bajo el título de la portada.
        tenant_name: nombre de la empresa (aparece en portada y footer).
        logo_path: ruta absoluta a una imagen (PNG/JPG); si existe, se dibuja
                   en la portada.
    """
    try:
        from markdown_it import MarkdownIt
        from xhtml2pdf import pisa
    except ImportError as e:
        raise RuntimeError(
            "Falta dependencia para PDF (markdown-it-py o xhtml2pdf): " + str(e)
        ) from e

    from datetime import date as _date

    # commonmark base + tablas GFM. Sin linkify (no instalado).
    md = MarkdownIt("commonmark", {"html": False, "breaks": False, "linkify": False}).enable("table")
    body_html = md.render(body or "")
    body_html = _classify_blockquotes(body_html)

    today = _date.today().strftime("%d/%m/%Y")

    # Sanitizar campos del usuario (escape HTML en strings de portada)
    safe_title = _html.escape(title or "Informe")
    safe_subtitle = _html.escape(subtitle or "") if subtitle else ""
    safe_author = _html.escape(author or "Asistente IA")
    safe_tenant = _html.escape(tenant_name or "")

    logo_html = ""
    if logo_path and os.path.exists(logo_path):
        # Path absoluto entre comillas; xhtml2pdf lo resuelve via link_callback
        logo_html = f'<div class="logo"><img src="{_html.escape(logo_path)}" /></div>'

    subtitle_html = f'<p class="subtitle">{safe_subtitle}</p>' if safe_subtitle else ""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <style>{_PDF_STYLESHEET}</style>
</head>
<body>
  <div id="header_content">
    <div class="page-header">
      <b>{safe_title}</b>
    </div>
  </div>
  <div id="footer_content">
    <div class="footer-content">
      {safe_tenant + ' &middot; ' if safe_tenant else ''}<span class="accent">P&aacute;gina <pdf:pagenumber/></span> &middot; Generado por {safe_author}
    </div>
  </div>

  <div class="cover">
    {logo_html}
    <p><span class="badge">INFORME</span></p>
    <h1>{safe_title}</h1>
    {subtitle_html}
    <p class="meta">
      <b>Empresa:</b> {safe_tenant or 'AutomatizaPyme'}<br/>
      <b>Autor:</b> {safe_author}<br/>
      <b>Fecha:</b> {today}
    </p>
  </div>

  {body_html}
</body>
</html>
"""

    def _link_callback(uri: str, rel: str) -> str:
        # xhtml2pdf llama a esto para resolver paths de imágenes/recursos.
        # Devolvemos el path tal cual si existe localmente.
        if os.path.exists(uri):
            return uri
        return uri

    buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        full_html,
        dest=buffer,
        encoding="utf-8",
        link_callback=_link_callback,
    )
    if pisa_status.err:
        raise RuntimeError(
            f"xhtml2pdf falló al generar el PDF ({pisa_status.err} errores)"
        )
    return buffer.getvalue()
