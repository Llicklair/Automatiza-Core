"""
Generación de PDFs: informe de tesorería (cash flow) y morosidad.
"""

import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _fmt_eur,
    _format_date,
    _make_doc,
    _table_header_style,
)

if REPORTLAB_AVAILABLE:
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )


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
        return "INFORME DE TESORERÍA\n".encode("utf-8")

    s = _common_styles()
    C = s["C"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get("company", {})

    # ── CABECERA ──
    elements.append(Paragraph("Informe de Tesorería", s["title"]))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            f"{company.get('name', '—')}  ·  {_format_date(data.get('period_start', ''))} — {_format_date(data.get('period_end', ''))}",
            ParagraphStyle(
                "CFSubtitle",
                parent=s["styles"]["Normal"],
                fontSize=10,
                fontName="Helvetica",
                textColor=colors.HexColor(C["GRAY"]),
            ),
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C["BLUE"])))
    elements.append(Spacer(1, 5 * mm))

    # ── KPI CARDS ──
    initial = float(data.get("initial_balance", 0))
    collections = float(data.get("total_collections", 0))
    payments = float(data.get("total_payments", 0))
    final = float(data.get("final_balance", 0))

    def kpi_cell(val_str, lbl, color_hex):
        return [
            Paragraph(
                val_str,
                ParagraphStyle(
                    "cfkv",
                    parent=s["styles"]["Normal"],
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(color_hex),
                    alignment=TA_CENTER,
                ),
            ),
            Spacer(1, 2),
            Paragraph(lbl, s["kpi_lbl"]),
        ]

    kpi_data = [
        [
            kpi_cell(_fmt_eur(initial), "Saldo inicial", C["GRAY"]),
            kpi_cell(_fmt_eur(collections), "Cobros previstos", C["EMERALD"]),
            kpi_cell(_fmt_eur(payments), "Pagos previstos", C["RED"]),
            kpi_cell(_fmt_eur(final), "Saldo final", C["BLUE"] if final >= 0 else C["RED"]),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[43.75 * mm] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor(C["GRAY"])),
                ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor(C["EMERALD"])),
                ("BOX", (2, 0), (2, 0), 0.5, colors.HexColor(C["RED"])),
                ("BOX", (3, 0), (3, 0), 0.5, colors.HexColor(C["BLUE"])),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#f0fdf4")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#fef2f2")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#eff6ff")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 6 * mm))

    # ── TABLA TEMPORAL ──
    periods = data.get("periods", [])
    if periods:
        elements.append(Paragraph("PREVISIÓN POR PERÍODO", s["section"]))
        period_col_widths = [50 * mm, 35 * mm, 35 * mm, 40 * mm]
        period_data = [
            [
                Paragraph("Período", s["header"]),
                Paragraph("Cobros", s["header"]),
                Paragraph("Pagos", s["header"]),
                Paragraph("Saldo acumulado", s["header"]),
            ]
        ]
        for p in periods:
            coll = float(p.get("collections", 0))
            pay = float(p.get("payments", 0))
            bal = float(p.get("cumulative_balance", 0))
            bal_color = C["EMERALD"] if bal >= 0 else C["RED"]
            period_data.append(
                [
                    Paragraph(str(p.get("label", "")), s["body"]),
                    Paragraph(
                        f"{coll:.2f} €",
                        ParagraphStyle(
                            "cfGreen",
                            parent=s["styles"]["Normal"],
                            fontSize=9,
                            fontName="Helvetica",
                            textColor=colors.HexColor(C["EMERALD"]),
                            alignment=TA_RIGHT,
                        ),
                    ),
                    Paragraph(
                        f"{pay:.2f} €",
                        ParagraphStyle(
                            "cfRed",
                            parent=s["styles"]["Normal"],
                            fontSize=9,
                            fontName="Helvetica",
                            textColor=colors.HexColor(C["RED"]),
                            alignment=TA_RIGHT,
                        ),
                    ),
                    Paragraph(
                        f"{bal:.2f} €",
                        ParagraphStyle(
                            "cfBal",
                            parent=s["styles"]["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                            textColor=colors.HexColor(bal_color),
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            )

        period_table = Table(period_data, colWidths=period_col_widths)
        period_table.setStyle(
            TableStyle(
                _table_header_style()
                + [
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        elements.append(period_table)
        elements.append(Spacer(1, 6 * mm))

        # ── GRÁFICA DE BARRAS ──
        try:
            bar_labels = [str(p.get("label", "")) for p in periods]
            bar_coll = [float(p.get("collections", 0)) for p in periods]
            bar_pay = [float(p.get("payments", 0)) for p in periods]

            d = Drawing(175 * mm, 55 * mm)
            chart = VerticalBarChart()
            chart.x = 40
            chart.y = 20
            chart.width = 175 * mm - 55
            chart.height = 55 * mm - 30
            chart.data = [bar_coll, bar_pay]
            chart.categoryAxis.categoryNames = bar_labels
            chart.categoryAxis.labels.fontSize = 7
            chart.categoryAxis.labels.fontName = "Helvetica"
            chart.valueAxis.labels.fontSize = 7
            chart.valueAxis.labels.fontName = "Helvetica"
            chart.valueAxis.visibleGrid = True
            chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
            chart.valueAxis.forceZero = True
            chart.bars[0].fillColor = colors.HexColor(C["EMERALD"])
            chart.bars[1].fillColor = colors.HexColor(C["RED"])
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
                (colors.HexColor(C["EMERALD"]), "Cobros"),
                (colors.HexColor(C["RED"]), "Pagos"),
            ]
            d.add(chart)
            d.add(legend)
            elements.append(d)
            elements.append(Spacer(1, 6 * mm))
        except Exception:
            _logger.warning("Failed to generate cash flow chart in PDF report", exc_info=True)

    # ── FACTURAS PENDIENTES DE COBRO (TOP 10) ──
    receivables = data.get("pending_receivables", [])
    if receivables:
        elements.append(Paragraph("FACTURAS PENDIENTES DE COBRO (TOP 10)", s["section"]))
        recv_data = [
            [
                Paragraph("Cliente", s["header"]),
                Paragraph("Nº Factura", s["header"]),
                Paragraph("Vencimiento", s["header"]),
                Paragraph("Importe", s["header"]),
            ]
        ]
        for r in receivables[:10]:
            recv_data.append(
                [
                    Paragraph(str(r.get("client_name", "—")), s["body"]),
                    Paragraph(str(r.get("invoice_number", "—")), s["body"]),
                    Paragraph(_format_date(str(r.get("due_date", ""))), s["body"]),
                    Paragraph(f"{float(r.get('amount', 0)):.2f} €", s["right"]),
                ]
            )
        recv_table = Table(recv_data, colWidths=[55 * mm, 35 * mm, 35 * mm, 35 * mm])
        recv_table.setStyle(
            TableStyle(
                _table_header_style()
                + [
                    ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
                ]
            )
        )
        elements.append(recv_table)

    # ── PIE ──
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])))
    elements.append(Spacer(1, 3 * mm))
    elements.append(
        Paragraph(
            f"Informe de tesorería generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            s["footer"],
        )
    )

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
        return "INFORME DE MOROSIDAD\n".encode("utf-8")

    s = _common_styles()
    C = s["C"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get("company", {})

    # ── CABECERA ──
    elements.append(Paragraph("Informe de Morosidad", s["title"]))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            f"{company.get('name', '—')}  ·  Fecha de corte: {_format_date(data.get('cutoff_date', ''))}",
            ParagraphStyle(
                "DelSubtitle",
                parent=s["styles"]["Normal"],
                fontSize=10,
                fontName="Helvetica",
                textColor=colors.HexColor(C["GRAY"]),
            ),
        )
    )
    elements.append(Spacer(1, 4 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C["RED"])))
    elements.append(Spacer(1, 5 * mm))

    # ── KPI CARDS ──
    total_overdue = float(data.get("total_overdue", 0))
    num_overdue = int(data.get("num_overdue", 0))
    avg_days = float(data.get("avg_days_overdue", 0))
    worst = data.get("worst_client", "—")

    def kpi_cell(val_str, lbl, color_hex):
        return [
            Paragraph(
                val_str,
                ParagraphStyle(
                    "delkv",
                    parent=s["styles"]["Normal"],
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(color_hex),
                    alignment=TA_CENTER,
                ),
            ),
            Spacer(1, 2),
            Paragraph(lbl, s["kpi_lbl"]),
        ]

    kpi_data = [
        [
            kpi_cell(_fmt_eur(total_overdue), "Total moroso", C["RED"]),
            kpi_cell(str(num_overdue), "Facturas vencidas", C["AMBER"]),
            kpi_cell(f"{avg_days:.0f} días", "Media retraso", C["GRAY"]),
            kpi_cell(worst[:20], "Cliente + moroso", C["SLATE"]),
        ]
    ]
    kpi_table = Table(kpi_data, colWidths=[43.75 * mm] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (0, 0), 0.5, colors.HexColor(C["RED"])),
                ("BOX", (1, 0), (1, 0), 0.5, colors.HexColor(C["AMBER"])),
                ("BOX", (2, 0), (2, 0), 0.5, colors.HexColor(C["GRAY"])),
                ("BOX", (3, 0), (3, 0), 0.5, colors.HexColor(C["SLATE"])),
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#fef2f2")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#fffbeb")),
                ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#f8fafc")),
                ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#f8fafc")),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(kpi_table)
    elements.append(Spacer(1, 6 * mm))

    # ── TABLA DE ANTIGÜEDAD (AGING) ──
    elements.append(Paragraph("ANÁLISIS DE ANTIGÜEDAD", s["section"]))
    aging = data.get("aging_buckets", {})
    bucket_order = ["0-30", "31-60", "61-90", ">90"]
    bucket_colors = [C["AMBER"], "#f97316", C["RED"], "#991b1b"]

    aging_header = [
        Paragraph("Tramo", s["header"]),
        Paragraph("Nº facturas", s["header"]),
        Paragraph("Importe", s["header"]),
    ]
    aging_data = [aging_header]
    for bucket, bcolor in zip(bucket_order, bucket_colors):
        b = aging.get(bucket, {})
        aging_data.append(
            [
                Paragraph(
                    f"{bucket} días",
                    ParagraphStyle(
                        f"ag_{bucket}",
                        parent=s["styles"]["Normal"],
                        fontSize=9,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(bcolor),
                    ),
                ),
                Paragraph(str(int(b.get("count", 0))), s["right"]),
                Paragraph(f"{float(b.get('amount', 0)):.2f} €", s["right"]),
            ]
        )

    aging_table = Table(aging_data, colWidths=[50 * mm, 40 * mm, 50 * mm])
    aging_table.setStyle(
        TableStyle(
            _table_header_style()
            + [
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ]
        )
    )
    elements.append(aging_table)
    elements.append(Spacer(1, 6 * mm))

    # ── DETALLE DE FACTURAS VENCIDAS ──
    overdue = data.get("overdue_invoices", [])
    if overdue:
        elements.append(Paragraph("DETALLE DE FACTURAS VENCIDAS", s["section"]))
        det_col_widths = [40 * mm, 25 * mm, 25 * mm, 20 * mm, 25 * mm, 25 * mm]
        det_data = [
            [
                Paragraph("Cliente", s["header"]),
                Paragraph("Nº Factura", s["header"]),
                Paragraph("Vencimiento", s["header"]),
                Paragraph("Días", s["header"]),
                Paragraph("Importe", s["header"]),
                Paragraph("Estado", s["header"]),
            ]
        ]
        for inv in overdue:
            days = int(inv.get("days_overdue", 0))

            row = [
                Paragraph(str(inv.get("client_name", "—"))[:25], s["body"]),
                Paragraph(str(inv.get("invoice_number", "—")), s["body"]),
                Paragraph(_format_date(str(inv.get("due_date", ""))), s["body"]),
                Paragraph(
                    str(days),
                    ParagraphStyle(
                        "delDays",
                        parent=s["styles"]["Normal"],
                        fontSize=9,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(C["RED"] if days > 60 else C["AMBER"]),
                        alignment=TA_RIGHT,
                    ),
                ),
                Paragraph(f"{float(inv.get('amount', 0)):.2f} €", s["right"]),
                Paragraph(str(inv.get("collection_status", "—")), s["body"]),
            ]
            det_data.append(row)

        det_table = Table(det_data, colWidths=det_col_widths)
        style_cmds = _table_header_style() + [("ALIGN", (3, 0), (4, -1), "RIGHT")]
        for idx, inv in enumerate(overdue, start=1):
            days = int(inv.get("days_overdue", 0))
            if days > 90:
                style_cmds.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#fef2f2")))
            elif days > 60:
                style_cmds.append(("BACKGROUND", (0, idx), (-1, idx), colors.HexColor("#fff7ed")))

        det_table.setStyle(TableStyle(style_cmds))
        elements.append(det_table)

    # ── PIE ──
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])))
    elements.append(Spacer(1, 3 * mm))
    elements.append(
        Paragraph(
            "Datos a fecha de generación. Revisar acciones de cobro pendientes.",
            ParagraphStyle(
                "DelNote",
                parent=s["styles"]["Normal"],
                fontSize=8,
                fontName="Helvetica",
                textColor=colors.HexColor(C["RED"]),
                alignment=TA_CENTER,
            ),
        )
    )
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            f"Generado por AutomatizaPyme · {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            s["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()
