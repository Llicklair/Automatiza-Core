"""
Generación de PDFs de informes: text_report, snapshot mensual, modelo 303,
registro RGPD, cash flow y morosidad.
"""
import io
from datetime import datetime

from app.services._pdf_base import (
    REPORTLAB_AVAILABLE, _common_styles, _fmt_eur, _make_doc,
    _table_header_style, _format_date,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie


# ---------------------------------------------------------------------------
# Informe de texto genérico
# ---------------------------------------------------------------------------

def generate_text_report_pdf(title: str, content: str, category: str = "Informe") -> bytes:
    """
    Genera un PDF profesional a partir de un bloque de texto.
    Ideal para informes de banca, fiscalidad, resúmenes de email, etc.
    """
    if not REPORTLAB_AVAILABLE:
        return content.encode('utf-8')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'],
        fontSize=18, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'),
        spaceAfter=10)
    category_style = ParagraphStyle('ReportCat', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#6366f1'),
        textTransform='uppercase', spaceAfter=5)
    body_style = ParagraphStyle('ReportBody', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#334155'),
        leading=14)
    date_style = ParagraphStyle('ReportDate', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', textColor=colors.HexColor('#94a3b8'),
        alignment=TA_RIGHT)

    elements = []

    elements.append(Paragraph(datetime.now().strftime('%d/%m/%Y %H:%M'), date_style))
    elements.append(Paragraph(category, category_style))
    elements.append(Paragraph(title, title_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    for line in content.split('\n'):
        if not line.strip():
            elements.append(Spacer(1, 3*mm))
            continue
        if line.strip().startswith(('•', '-', '*')):
            p_style = ParagraphStyle('Bullet', parent=body_style, leftIndent=5*mm)
            elements.append(Paragraph(line.strip(), p_style))
        else:
            elements.append(Paragraph(line.strip(), body_style))
            elements.append(Spacer(1, 2*mm))

    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#f1f5f9')))
    elements.append(Paragraph(
        "Generado por el Sistema de Inteligencia Artificial de AutomatizaPyme",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#cbd5e1'))
    ))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Snapshot / Informe mensual de gestión
# ---------------------------------------------------------------------------

def generate_snapshot_pdf(snap: dict, company_name: str, month: str) -> bytes:
    """
    Genera el informe mensual con gráficas de barras y circular.

    snap: dict con estructura igual a CompanySnapshot:
      snap["facturas"], snap["banca"], snap["rrhh"], snap["clientes"], snap["resumen_ejecutivo"]
    """
    if not REPORTLAB_AVAILABLE:
        return _snapshot_text_fallback(snap, company_name, month)

    # ── Paleta de colores ──
    C_INDIGO  = colors.HexColor('#6366f1')
    C_EMERALD = colors.HexColor('#10b981')
    C_RED     = colors.HexColor('#ef4444')
    C_AMBER   = colors.HexColor('#f59e0b')
    C_BLUE    = colors.HexColor('#3b82f6')
    C_SLATE   = colors.HexColor('#1e293b')
    C_GRAY    = colors.HexColor('#64748b')
    C_LIGHT   = colors.HexColor('#f8fafc')
    C_LINE    = colors.HexColor('#e2e8f0')
    C_FOOTER  = colors.HexColor('#94a3b8')

    # ── Datos ──
    f = snap.get("facturas", {})
    b = snap.get("banca", {})
    h = snap.get("rrhh", {})
    c = snap.get("clientes", {})
    resumen = snap.get("resumen_ejecutivo", "")

    ingresos   = float(f.get("ingresos_total", 0))
    gastos     = float(f.get("gastos_total", 0))
    margen     = float(f.get("margen_bruto", 0))
    margen_pct = float(f.get("margen_pct", 0))
    pendiente  = float(f.get("importe_pendiente_cobro", 0))
    n_emitidas = int(f.get("facturas_emitidas", 0))
    n_recibidas = int(f.get("facturas_recibidas", 0))
    n_pend     = int(f.get("facturas_pendientes_cobro", 0))

    bank_in    = float(b.get("total_ingresos", 0))
    bank_out   = float(b.get("total_gastos", 0))
    bank_neto  = float(b.get("saldo_neto", 0))
    n_tx       = int(b.get("transacciones", 0))
    n_rec      = int(b.get("reconciliadas", 0))

    empleados  = int(h.get("empleados_activos", 0))
    nominas    = float(h.get("coste_nominas", 0))
    nom_pagadas = int(h.get("nominas_pagadas", 0))
    nom_pend   = int(h.get("nominas_pendientes", 0))

    total_cli  = int(c.get("total_clientes", 0))
    nuevos_cli = int(c.get("nuevos_periodo", 0))
    top_name   = c.get("top_client_name") or ""
    top_amt    = float(c.get("top_client_amount", 0))

    # ── Mes legible ──
    try:
        y, mo = month.split("-")
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        month_label = f"{meses[int(mo)-1]} {y}"
    except Exception:
        month_label = month

    # ── Documento ──
    buffer = io.BytesIO()
    PAGE_W, PAGE_H = A4
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_company  = sty("Co", fontSize=20, fontName="Helvetica-Bold", textColor=C_SLATE)
    s_badge    = sty("Ba", fontSize=9,  fontName="Helvetica-Bold", textColor=C_INDIGO)
    s_month    = sty("Mo", fontSize=13, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_generated = sty("Ge", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_RIGHT)
    s_section  = sty("Se", fontSize=10, fontName="Helvetica-Bold", textColor=C_GRAY,
                     spaceBefore=8, spaceAfter=4)
    s_body     = sty("Bo", fontSize=9,  fontName="Helvetica", textColor=C_SLATE, leading=13)
    s_resumen  = sty("Re", fontSize=9,  fontName="Helvetica", textColor=colors.HexColor("#334155"),
                     leading=14, leftIndent=4*mm, rightIndent=4*mm)
    s_kpi_val  = sty("Kv", fontSize=16, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_CENTER)
    s_kpi_lbl  = sty("Kl", fontSize=7,  fontName="Helvetica",      textColor=C_GRAY,  alignment=TA_CENTER)
    s_footer   = sty("Fo", fontSize=7,  fontName="Helvetica", textColor=C_FOOTER, alignment=TA_CENTER)
    s_row_lbl  = sty("Rl", fontSize=8,  fontName="Helvetica", textColor=C_GRAY)
    s_row_val  = sty("Rv", fontSize=8,  fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_row_val_em = sty("Rve", fontSize=8, fontName="Helvetica-Bold", textColor=C_INDIGO, alignment=TA_RIGHT)

    fmt_eur = lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    fmt_int = lambda v: str(int(v))

    elements = []

    # ── CABECERA ──
    header_data = [[
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
    ]]
    header_table = Table(header_data, colWidths=[110*mm, 65*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_INDIGO))
    elements.append(Spacer(1, 6*mm))

    # ── RESUMEN EJECUTIVO ──
    elements.append(Paragraph("RESUMEN EJECUTIVO", s_section))
    resumen_box = Table(
        [[Paragraph(resumen, s_resumen)]],
        colWidths=[175*mm],
    )
    resumen_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#eef2ff")),
        ("LINEABOVE",  (0,0), (-1, 0), 2, C_INDIGO),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(resumen_box)
    elements.append(Spacer(1, 5*mm))

    # ── KPI CARDS ──
    def kpi_cell(val: str, lbl: str, color):
        return [
            Paragraph(val, sty("kv2", fontSize=14, fontName="Helvetica-Bold",
                                textColor=color, alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(lbl, s_kpi_lbl),
        ]

    kpi_data = [[
        kpi_cell(fmt_eur(ingresos),  "Ingresos",      C_EMERALD),
        kpi_cell(fmt_eur(gastos),    "Gastos",         C_RED),
        kpi_cell(fmt_eur(margen),    f"Margen ({margen_pct:.1f}%)", C_INDIGO),
        kpi_cell(fmt_eur(pendiente), f"Pendiente cobro\n({n_pend} fact.)", C_AMBER),
    ]]
    kpi_table = Table(kpi_data, colWidths=[43.75*mm]*4)
    kpi_table.setStyle(TableStyle([
        ("BOX",         (0,0), (0,0), 0.5, C_EMERALD),
        ("BOX",         (1,0), (1,0), 0.5, C_RED),
        ("BOX",         (2,0), (2,0), 0.5, C_INDIGO),
        ("BOX",         (3,0), (3,0), 0.5, C_AMBER),
        ("BACKGROUND",  (0,0), (0,0), colors.HexColor("#f0fdf4")),
        ("BACKGROUND",  (1,0), (1,0), colors.HexColor("#fef2f2")),
        ("BACKGROUND",  (2,0), (2,0), colors.HexColor("#eef2ff")),
        ("BACKGROUND",  (3,0), (3,0), colors.HexColor("#fffbeb")),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0), (-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 6*mm))

    # ── GRÁFICA 1 — Barra: Ingresos / Gastos / Margen ──
    elements.append(Paragraph("1. ANÁLISIS DE FACTURACIÓN", s_section))

    def _bar_chart(labels, values, bar_colors, width=110*mm, height=55*mm) -> Drawing:
        d = Drawing(width, height)
        chart = VerticalBarChart()
        chart.x = 35
        chart.y = 20
        chart.width  = width  - 50
        chart.height = height - 30

        chart.data       = [values]
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.fontSize = 8
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fillColor = colors.HexColor("#64748b")
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontName  = "Helvetica"
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
        [Paragraph("Pend. de cobro", s_row_lbl), Paragraph(f"{n_pend} · {fmt_eur(pendiente)}", s_row_val)],
        [Paragraph("Margen bruto", s_row_lbl), Paragraph(fmt_eur(margen), s_row_val_em)],
    ]
    fac_tbl = Table(fac_detail, colWidths=[35*mm, 25*mm])
    fac_tbl.setStyle(TableStyle([
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("LINEBELOW",   (0,0), (-1,0),  0.5, C_LINE),
        ("LINEBELOW",   (0,1), (-1,-2), 0.3, colors.HexColor("#f1f5f9")),
        ("BACKGROUND",  (0,0), (-1,0),  C_LIGHT),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
    ]))

    combined_fac = Table([[bar_drawing, fac_tbl]], colWidths=[115*mm, 65*mm])
    combined_fac.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
    ]))
    elements.append(combined_fac)
    elements.append(Spacer(1, 5*mm))

    # ── GRÁFICA 2 — Circular: Distribución de costes ──
    elements.append(Paragraph("2. DISTRIBUCIÓN DE COSTES", s_section))

    pie_data_raw = [
        ("Gastos facturación", gastos,  C_RED),
        ("Nóminas",            nominas, C_AMBER),
        ("Salidas bancarias",  bank_out, C_BLUE),
    ]
    pie_data_raw = [(lbl, v, c_) for lbl, v, c_ in pie_data_raw if v > 0]
    total_costes = sum(v for _, v, _ in pie_data_raw)

    def _pie_chart(items, width=100*mm, height=70*mm) -> Drawing:
        d = Drawing(width, height)
        pie = Pie()
        pie.x = width * 0.25
        pie.y = 12
        pie.width  = min(height - 24, width * 0.4)
        pie.height = min(height - 24, width * 0.4)
        pie.data   = [v for _, v, _ in items]
        pie.labels = [
            f"{lbl}\n{(v/total_costes*100):.1f}%"
            for lbl, v, _ in items
        ] if total_costes > 0 else [lbl for lbl, _, _ in items]
        pie.sideLabels     = True
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        pie.sideLabelsOffset = 0.15
        for i, (_, _, c_) in enumerate(items):
            pie.slices[i].fillColor = c_
        pie.slices.fontSize    = 7
        pie.slices.fontName    = "Helvetica"
        d.add(pie)
        return d

    if pie_data_raw:
        pie_drawing = _pie_chart(pie_data_raw, width=100*mm, height=70*mm)

        right_sections = []
        right_sections.append([Paragraph("BANCA", sty("bs", fontSize=8, fontName="Helvetica-Bold", textColor=C_BLUE)), ""])
        right_sections.append([Paragraph("Entradas", s_row_lbl), Paragraph(fmt_eur(bank_in), s_row_val)])
        right_sections.append([Paragraph("Salidas", s_row_lbl), Paragraph(fmt_eur(bank_out), s_row_val)])
        right_sections.append([Paragraph("Saldo neto", s_row_lbl), Paragraph(fmt_eur(bank_neto), s_row_val_em)])
        right_sections.append([Paragraph(f"Movimientos: {n_tx}  Reconciliados: {n_rec}", s_row_lbl), ""])
        right_sections.append(["", ""])
        right_sections.append([Paragraph("RRHH", sty("rs", fontSize=8, fontName="Helvetica-Bold", textColor=C_AMBER)), ""])
        right_sections.append([Paragraph("Empleados activos", s_row_lbl), Paragraph(fmt_int(empleados), s_row_val)])
        right_sections.append([Paragraph("Coste nóminas", s_row_lbl), Paragraph(fmt_eur(nominas), s_row_val)])
        right_sections.append([Paragraph(f"Pagadas: {nom_pagadas}  Pendientes: {nom_pend}", s_row_lbl), ""])

        right_tbl = Table(right_sections, colWidths=[50*mm, 30*mm])
        right_tbl.setStyle(TableStyle([
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("TOPPADDING",  (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0), (-1,-1), 0),
            ("SPAN",        (0,0), (1,0)),
            ("SPAN",        (0,4), (1,4)),
            ("SPAN",        (0,5), (1,5)),
            ("SPAN",        (0,6), (1,6)),
            ("SPAN",        (0,9), (1,9)),
            ("LINEBELOW",   (0,0), (1,0), 0.5, C_BLUE),
            ("LINEBELOW",   (0,6), (1,6), 0.5, C_AMBER),
        ]))

        combined_pie = Table([[pie_drawing, right_tbl]], colWidths=[100*mm, 80*mm])
        combined_pie.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ]))
        elements.append(combined_pie)
    else:
        elements.append(Paragraph("Sin datos de costes para este período.", s_body))

    elements.append(Spacer(1, 5*mm))

    # ── SECCIÓN 3 — CLIENTES ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph("3. CLIENTES", s_section))

    cli_data = [
        [Paragraph("Clientes totales", s_row_lbl), Paragraph(fmt_int(total_cli), s_row_val)],
        [Paragraph("Nuevos este período", s_row_lbl), Paragraph(fmt_int(nuevos_cli), s_row_val)],
    ]
    if top_name:
        cli_data.append([
            Paragraph("Cliente principal", s_row_lbl),
            Paragraph(f"{top_name}  ·  {fmt_eur(top_amt)}", s_row_val_em),
        ])
    cli_tbl = Table(cli_data, colWidths=[60*mm, 115*mm])
    cli_tbl.setStyle(TableStyle([
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("LINEBELOW",   (0,0), (-1,-2), 0.3, colors.HexColor("#f1f5f9")),
    ]))
    elements.append(cli_tbl)
    elements.append(Spacer(1, 8*mm))

    # ── PIE ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Informe generado automáticamente por el motor de IA de AutomatizaPyme · "
        f"Período: {month_label} · {datetime.now().strftime('%d/%m/%Y')}",
        s_footer,
    ))

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


# ---------------------------------------------------------------------------
# Modelo 303 — Autoliquidación IVA
# ---------------------------------------------------------------------------

def generate_modelo_303_pdf(data: dict) -> bytes:
    """
    Genera PDF borrador del Modelo 303 (liquidación trimestral IVA).

    data:
    - tenant: dict con name, nif
    - quarter: int (1-4)
    - year: int
    - vat_collected: list of dict con rate, base, quota  (IVA devengado / ventas)
    - vat_deducted: list of dict con rate, base, quota   (IVA deducible / compras)
    """
    if not REPORTLAB_AVAILABLE:
        return f"MODELO 303 BORRADOR Q{data.get('quarter')}/{data.get('year')}\n".encode('utf-8')

    s = _common_styles()
    C = s['C']
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    tenant = data.get('tenant', {})
    quarter = int(data.get('quarter', 1))
    year = int(data.get('year', 2026))
    quarter_labels = {1: "1T (Enero - Marzo)", 2: "2T (Abril - Junio)",
                      3: "3T (Julio - Septiembre)", 4: "4T (Octubre - Diciembre)"}

    # ── CABECERA ──
    elements.append(Paragraph("Modelo 303 — Autoliquidación IVA", s['title']))
    elements.append(Spacer(1, 3*mm))

    draft_style = ParagraphStyle('DraftBadge', parent=s['styles']['Normal'],
        fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor(C['AMBER']))
    draft_data = [[Paragraph("BORRADOR — NO VÁLIDO PARA PRESENTACIÓN", draft_style)]]
    draft_table = Table(draft_data, colWidths=[175*mm])
    draft_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fffbeb')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor(C['AMBER'])),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    elements.append(draft_table)
    elements.append(Spacer(1, 5*mm))

    info_data = [
        [Paragraph("Empresa:", s['header']), Paragraph(tenant.get('name', '—'), s['body']),
         Paragraph("NIF:", s['header']), Paragraph(tenant.get('nif', '—'), s['body'])],
        [Paragraph("Período:", s['header']), Paragraph(quarter_labels.get(quarter, ''), s['body']),
         Paragraph("Ejercicio:", s['header']), Paragraph(str(year), s['body'])],
    ]
    info_table = Table(info_data, colWidths=[22*mm, 65*mm, 22*mm, 65*mm])
    info_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C['INDIGO'])))
    elements.append(Spacer(1, 5*mm))

    # ── SECCIÓN A: IVA DEVENGADO ──
    elements.append(Paragraph("A) IVA DEVENGADO (Ventas y prestaciones de servicios)", s['section']))
    vat_collected = data.get('vat_collected', [])

    vat_col_widths = [50*mm, 45*mm, 45*mm]
    vat_data = [[Paragraph('Tipo IVA', s['header']), Paragraph('Base imponible', s['header']),
                 Paragraph('Cuota', s['header'])]]
    total_col_base = 0.0
    total_col_quota = 0.0
    for row in vat_collected:
        base_v = float(row.get('base', 0))
        quota_v = float(row.get('quota', 0))
        total_col_base += base_v
        total_col_quota += quota_v
        vat_data.append([
            Paragraph(f"{float(row.get('rate', 0)):.0f}%", s['body']),
            Paragraph(f"{base_v:.2f} €", s['right']),
            Paragraph(f"{quota_v:.2f} €", s['right']),
        ])
    vat_data.append([
        Paragraph("TOTAL IVA DEVENGADO", ParagraphStyle('VatTotal', parent=s['styles']['Normal'],
            fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(C['SLATE']))),
        Paragraph(f"{total_col_base:.2f} €", s['right_bold']),
        Paragraph(f"{total_col_quota:.2f} €", s['right_bold']),
    ])

    vat_table = Table(vat_data, colWidths=vat_col_widths)
    vat_table.setStyle(TableStyle(_table_header_style() + [
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor(C['LINE'])),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(vat_table)
    elements.append(Spacer(1, 6*mm))

    # ── SECCIÓN B: IVA DEDUCIBLE ──
    elements.append(Paragraph("B) IVA DEDUCIBLE (Compras y gastos)", s['section']))
    vat_deducted = data.get('vat_deducted', [])

    ded_data = [[Paragraph('Tipo IVA', s['header']), Paragraph('Base imponible', s['header']),
                 Paragraph('Cuota', s['header'])]]
    total_ded_base = 0.0
    total_ded_quota = 0.0
    for row in vat_deducted:
        base_v = float(row.get('base', 0))
        quota_v = float(row.get('quota', 0))
        total_ded_base += base_v
        total_ded_quota += quota_v
        ded_data.append([
            Paragraph(f"{float(row.get('rate', 0)):.0f}%", s['body']),
            Paragraph(f"{base_v:.2f} €", s['right']),
            Paragraph(f"{quota_v:.2f} €", s['right']),
        ])
    ded_data.append([
        Paragraph("TOTAL IVA DEDUCIBLE", ParagraphStyle('DedTotal', parent=s['styles']['Normal'],
            fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(C['SLATE']))),
        Paragraph(f"{total_ded_base:.2f} €", s['right_bold']),
        Paragraph(f"{total_ded_quota:.2f} €", s['right_bold']),
    ])
    ded_table = Table(ded_data, colWidths=vat_col_widths)
    ded_table.setStyle(TableStyle(_table_header_style() + [
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor(C['LINE'])),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#fef2f2')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    elements.append(ded_table)
    elements.append(Spacer(1, 8*mm))

    # ── RESULTADO ──
    resultado = total_col_quota - total_ded_quota
    result_label = "A INGRESAR" if resultado >= 0 else "A COMPENSAR"
    result_color = C['RED'] if resultado >= 0 else C['EMERALD']

    result_data = [
        [Paragraph("IVA devengado (A):", s['right']), Paragraph(f"{total_col_quota:.2f} €", s['right_bold'])],
        [Paragraph("IVA deducible (B):", s['right']), Paragraph(f"{total_ded_quota:.2f} €", s['right_bold'])],
        [Paragraph(f"RESULTADO ({result_label}):", ParagraphStyle('ResLabel', parent=s['styles']['Normal'],
            fontSize=12, fontName='Helvetica-Bold', textColor=colors.HexColor(result_color), alignment=TA_RIGHT)),
         Paragraph(f"{abs(resultado):.2f} €", ParagraphStyle('ResVal', parent=s['styles']['Normal'],
            fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor(result_color), alignment=TA_RIGHT))],
    ]
    result_table = Table(result_data, colWidths=[130*mm, 40*mm], hAlign='RIGHT')
    result_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, 2), (-1, 2), 2, colors.HexColor(result_color)),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#f8fafc')),
    ]))
    elements.append(result_table)
    elements.append(Spacer(1, 10*mm))

    # ── PIE ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C['LINE'])))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Documento informativo generado automáticamente. No sustituye la presentación oficial ante la AEAT.",
        ParagraphStyle('AEATFooter', parent=s['styles']['Normal'],
            fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor(C['RED']), alignment=TA_CENTER)))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"Generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        s['footer']))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Registro RGPD (Art. 30)
# ---------------------------------------------------------------------------

def generate_rgpd_registry_pdf(data: dict) -> bytes:
    """
    Genera PDF del registro obligatorio Art. 30 RGPD.

    data:
    - company: dict con name, nif, address
    - dpo: dict|None con name, email
    - activities: list of dict con name, purpose, legal_basis, data_subjects,
      data_categories, recipients, international_transfers, retention_period, security_measures
    """
    if not REPORTLAB_AVAILABLE:
        return "REGISTRO RGPD\n".encode('utf-8')

    s = _common_styles()
    C = s['C']
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get('company', {})
    dpo = data.get('dpo')

    # ── CABECERA ──
    elements.append(Paragraph("Registro de Actividades de Tratamiento", s['title']))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph("Artículo 30 del Reglamento General de Protección de Datos (UE) 2016/679",
        ParagraphStyle('RGPDSubtitle', parent=s['styles']['Normal'],
            fontSize=9, fontName='Helvetica', textColor=colors.HexColor(C['GRAY']))))
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C['INDIGO'])))
    elements.append(Spacer(1, 5*mm))

    # ── RESPONSABLE DEL TRATAMIENTO ──
    elements.append(Paragraph("RESPONSABLE DEL TRATAMIENTO", s['section']))
    resp_data = [
        [Paragraph("Denominación:", s['header']), Paragraph(company.get('name', '—'), s['body'])],
        [Paragraph("NIF/CIF:", s['header']), Paragraph(company.get('nif', '—'), s['body'])],
        [Paragraph("Dirección:", s['header']), Paragraph(company.get('address', '—'), s['body'])],
    ]
    if dpo:
        resp_data.append([Paragraph("DPO:", s['header']),
                          Paragraph(f"{dpo.get('name', '—')} ({dpo.get('email', '')})", s['body'])])

    resp_table = Table(resp_data, colWidths=[30*mm, 145*mm])
    resp_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#f1f5f9')),
    ]))
    elements.append(resp_table)
    elements.append(Spacer(1, 6*mm))

    # ── ACTIVIDADES DE TRATAMIENTO ──
    activities = data.get('activities', [])
    fields = [
        ('name', 'Actividad de tratamiento'),
        ('purpose', 'Finalidad'),
        ('legal_basis', 'Base legal'),
        ('data_subjects', 'Categorías de interesados'),
        ('data_categories', 'Categorías de datos'),
        ('recipients', 'Destinatarios'),
        ('international_transfers', 'Transferencias internacionales'),
        ('retention_period', 'Plazo de conservación'),
        ('security_measures', 'Medidas de seguridad'),
    ]

    for i, activity in enumerate(activities):
        elements.append(Paragraph(f"ACTIVIDAD {i + 1}: {activity.get('name', '—')}", s['section']))
        act_data = []
        for key, label in fields:
            if key == 'name':
                continue
            val = activity.get(key, '—') or '—'
            act_data.append([
                Paragraph(label, s['header']),
                Paragraph(str(val), s['body']),
            ])

        act_table = Table(act_data, colWidths=[50*mm, 125*mm])
        act_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('LINEBELOW', (0, 0), (-1, -1), 0.3, colors.HexColor('#f1f5f9')),
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8fafc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(act_table)
        elements.append(Spacer(1, 4*mm))

    # ── PIE ──
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C['LINE'])))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f"Registro generado el {datetime.now().strftime('%d/%m/%Y')} · AutomatizaPyme",
        s['footer']))
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph("Firma del Responsable del Tratamiento:", s['header']))
    elements.append(Spacer(1, 20*mm))
    elements.append(HRFlowable(width="60%", thickness=0.5, color=colors.HexColor(C['SLATE'])))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Informe de Tesorería (Cash Flow)
# ---------------------------------------------------------------------------

def generate_cashflow_report_pdf(data: dict) -> bytes:
    """
    Genera PDF de informe de tesorería / cash flow.

    data:
    - company: dict con name, nif
    - period_start: str (ISO)
    - period_end: str (ISO)
    - initial_balance: float
    - total_collections: float
    - total_payments: float
    - final_balance: float
    - periods: list of dict con label, collections, payments, cumulative_balance
    - pending_receivables: list of dict con client_name, invoice_number, due_date, amount
    """
    if not REPORTLAB_AVAILABLE:
        return "INFORME DE TESORERÍA\n".encode('utf-8')

    s = _common_styles()
    C = s['C']
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get('company', {})

    # ── CABECERA ──
    elements.append(Paragraph("Informe de Tesorería", s['title']))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"{company.get('name', '—')}  ·  {_format_date(data.get('period_start', ''))} — {_format_date(data.get('period_end', ''))}",
        ParagraphStyle('CFSubtitle', parent=s['styles']['Normal'],
            fontSize=10, fontName='Helvetica', textColor=colors.HexColor(C['GRAY']))))
    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C['BLUE'])))
    elements.append(Spacer(1, 5*mm))

    # ── KPI CARDS ──
    initial = float(data.get('initial_balance', 0))
    collections = float(data.get('total_collections', 0))
    payments = float(data.get('total_payments', 0))
    final = float(data.get('final_balance', 0))

    def kpi_cell(val_str, lbl, color_hex):
        return [
            Paragraph(val_str, ParagraphStyle('cfkv', parent=s['styles']['Normal'],
                fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor(color_hex), alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(lbl, s['kpi_lbl']),
        ]

    kpi_data = [[
        kpi_cell(_fmt_eur(initial), "Saldo inicial", C['GRAY']),
        kpi_cell(_fmt_eur(collections), "Cobros previstos", C['EMERALD']),
        kpi_cell(_fmt_eur(payments), "Pagos previstos", C['RED']),
        kpi_cell(_fmt_eur(final), "Saldo final", C['BLUE'] if final >= 0 else C['RED']),
    ]]
    kpi_table = Table(kpi_data, colWidths=[43.75*mm]*4)
    kpi_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor(C['GRAY'])),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor(C['EMERALD'])),
        ('BOX', (2, 0), (2, 0), 0.5, colors.HexColor(C['RED'])),
        ('BOX', (3, 0), (3, 0), 0.5, colors.HexColor(C['BLUE'])),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f0fdf4')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#fef2f2')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#eff6ff')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 6*mm))

    # ── TABLA TEMPORAL ──
    periods = data.get('periods', [])
    if periods:
        elements.append(Paragraph("PREVISIÓN POR PERÍODO", s['section']))
        period_col_widths = [50*mm, 35*mm, 35*mm, 40*mm]
        period_data = [[
            Paragraph('Período', s['header']),
            Paragraph('Cobros', s['header']),
            Paragraph('Pagos', s['header']),
            Paragraph('Saldo acumulado', s['header']),
        ]]
        for p in periods:
            coll = float(p.get('collections', 0))
            pay = float(p.get('payments', 0))
            bal = float(p.get('cumulative_balance', 0))
            bal_color = C['EMERALD'] if bal >= 0 else C['RED']
            period_data.append([
                Paragraph(str(p.get('label', '')), s['body']),
                Paragraph(f"{coll:.2f} €", ParagraphStyle('cfGreen', parent=s['styles']['Normal'],
                    fontSize=9, fontName='Helvetica', textColor=colors.HexColor(C['EMERALD']), alignment=TA_RIGHT)),
                Paragraph(f"{pay:.2f} €", ParagraphStyle('cfRed', parent=s['styles']['Normal'],
                    fontSize=9, fontName='Helvetica', textColor=colors.HexColor(C['RED']), alignment=TA_RIGHT)),
                Paragraph(f"{bal:.2f} €", ParagraphStyle('cfBal', parent=s['styles']['Normal'],
                    fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(bal_color), alignment=TA_RIGHT)),
            ])

        period_table = Table(period_data, colWidths=period_col_widths)
        period_table.setStyle(TableStyle(_table_header_style() + [
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(period_table)
        elements.append(Spacer(1, 6*mm))

        # ── GRÁFICA DE BARRAS ──
        try:
            bar_labels = [str(p.get('label', '')) for p in periods]
            bar_coll = [float(p.get('collections', 0)) for p in periods]
            bar_pay = [float(p.get('payments', 0)) for p in periods]

            d = Drawing(175*mm, 55*mm)
            chart = VerticalBarChart()
            chart.x = 40
            chart.y = 20
            chart.width = 175*mm - 55
            chart.height = 55*mm - 30
            chart.data = [bar_coll, bar_pay]
            chart.categoryAxis.categoryNames = bar_labels
            chart.categoryAxis.labels.fontSize = 7
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 7
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.visibleGrid = True
            chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
            chart.valueAxis.forceZero = True
            chart.bars[0].fillColor = colors.HexColor(C['EMERALD'])
            chart.bars[1].fillColor = colors.HexColor(C['RED'])
            chart.bars[0].strokeColor = colors.white
            chart.bars[1].strokeColor = colors.white

            from reportlab.graphics.charts.legends import Legend
            legend = Legend()
            legend.x = 50
            legend.y = 0
            legend.fontSize = 7
            legend.fontName = "Helvetica"
            legend.columnMaximum = 1
            legend.colorNamePairs = [
                (colors.HexColor(C['EMERALD']), 'Cobros'),
                (colors.HexColor(C['RED']), 'Pagos'),
            ]
            d.add(chart)
            d.add(legend)
            elements.append(d)
            elements.append(Spacer(1, 6*mm))
        except Exception:
            pass

    # ── FACTURAS PENDIENTES DE COBRO (TOP 10) ──
    receivables = data.get('pending_receivables', [])
    if receivables:
        elements.append(Paragraph("FACTURAS PENDIENTES DE COBRO (TOP 10)", s['section']))
        recv_data = [[
            Paragraph('Cliente', s['header']),
            Paragraph('Nº Factura', s['header']),
            Paragraph('Vencimiento', s['header']),
            Paragraph('Importe', s['header']),
        ]]
        for r in receivables[:10]:
            recv_data.append([
                Paragraph(str(r.get('client_name', '—')), s['body']),
                Paragraph(str(r.get('invoice_number', '—')), s['body']),
                Paragraph(_format_date(str(r.get('due_date', ''))), s['body']),
                Paragraph(f"{float(r.get('amount', 0)):.2f} €", s['right']),
            ])
        recv_table = Table(recv_data, colWidths=[55*mm, 35*mm, 35*mm, 35*mm])
        recv_table.setStyle(TableStyle(_table_header_style() + [
            ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ]))
        elements.append(recv_table)

    # ── PIE ──
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C['LINE'])))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f"Informe de tesorería generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        s['footer']))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Informe de Morosidad
# ---------------------------------------------------------------------------

def generate_delinquency_report_pdf(data: dict) -> bytes:
    """
    Genera PDF de informe de morosidad / aging analysis.

    data:
    - company: dict con name, nif
    - cutoff_date: str (ISO)
    - total_overdue: float
    - num_overdue: int
    - avg_days_overdue: float
    - worst_client: str
    - aging_buckets: dict con '0-30', '31-60', '61-90', '>90' — cada uno con count, amount
    - overdue_invoices: list of dict con client_name, invoice_number, due_date,
      days_overdue, amount, collection_status
    """
    if not REPORTLAB_AVAILABLE:
        return "INFORME DE MOROSIDAD\n".encode('utf-8')

    s = _common_styles()
    C = s['C']
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get('company', {})

    # ── CABECERA ──
    elements.append(Paragraph("Informe de Morosidad", s['title']))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"{company.get('name', '—')}  ·  Fecha de corte: {_format_date(data.get('cutoff_date', ''))}",
        ParagraphStyle('DelSubtitle', parent=s['styles']['Normal'],
            fontSize=10, fontName='Helvetica', textColor=colors.HexColor(C['GRAY']))))
    elements.append(Spacer(1, 4*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C['RED'])))
    elements.append(Spacer(1, 5*mm))

    # ── KPI CARDS ──
    total_overdue = float(data.get('total_overdue', 0))
    num_overdue = int(data.get('num_overdue', 0))
    avg_days = float(data.get('avg_days_overdue', 0))
    worst = data.get('worst_client', '—')

    def kpi_cell(val_str, lbl, color_hex):
        return [
            Paragraph(val_str, ParagraphStyle('delkv', parent=s['styles']['Normal'],
                fontSize=14, fontName='Helvetica-Bold', textColor=colors.HexColor(color_hex), alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(lbl, s['kpi_lbl']),
        ]

    kpi_data = [[
        kpi_cell(_fmt_eur(total_overdue), "Total moroso", C['RED']),
        kpi_cell(str(num_overdue), "Facturas vencidas", C['AMBER']),
        kpi_cell(f"{avg_days:.0f} días", "Media retraso", C['GRAY']),
        kpi_cell(worst[:20], "Cliente + moroso", C['SLATE']),
    ]]
    kpi_table = Table(kpi_data, colWidths=[43.75*mm]*4)
    kpi_table.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor(C['RED'])),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor(C['AMBER'])),
        ('BOX', (2, 0), (2, 0), 0.5, colors.HexColor(C['GRAY'])),
        ('BOX', (3, 0), (3, 0), 0.5, colors.HexColor(C['SLATE'])),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#fef2f2')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#fffbeb')),
        ('BACKGROUND', (2, 0), (2, 0), colors.HexColor('#f8fafc')),
        ('BACKGROUND', (3, 0), (3, 0), colors.HexColor('#f8fafc')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 6*mm))

    # ── TABLA DE ANTIGÜEDAD (AGING) ──
    elements.append(Paragraph("ANÁLISIS DE ANTIGÜEDAD", s['section']))
    aging = data.get('aging_buckets', {})
    bucket_order = ['0-30', '31-60', '61-90', '>90']
    bucket_colors = [C['AMBER'], '#f97316', C['RED'], '#991b1b']

    aging_header = [Paragraph('Tramo', s['header']), Paragraph('Nº facturas', s['header']),
                    Paragraph('Importe', s['header'])]
    aging_data = [aging_header]
    for bucket, bcolor in zip(bucket_order, bucket_colors):
        b = aging.get(bucket, {})
        aging_data.append([
            Paragraph(f"{bucket} días", ParagraphStyle(f'ag_{bucket}', parent=s['styles']['Normal'],
                fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(bcolor))),
            Paragraph(str(int(b.get('count', 0))), s['right']),
            Paragraph(f"{float(b.get('amount', 0)):.2f} €", s['right']),
        ])

    aging_table = Table(aging_data, colWidths=[50*mm, 40*mm, 50*mm])
    aging_table.setStyle(TableStyle(_table_header_style() + [
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
    ]))
    elements.append(aging_table)
    elements.append(Spacer(1, 6*mm))

    # ── DETALLE DE FACTURAS VENCIDAS ──
    overdue = data.get('overdue_invoices', [])
    if overdue:
        elements.append(Paragraph("DETALLE DE FACTURAS VENCIDAS", s['section']))
        det_col_widths = [40*mm, 25*mm, 25*mm, 20*mm, 25*mm, 25*mm]
        det_data = [[
            Paragraph('Cliente', s['header']),
            Paragraph('Nº Factura', s['header']),
            Paragraph('Vencimiento', s['header']),
            Paragraph('Días', s['header']),
            Paragraph('Importe', s['header']),
            Paragraph('Estado', s['header']),
        ]]
        for inv in overdue:
            days = int(inv.get('days_overdue', 0))

            row = [
                Paragraph(str(inv.get('client_name', '—'))[:25], s['body']),
                Paragraph(str(inv.get('invoice_number', '—')), s['body']),
                Paragraph(_format_date(str(inv.get('due_date', ''))), s['body']),
                Paragraph(str(days), ParagraphStyle('delDays', parent=s['styles']['Normal'],
                    fontSize=9, fontName='Helvetica-Bold',
                    textColor=colors.HexColor(C['RED'] if days > 60 else C['AMBER']), alignment=TA_RIGHT)),
                Paragraph(f"{float(inv.get('amount', 0)):.2f} €", s['right']),
                Paragraph(str(inv.get('collection_status', '—')), s['body']),
            ]
            det_data.append(row)

        det_table = Table(det_data, colWidths=det_col_widths)
        style_cmds = _table_header_style() + [('ALIGN', (3, 0), (4, -1), 'RIGHT')]
        for idx, inv in enumerate(overdue, start=1):
            days = int(inv.get('days_overdue', 0))
            if days > 90:
                style_cmds.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#fef2f2')))
            elif days > 60:
                style_cmds.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#fff7ed')))

        det_table.setStyle(TableStyle(style_cmds))
        elements.append(det_table)

    # ── PIE ──
    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C['LINE'])))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Datos a fecha de generación. Revisar acciones de cobro pendientes.",
        ParagraphStyle('DelNote', parent=s['styles']['Normal'],
            fontSize=8, fontName='Helvetica', textColor=colors.HexColor(C['RED']), alignment=TA_CENTER)))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(
        f"Generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        s['footer']))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Informe Fiscal (IVA + IRPF + IS)
# ---------------------------------------------------------------------------

def generate_fiscal_report_pdf(snap: dict, company_name: str, period: str) -> bytes:
    """
    Genera el informe fiscal PDF con secciones IVA, IRPF e IS.

    snap: dict con estructura FiscalSnapshot:
      snap["iva"], snap["irpf"], snap["impuesto_sociedades"], snap["resumen_ejecutivo"]
    """
    if not REPORTLAB_AVAILABLE:
        return f"Informe Fiscal {period}\n{snap.get('resumen_ejecutivo', '')}".encode("utf-8")

    C_INDIGO  = colors.HexColor('#6366f1')
    C_EMERALD = colors.HexColor('#10b981')
    C_RED     = colors.HexColor('#ef4444')
    C_AMBER   = colors.HexColor('#f59e0b')
    C_BLUE    = colors.HexColor('#3b82f6')
    C_SLATE   = colors.HexColor('#1e293b')
    C_GRAY    = colors.HexColor('#64748b')
    C_LIGHT   = colors.HexColor('#f8fafc')
    C_LINE    = colors.HexColor('#e2e8f0')
    C_FOOTER  = colors.HexColor('#94a3b8')

    iva = snap.get("iva", {})
    irpf = snap.get("irpf", {})
    is_ = snap.get("impuesto_sociedades", {})
    resumen = snap.get("resumen_ejecutivo", "")
    period_label = snap.get("period_label", period)

    fmt_eur = lambda v: f"{v:,.2f} \u20ac".replace(",", "X").replace(".", ",").replace("X", ".")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_company   = sty("FCo", fontSize=20, fontName="Helvetica-Bold", textColor=C_SLATE)
    s_badge     = sty("FBa", fontSize=9,  fontName="Helvetica-Bold", textColor=C_RED)
    s_period    = sty("FPe", fontSize=13, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_generated = sty("FGe", fontSize=7,  fontName="Helvetica", textColor=C_FOOTER, alignment=TA_RIGHT)
    s_section   = sty("FSe", fontSize=10, fontName="Helvetica-Bold", textColor=C_GRAY, spaceBefore=6, spaceAfter=4)
    s_resumen   = sty("FRe", fontSize=9,  fontName="Helvetica", textColor=colors.HexColor("#334155"), leading=13, spaceBefore=4)
    s_kpi_lbl   = sty("FKl", fontSize=7,  fontName="Helvetica", textColor=C_GRAY, alignment=TA_CENTER)
    s_footer    = sty("FFo", fontSize=7,  fontName="Helvetica", textColor=C_FOOTER, alignment=TA_CENTER)
    s_row_lbl   = sty("FRl", fontSize=8,  fontName="Helvetica", textColor=C_GRAY)
    s_row_val   = sty("FRv", fontSize=8,  fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_row_val_em  = sty("FRve", fontSize=8, fontName="Helvetica-Bold", textColor=C_INDIGO, alignment=TA_RIGHT)
    s_row_val_red = sty("FRvr", fontSize=8, fontName="Helvetica-Bold", textColor=C_RED, alignment=TA_RIGHT)

    elements = []

    # ── CABECERA ──
    header_data = [[
        [Paragraph(company_name, s_company), Spacer(1, 5), Paragraph("INFORME FISCAL", s_badge)],
        [Paragraph(period_label, s_period), Spacer(1, 5),
         Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", s_generated)],
    ]]
    header_table = Table(header_data, colWidths=[110*mm, 65*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 7*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_RED))
    elements.append(Spacer(1, 6*mm))

    # ── RESUMEN EJECUTIVO ──
    elements.append(Paragraph("RESUMEN EJECUTIVO", s_section))
    resumen_box = Table([[Paragraph(resumen, s_resumen)]], colWidths=[175*mm])
    resumen_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#fef2f2")),
        ("LINEABOVE",  (0,0), (-1,0), 2, C_RED),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ]))
    elements.append(resumen_box)
    elements.append(Spacer(1, 6*mm))

    # ── KPIs ──
    resultado_iva = float(iva.get("resultado_iva", 0))
    total_irpf = float(irpf.get("total_retenciones", 0))
    cuota_is = float(is_.get("cuota_estimada", 0))
    saldo_fiscal = resultado_iva + total_irpf + cuota_is
    iva_color = C_RED if resultado_iva > 0 else C_EMERALD

    kpi_data = [[
        [Paragraph(fmt_eur(resultado_iva), sty("fkv1", fontSize=14, fontName="Helvetica-Bold", textColor=iva_color, alignment=TA_CENTER)),
         Paragraph("Resultado IVA", s_kpi_lbl)],
        [Paragraph(fmt_eur(total_irpf), sty("fkv2", fontSize=14, fontName="Helvetica-Bold", textColor=C_AMBER, alignment=TA_CENTER)),
         Paragraph("IRPF Retenciones", s_kpi_lbl)],
        [Paragraph(fmt_eur(cuota_is), sty("fkv3", fontSize=14, fontName="Helvetica-Bold", textColor=C_BLUE, alignment=TA_CENTER)),
         Paragraph("IS Estimado", s_kpi_lbl)],
        [Paragraph(fmt_eur(saldo_fiscal), sty("fkv4", fontSize=14, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_CENTER)),
         Paragraph("Total obligaciones", s_kpi_lbl)],
    ]]
    kpi_table = Table(kpi_data, colWidths=[44*mm]*4)
    kpi_table.setStyle(TableStyle([
        ("BOX", (0,0),(0,0), 0.5, iva_color),
        ("BOX", (1,0),(1,0), 0.5, C_AMBER),
        ("BOX", (2,0),(2,0), 0.5, C_BLUE),
        ("BOX", (3,0),(3,0), 0.5, C_SLATE),
        ("BACKGROUND", (0,0),(0,0), colors.HexColor("#fef2f2") if resultado_iva > 0 else colors.HexColor("#f0fdf4")),
        ("BACKGROUND", (1,0),(1,0), colors.HexColor("#fffbeb")),
        ("BACKGROUND", (2,0),(2,0), colors.HexColor("#eff6ff")),
        ("BACKGROUND", (3,0),(3,0), C_LIGHT),
        ("TOPPADDING", (0,0),(-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("VALIGN", (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 6*mm))

    # ── SECCIÓN 1: IVA ──
    elements.append(Paragraph("1. IMPUESTO SOBRE EL VALOR AÑADIDO (IVA)", s_section))

    rep_21 = float(iva.get("repercutido_21", 0))
    rep_10 = float(iva.get("repercutido_10", 0))
    rep_4  = float(iva.get("repercutido_4", 0))
    sop_21 = float(iva.get("soportado_21", 0))
    sop_10 = float(iva.get("soportado_10", 0))
    sop_4  = float(iva.get("soportado_4", 0))
    total_rep = float(iva.get("total_repercutido", 0))
    total_sop = float(iva.get("total_soportado", 0))

    iva_detail = [
        [Paragraph("Tipo", s_row_lbl), Paragraph("Repercutido", s_row_val),
         Paragraph("Soportado", s_row_val), Paragraph("Diferencia", s_row_val)],
        [Paragraph("General (21%)", s_row_lbl), Paragraph(fmt_eur(rep_21), s_row_val),
         Paragraph(fmt_eur(sop_21), s_row_val), Paragraph(fmt_eur(rep_21 - sop_21), s_row_val)],
        [Paragraph("Reducido (10%)", s_row_lbl), Paragraph(fmt_eur(rep_10), s_row_val),
         Paragraph(fmt_eur(sop_10), s_row_val), Paragraph(fmt_eur(rep_10 - sop_10), s_row_val)],
        [Paragraph("Superreducido (4%)", s_row_lbl), Paragraph(fmt_eur(rep_4), s_row_val),
         Paragraph(fmt_eur(sop_4), s_row_val), Paragraph(fmt_eur(rep_4 - sop_4), s_row_val)],
        [Paragraph("TOTAL", sty("FTot", fontSize=8, fontName="Helvetica-Bold", textColor=C_SLATE)),
         Paragraph(fmt_eur(total_rep), s_row_val_em), Paragraph(fmt_eur(total_sop), s_row_val_red),
         Paragraph(fmt_eur(resultado_iva), sty("FResV", fontSize=8, fontName="Helvetica-Bold",
                   textColor=C_RED if resultado_iva > 0 else C_EMERALD, alignment=TA_RIGHT))],
    ]
    iva_tbl = Table(iva_detail, colWidths=[45*mm, 38*mm, 38*mm, 38*mm])
    iva_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0),(-1,-1), 8),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW", (0,0),(-1,0), 0.5, C_LINE),
        ("LINEBELOW", (0,-2),(-1,-2), 0.3, colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0,0),(-1,0), C_LIGHT),
        ("BACKGROUND", (0,-1),(-1,-1), colors.HexColor("#fef2f2") if resultado_iva > 0 else colors.HexColor("#f0fdf4")),
        ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"),
    ]))
    elements.append(iva_tbl)

    if total_rep > 0 or total_sop > 0:
        d = Drawing(160*mm, 50*mm)
        chart = VerticalBarChart()
        chart.x = 35
        chart.y = 15
        chart.width = 150*mm - 50
        chart.height = 50*mm - 25
        chart.data = [[total_rep, total_sop, abs(resultado_iva)]]
        chart.categoryAxis.categoryNames = ["Repercutido", "Soportado", "Resultado"]
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fillColor = C_GRAY
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.labels.fillColor = C_GRAY
        chart.valueAxis.visibleGrid = True
        chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
        chart.valueAxis.gridStrokeWidth = 0.5
        chart.valueAxis.forceZero = True
        chart.bars[0].fillColor = C_INDIGO
        chart.bars[(0, 0)].fillColor = C_EMERALD
        chart.bars[(0, 1)].fillColor = C_RED
        chart.bars[(0, 2)].fillColor = C_AMBER
        d.add(chart)
        elements.append(Spacer(1, 3*mm))
        elements.append(d)

    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))

    # ── SECCIÓN 2: IRPF ──
    elements.append(Paragraph("2. RETENCIONES IRPF", s_section))
    irpf_nominas = float(irpf.get("retenciones_nominas", 0))
    irpf_facturas = float(irpf.get("retenciones_facturas", 0))

    irpf_detail = [
        [Paragraph("Concepto", s_row_lbl), Paragraph("Importe", s_row_val)],
        [Paragraph("Retenciones en nominas", s_row_lbl), Paragraph(fmt_eur(irpf_nominas), s_row_val)],
        [Paragraph("Retenciones en facturas profesionales", s_row_lbl), Paragraph(fmt_eur(irpf_facturas), s_row_val)],
        [Paragraph("TOTAL RETENCIONES", sty("FIrpfT", fontSize=8, fontName="Helvetica-Bold", textColor=C_SLATE)),
         Paragraph(fmt_eur(total_irpf), s_row_val_em)],
    ]
    irpf_tbl = Table(irpf_detail, colWidths=[120*mm, 45*mm])
    irpf_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0),(-1,-1), 8),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW", (0,0),(-1,0), 0.5, C_LINE),
        ("LINEBELOW", (0,-2),(-1,-2), 0.3, colors.HexColor("#f1f5f9")),
        ("BACKGROUND", (0,0),(-1,0), C_LIGHT),
        ("BACKGROUND", (0,-1),(-1,-1), colors.HexColor("#fffbeb")),
        ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"),
    ]))
    elements.append(irpf_tbl)

    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))

    # ── SECCIÓN 3: IMPUESTO DE SOCIEDADES ──
    elements.append(Paragraph("3. IMPUESTO DE SOCIEDADES (ESTIMACION)", s_section))
    ingresos_b = float(is_.get("ingresos_brutos", 0))
    gastos_d = float(is_.get("gastos_deducibles", 0))
    base_imp = float(is_.get("base_imponible", 0))
    tipo_is = float(is_.get("tipo_estimado", 25))

    is_detail = [
        [Paragraph("Concepto", s_row_lbl), Paragraph("Importe", s_row_val)],
        [Paragraph("Ingresos brutos (base imponible ventas)", s_row_lbl), Paragraph(fmt_eur(ingresos_b), s_row_val)],
        [Paragraph("Gastos deducibles (compras + nominas)", s_row_lbl), Paragraph(fmt_eur(gastos_d), s_row_val_red)],
        [Paragraph("Base imponible", sty("FIsBI", fontSize=8, fontName="Helvetica-Bold", textColor=C_SLATE)),
         Paragraph(fmt_eur(base_imp), s_row_val_em)],
        [Paragraph(f"Tipo impositivo ({tipo_is:.0f}%)", s_row_lbl), Paragraph(f"{tipo_is:.0f}%", s_row_val)],
        [Paragraph("CUOTA ESTIMADA IS", sty("FIsQ", fontSize=9, fontName="Helvetica-Bold", textColor=C_SLATE)),
         Paragraph(fmt_eur(cuota_is), sty("FIsQV", fontSize=9, fontName="Helvetica-Bold", textColor=C_BLUE, alignment=TA_RIGHT))],
    ]
    is_tbl = Table(is_detail, colWidths=[120*mm, 45*mm])
    is_tbl.setStyle(TableStyle([
        ("FONTSIZE", (0,0),(-1,-1), 8),
        ("TOPPADDING", (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING", (0,0),(-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
        ("LINEBELOW", (0,0),(-1,0), 0.5, C_LINE),
        ("LINEBELOW", (0,2),(-1,2), 0.3, colors.HexColor("#f1f5f9")),
        ("LINEBELOW", (0,-2),(-1,-2), 0.5, C_LINE),
        ("BACKGROUND", (0,0),(-1,0), C_LIGHT),
        ("BACKGROUND", (0,-1),(-1,-1), colors.HexColor("#eff6ff")),
        ("FONTNAME", (0,0),(-1,0), "Helvetica-Bold"),
    ]))
    elements.append(is_tbl)

    elements.append(Spacer(1, 8*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Este informe es una estimacion orientativa generada automaticamente. "
        "No sustituye el asesoramiento fiscal profesional ni las declaraciones oficiales ante la AEAT.",
        sty("FDisc", fontSize=7, fontName="Helvetica", textColor=C_RED, alignment=TA_CENTER)))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        f"Generado por AutomatizaPyme \u00b7 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        s_footer))

    doc.build(elements)
    return buffer.getvalue()
