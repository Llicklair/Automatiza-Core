"""
Generación de PDF: informe mensual de gestión (snapshot).
"""

import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

from app.services.documents._pdf_base import REPORTLAB_AVAILABLE

if REPORTLAB_AVAILABLE:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )


def generate_snapshot_pdf(snap: dict, company_name: str, month: str) -> bytes:
    """
    Genera el informe mensual con gráficas de barras y circular.

    snap: dict con estructura igual a CompanySnapshot:
      snap["facturas"], snap["banca"], snap["rrhh"], snap["clientes"], snap["resumen_ejecutivo"]
    """
    if not REPORTLAB_AVAILABLE:
        return _snapshot_text_fallback(snap, company_name, month)

    # ── Paleta de colores ──
    C_INDIGO = colors.HexColor("#6366f1")
    C_EMERALD = colors.HexColor("#10b981")
    C_RED = colors.HexColor("#ef4444")
    C_AMBER = colors.HexColor("#f59e0b")
    C_BLUE = colors.HexColor("#3b82f6")
    C_SLATE = colors.HexColor("#1e293b")
    C_GRAY = colors.HexColor("#64748b")
    C_LIGHT = colors.HexColor("#f8fafc")
    C_LINE = colors.HexColor("#e2e8f0")
    C_FOOTER = colors.HexColor("#94a3b8")

    # ── Datos ──
    f = snap.get("facturas", {})
    b = snap.get("banca", {})
    h = snap.get("rrhh", {})
    c = snap.get("clientes", {})
    resumen = snap.get("resumen_ejecutivo", "")

    ingresos = float(f.get("ingresos_total", 0))
    gastos = float(f.get("gastos_total", 0))
    margen = float(f.get("margen_bruto", 0))
    margen_pct = float(f.get("margen_pct", 0))
    pendiente = float(f.get("importe_pendiente_cobro", 0))
    n_emitidas = int(f.get("facturas_emitidas", 0))
    n_recibidas = int(f.get("facturas_recibidas", 0))
    n_pend = int(f.get("facturas_pendientes_cobro", 0))

    bank_in = float(b.get("total_ingresos", 0))
    bank_out = float(b.get("total_gastos", 0))
    bank_neto = float(b.get("saldo_neto", 0))
    n_tx = int(b.get("transacciones", 0))
    n_rec = int(b.get("reconciliadas", 0))

    empleados = int(h.get("empleados_activos", 0))
    nominas = float(h.get("coste_nominas", 0))
    nom_pagadas = int(h.get("nominas_pagadas", 0))
    nom_pend = int(h.get("nominas_pendientes", 0))

    total_cli = int(c.get("total_clientes", 0))
    nuevos_cli = int(c.get("nuevos_periodo", 0))
    top_name = c.get("top_client_name") or ""
    top_amt = float(c.get("top_client_amount", 0))

    # ── Mes legible ──
    try:
        y, mo = month.split("-")
        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]
        month_label = f"{meses[int(mo) - 1]} {y}"
    except Exception:
        month_label = month

    # ── Documento ──
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_company = sty("Co", fontSize=20, fontName="Helvetica-Bold", textColor=C_SLATE)
    s_badge = sty("Ba", fontSize=9, fontName="Helvetica-Bold", textColor=C_INDIGO)
    s_month = sty(
        "Mo", fontSize=13, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT
    )
    s_generated = sty(
        "Ge", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_RIGHT
    )
    s_section = sty(
        "Se", fontSize=10, fontName="Helvetica-Bold", textColor=C_GRAY, spaceBefore=8, spaceAfter=4
    )
    s_body = sty("Bo", fontSize=9, fontName="Helvetica", textColor=C_SLATE, leading=13)
    s_resumen = sty(
        "Re",
        fontSize=9,
        fontName="Helvetica",
        textColor=colors.HexColor("#334155"),
        leading=14,
        leftIndent=4 * mm,
        rightIndent=4 * mm,
    )
    sty("Kv", fontSize=16, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_CENTER)
    s_kpi_lbl = sty("Kl", fontSize=7, fontName="Helvetica", textColor=C_GRAY, alignment=TA_CENTER)
    s_footer = sty("Fo", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_CENTER)
    s_row_lbl = sty("Rl", fontSize=8, fontName="Helvetica", textColor=C_GRAY)
    s_row_val = sty(
        "Rv", fontSize=8, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT
    )
    s_row_val_em = sty(
        "Rve", fontSize=8, fontName="Helvetica-Bold", textColor=C_INDIGO, alignment=TA_RIGHT
    )

    def fmt_eur(v):
        return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")

    def fmt_int(v):
        return str(int(v))

    elements = []

    # ── CABECERA ──
    header_data = [
        [
            [
                Paragraph(company_name, s_company),
                Spacer(1, 3),
                Paragraph("INFORME MENSUAL DE GESTIÓN", s_badge),
            ],
            [
                Paragraph(month_label, s_month),
                Spacer(1, 3),
                Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", s_generated),
            ],
        ]
    ]
    header_table = Table(header_data, colWidths=[110 * mm, 65 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.append(header_table)
    elements.append(Spacer(1, 5 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_INDIGO))
    elements.append(Spacer(1, 6 * mm))

    # ── RESUMEN EJECUTIVO ──
    elements.append(Paragraph("RESUMEN EJECUTIVO", s_section))
    resumen_box = Table([[Paragraph(resumen, s_resumen)]], colWidths=[175 * mm])
    resumen_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eef2ff")),
                ("LINEABOVE", (0, 0), (-1, 0), 2, C_INDIGO),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(resumen_box)
    elements.append(Spacer(1, 5 * mm))

    # ── KPI CARDS ──
    def kpi_cell(val: str, lbl: str, color):
        return [
            Paragraph(
                val,
                sty(
                    "kv2",
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=color,
                    alignment=TA_CENTER,
                ),
            ),
            Spacer(1, 2),
            Paragraph(lbl, s_kpi_lbl),
        ]

    kpi_data = [
        [
            kpi_cell(fmt_eur(ingresos), "Ingresos", C_EMERALD),
            kpi_cell(fmt_eur(gastos), "Gastos", C_RED),
            kpi_cell(fmt_eur(margen), f"Margen ({margen_pct:.1f}%)", C_INDIGO),
            kpi_cell(fmt_eur(pendiente), f"Pendiente cobro\n({n_pend} fact.)", C_AMBER),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[43.75 * mm] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, C_EMERALD),
                ("BOX", (1, 0), (1, 0), 0.5, C_RED),
                ("BOX", (2, 0), (2, 0), 0.5, C_INDIGO),
                ("BOX", (3, 0), (3, 0), 0.5, C_AMBER),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f0fdf4")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fef2f2")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#eef2ff")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#fffbeb")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 6 * mm))

    # ── GRÁFICA 1 — Barra: Ingresos / Gastos / Margen ──
    elements.append(Paragraph("1. ANÁLISIS DE FACTURACIÓN", s_section))

    def _bar_chart(labels, values, bar_colors, width=110 * mm, height=55 * mm) -> Drawing:
        d = Drawing(width, height)
        chart = VerticalBarChart()
        chart.x = 35
        chart.y = 20
        chart.width = width - 50
        chart.height = height - 30
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

    bar_labels = ["Ingresos", "Gastos", "Margen bruto"]
    bar_values = [ingresos, gastos, margen]
    bar_colors_list = [C_EMERALD, C_RED, C_INDIGO if margen >= 0 else C_RED]
    bar_drawing = _bar_chart(bar_labels, bar_values, bar_colors_list)

    fac_detail = [
        [Paragraph("Concepto", s_row_lbl), Paragraph("Valor", s_row_val)],
        [Paragraph("Facturas emitidas", s_row_lbl), Paragraph(fmt_int(n_emitidas), s_row_val)],
        [Paragraph("Facturas recibidas", s_row_lbl), Paragraph(fmt_int(n_recibidas), s_row_val)],
        [
            Paragraph("Pend. de cobro", s_row_lbl),
            Paragraph(f"{n_pend} · {fmt_eur(pendiente)}", s_row_val),
        ],
        [Paragraph("Margen bruto", s_row_lbl), Paragraph(fmt_eur(margen), s_row_val_em)],
    ]
    fac_tbl = Table(fac_detail, colWidths=[35 * mm, 25 * mm])
    fac_tbl.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, C_LINE),
                ("LINEBELOW", (0, 1), (-1, -2), 0.3, colors.HexColor("#f1f5f9")),
                ("BACKGROUND", (0, 0), (-1, 0), C_LIGHT),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ]
        )
    )

    combined_fac = Table([[bar_drawing, fac_tbl]], colWidths=[115 * mm, 65 * mm])
    combined_fac.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.append(combined_fac)
    elements.append(Spacer(1, 5 * mm))

    # ── GRÁFICA 2 — Circular: Distribución de costes ──
    elements.append(Paragraph("2. DISTRIBUCIÓN DE COSTES", s_section))

    pie_data_raw = [
        ("Gastos facturación", gastos, C_RED),
        ("Nóminas", nominas, C_AMBER),
        ("Salidas bancarias", bank_out, C_BLUE),
    ]
    pie_data_raw = [(lbl, v, c_) for lbl, v, c_ in pie_data_raw if v > 0]
    total_costes = sum(v for _, v, _ in pie_data_raw)

    def _pie_chart(items, width=100 * mm, height=70 * mm) -> Drawing:
        d = Drawing(width, height)
        pie = Pie()
        pie.x = width * 0.25
        pie.y = 12
        pie.width = min(height - 24, width * 0.4)
        pie.height = min(height - 24, width * 0.4)
        pie.data = [v for _, v, _ in items]
        pie.labels = (
            [f"{lbl}\n{(v / total_costes * 100):.1f}%" for lbl, v, _ in items]
            if total_costes > 0
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

    if pie_data_raw:
        pie_drawing = _pie_chart(pie_data_raw, width=100 * mm, height=70 * mm)

        right_sections = []
        right_sections.append(
            [
                Paragraph(
                    "BANCA", sty("bs", fontSize=8, fontName="Helvetica-Bold", textColor=C_BLUE)
                ),
                "",
            ]
        )
        right_sections.append(
            [Paragraph("Entradas", s_row_lbl), Paragraph(fmt_eur(bank_in), s_row_val)]
        )
        right_sections.append(
            [Paragraph("Salidas", s_row_lbl), Paragraph(fmt_eur(bank_out), s_row_val)]
        )
        right_sections.append(
            [Paragraph("Saldo neto", s_row_lbl), Paragraph(fmt_eur(bank_neto), s_row_val_em)]
        )
        right_sections.append(
            [Paragraph(f"Movimientos: {n_tx}  Reconciliados: {n_rec}", s_row_lbl), ""]
        )
        right_sections.append(["", ""])
        right_sections.append(
            [
                Paragraph(
                    "RRHH", sty("rs", fontSize=8, fontName="Helvetica-Bold", textColor=C_AMBER)
                ),
                "",
            ]
        )
        right_sections.append(
            [Paragraph("Empleados activos", s_row_lbl), Paragraph(fmt_int(empleados), s_row_val)]
        )
        right_sections.append(
            [Paragraph("Coste nóminas", s_row_lbl), Paragraph(fmt_eur(nominas), s_row_val)]
        )
        right_sections.append(
            [Paragraph(f"Pagadas: {nom_pagadas}  Pendientes: {nom_pend}", s_row_lbl), ""]
        )

        right_tbl = Table(right_sections, colWidths=[50 * mm, 30 * mm])
        right_tbl.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("SPAN", (0, 0), (1, 0)),
                    ("SPAN", (0, 4), (1, 4)),
                    ("SPAN", (0, 5), (1, 5)),
                    ("SPAN", (0, 6), (1, 6)),
                    ("SPAN", (0, 9), (1, 9)),
                    ("LINEBELOW", (0, 0), (1, 0), 0.5, C_BLUE),
                    ("LINEBELOW", (0, 6), (1, 6), 0.5, C_AMBER),
                ]
            )
        )

        combined_pie = Table([[pie_drawing, right_tbl]], colWidths=[100 * mm, 80 * mm])
        combined_pie.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(combined_pie)
    else:
        elements.append(Paragraph("Sin datos de costes para este período.", s_body))

    elements.append(Spacer(1, 5 * mm))

    # ── SECCIÓN 3 — CLIENTES ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3 * mm))
    elements.append(Paragraph("3. CLIENTES", s_section))

    cli_data = [
        [Paragraph("Clientes totales", s_row_lbl), Paragraph(fmt_int(total_cli), s_row_val)],
        [Paragraph("Nuevos este período", s_row_lbl), Paragraph(fmt_int(nuevos_cli), s_row_val)],
    ]
    if top_name:
        cli_data.append(
            [
                Paragraph("Cliente principal", s_row_lbl),
                Paragraph(f"{top_name}  ·  {fmt_eur(top_amt)}", s_row_val_em),
            ]
        )
    cli_tbl = Table(cli_data, colWidths=[60 * mm, 115 * mm])
    cli_tbl.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -2), 0.3, colors.HexColor("#f1f5f9")),
            ]
        )
    )
    elements.append(cli_tbl)
    elements.append(Spacer(1, 8 * mm))

    # ── PIE ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3 * mm))
    elements.append(
        Paragraph(
            "Informe generado automáticamente por el motor de IA de AutomatizaCore · "
            f"Período: {month_label} · {datetime.now().strftime('%d/%m/%Y')}",
            s_footer,
        )
    )

    doc.build(elements)
    return buffer.getvalue()


def _snapshot_text_fallback(snap: dict, company_name: str, month: str) -> bytes:
    """Fallback de texto plano si ReportLab no está disponible."""
    f = snap.get("facturas", {})
    lines = [
        f"INFORME MENSUAL {month} — {company_name}",
        f"Ingresos: {f.get('ingresos_total', 0):.2f} EUR",
        f"Gastos: {f.get('gastos_total', 0):.2f} EUR",
        f"Margen: {f.get('margen_bruto', 0):.2f} EUR",
    ]
    return "\n".join(lines).encode("utf-8")
