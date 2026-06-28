"""
Renderer de informes PDF generados por agentes IA.

El agente devuelve un objeto Report (JSON validado con Pydantic) y este
módulo lo convierte en un PDF profesional con la paleta corporativa
definida en pdf_base.py.

Soporta: KPIs, tablas, callouts (info/warning/success/danger) y gráficos
(bar/line/pie) por sección.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
)

logger = logging.getLogger(__name__)

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
    today = datetime.now(UTC).strftime("%d/%m/%Y")
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
            logger.debug("No se pudo dibujar el logo en el pie del informe; continúo", exc_info=True)

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
