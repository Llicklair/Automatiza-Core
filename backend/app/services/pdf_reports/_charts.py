"""Constructores de graficas (bar chart, pie chart) para snapshot PDF."""

from app.services.documents._pdf_base import REPORTLAB_AVAILABLE

if REPORTLAB_AVAILABLE:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.units import mm


def build_bar_chart(
    labels: list[str],
    values: list[float],
    bar_colors: list,
    width=110,  # in mm
    height=55,  # in mm
) -> "Drawing":
    """Genera Drawing con grafica de barras verticales."""
    w = width * mm
    h = height * mm
    d = Drawing(w, h)
    chart = VerticalBarChart()
    chart.x = 35
    chart.y = 20
    chart.width = w - 50
    chart.height = h - 30

    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 8
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fillColor = colors.HexColor("#64748b")
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fillColor = colors.HexColor("#64748b")
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
    chart.valueAxis.gridStrokeWidth = 0.5
    chart.valueAxis.forceZero = True

    max_v = max(abs(v) for v in values) if values else 1
    chart.valueAxis.valueMax = max_v * 1.25
    chart.valueAxis.valueMin = min(0, min(values) * 1.1)

    chart.bars[0].fillColor = bar_colors[0]
    chart.bars[0].strokeColor = colors.white
    chart.bars[0].strokeWidth = 0.5

    for i, c_ in enumerate(bar_colors):
        chart.bars[(0, i)].fillColor = c_

    d.add(chart)
    return d


def build_pie_chart(
    items: list[tuple[str, float, "colors.Color"]],
    total: float,
    width=100,  # in mm
    height=70,  # in mm
) -> "Drawing":
    """Genera Drawing con grafica circular.

    items: lista de (label, valor, color).
    total: suma total para calcular porcentajes.
    """
    w = width * mm
    h = height * mm
    d = Drawing(w, h)
    pie = Pie()
    pie.x = w * 0.25
    pie.y = 12
    pie.width = min(h - 24, w * 0.4)
    pie.height = min(h - 24, w * 0.4)
    pie.data = [v for _, v, _ in items]
    pie.labels = (
        [f"{lbl}\n{(v / total * 100):.1f}%" for lbl, v, _ in items]
        if total > 0
        else [lbl for lbl, _, _ in items]
    )
    pie.sideLabels = True
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = colors.white
    pie.sideLabelsOffset = 0.15
    for i, (_, _, c_) in enumerate(items):
        pie.slices[i].fillColor = c_
    pie.slices.fontSize = 7
    pie.slices.fontName = "Helvetica"
    d.add(pie)
    return d
