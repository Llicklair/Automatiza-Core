"""
Generación de PDFs de facturación: factura estándar, rectificativa y con retención.
"""

import io

from app.services.pdf._invoice_sections import (
    _generate_simple_text_pdf,
    _invoice_lines_table,
    _simple_header,
    _themed_header,
    _verifactu_qr_block,
)
from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _client_block,
    _common_styles,
    _format_date,
    _invoice_footer,
    _make_doc,
    _table_header_style,
    build_theme,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )


# ---------------------------------------------------------------------------
# Factura estándar
# ---------------------------------------------------------------------------


def generate_invoice_pdf(invoice_data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera un PDF de factura a partir de los datos del invoice.
    theme_config: dict con accent_color, font_family, layout_style, header_style, table_style, logo_position, footer_text
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_text_pdf(invoice_data)

    th = build_theme(theme_config)
    acc = th["accent_color"]
    font = th["_font"]
    bold = th["_font_bold"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=8 * mm if th["header_style"] != "color_band" else 0,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    title_sty = ParagraphStyle(
        "T_title",
        parent=styles["Normal"],
        fontSize=20,
        fontName=bold,
        textColor=colors.HexColor("#1e293b"),
    )
    header_sty = ParagraphStyle(
        "T_header",
        parent=styles["Normal"],
        fontSize=9,
        fontName=bold,
        textColor=colors.HexColor("#64748b"),
    )
    body_sty = ParagraphStyle(
        "T_body",
        parent=styles["Normal"],
        fontSize=9,
        fontName=font,
        textColor=colors.HexColor("#1e293b"),
    )
    right_sty = ParagraphStyle(
        "T_right",
        parent=styles["Normal"],
        fontSize=9,
        fontName=font,
        textColor=colors.HexColor("#1e293b"),
        alignment=TA_RIGHT,
    )
    total_sty = ParagraphStyle(
        "T_total",
        parent=styles["Normal"],
        fontSize=14,
        fontName=bold,
        textColor=colors.HexColor(acc),
        alignment=TA_RIGHT,
    )

    elements = []
    company = invoice_data.get("company", {})
    client = invoice_data.get("client", {})

    # ── CABECERA según header_style ──
    elements.extend(_themed_header(invoice_data, company, th, styles, title_sty, body_sty, right_sty, bold, font, acc))

    # ── CLIENTE ──
    elements.extend(_client_block(client, header_sty, body_sty, bold_font=bold))
    elements.append(Spacer(1, 1 * mm))

    # ── LÍNEAS ──
    invoice_lines = invoice_data.get("lines", [])
    elements.append(_invoice_lines_table(invoice_lines, header_sty, body_sty, right_sty, th))
    elements.append(Spacer(1, 6 * mm))

    # ── TOTALES ──
    base = float(invoice_data.get("amount_base", 0))
    tax = float(invoice_data.get("tax_amount", 0))
    total = float(invoice_data.get("amount_total", 0))

    total_bg = colors.HexColor(acc + "22") if len(acc) == 7 else colors.HexColor("#eef2ff")
    totals_data = [
        [Paragraph("Base imponible:", right_sty), Paragraph(f"{base:.2f} €", right_sty)],
        [Paragraph("IVA:", right_sty), Paragraph(f"{tax:.2f} €", right_sty)],
        [
            Paragraph(
                "TOTAL:",
                ParagraphStyle(
                    "T_tlbl",
                    parent=styles["Normal"],
                    fontSize=12,
                    fontName=bold,
                    textColor=colors.HexColor(acc),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(f"{total:.2f} €", total_sty),
        ],
    ]
    totals_table = Table(totals_data, colWidths=[130 * mm, 40 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 2), (-1, 2), total_bg),
            ]
        )
    )
    elements.append(totals_table)

    # ── NOTAS Y PAGO ──
    payment_terms = invoice_data.get("payment_terms") or ""
    notes = invoice_data.get("notes") or ""
    if payment_terms or notes:
        elements.append(Spacer(1, 8 * mm))
        if payment_terms:
            elements.append(Paragraph("FORMA DE PAGO", header_sty))
            elements.append(Spacer(1, 1.5 * mm))
            elements.append(Paragraph(str(payment_terms), body_sty))
            elements.append(Spacer(1, 4 * mm))
        if notes:
            elements.append(Paragraph("NOTAS", header_sty))
            elements.append(Spacer(1, 1.5 * mm))
            elements.append(Paragraph(str(notes), body_sty))

    # ── QR VERIFACTU (si disponible) ──
    elements.extend(_verifactu_qr_block(invoice_data.get("verifactu")))

    # ── PIE ──
    footer_text = (
        th.get("footer_text") or "Documento generado automáticamente por AutomatizaCore · Gracias por su confianza."
    )
    elements.extend(_invoice_footer(footer_text, font=font))

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Factura rectificativa
# ---------------------------------------------------------------------------


def generate_rectificative_invoice_pdf(data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera PDF de factura rectificativa (Art. 15 RD 1619/2012).
    """
    if not REPORTLAB_AVAILABLE:
        return f"FACTURA RECTIFICATIVA {data.get('number', '')}\n".encode()

    s = _common_styles()
    C = s["C"]
    _accent = (theme_config or {}).get("accent_color") or C["RED"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer, topMargin=8 * mm)
    elements = []

    company = data.get("company", {})
    client = data.get("client", {})
    original = data.get("original_invoice", {})

    # ── CABECERA ──
    elements.extend(_simple_header(company, data, s, _accent, doc_title="FACTURA RECTIFICATIVA"))

    # ── CLIENTE ──
    elements.extend(_client_block(client, s["header"], s["body"]))

    # ── FACTURA ORIGINAL ──
    elements.append(Paragraph("FACTURA ORIGINAL RECTIFICADA", s["section"]))
    orig_data = [
        [
            Paragraph("Nº Factura:", s["header"]),
            Paragraph(str(original.get("number", "—")), s["body"]),
            Paragraph("Fecha:", s["header"]),
            Paragraph(_format_date(original.get("date", "")), s["body"]),
        ],
        [
            Paragraph("Base:", s["header"]),
            Paragraph(f"{float(original.get('amount_base', 0)):.2f} €", s["body"]),
            Paragraph("IVA:", s["header"]),
            Paragraph(f"{float(original.get('tax_amount', 0)):.2f} €", s["body"]),
        ],
        [
            Paragraph("Total original:", s["header"]),
            Paragraph(
                f"{float(original.get('amount_total', 0)):.2f} €",
                ParagraphStyle(
                    "OrigTotal",
                    parent=s["styles"]["Normal"],
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["SLATE"]),
                ),
            ),
            Paragraph("", s["body"]),
            Paragraph("", s["body"]),
        ],
    ]
    orig_table = Table(orig_data, colWidths=[25 * mm, 60 * mm, 15 * mm, 60 * mm])
    orig_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fef2f2")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(C["RED"])),
            ]
        )
    )
    elements.append(orig_table)
    elements.append(Spacer(1, 4 * mm))

    # ── MOTIVO ──
    reason = data.get("reason", "—")
    elements.append(Paragraph("MOTIVO DE RECTIFICACIÓN", s["section"]))
    elements.append(Paragraph(str(reason), s["body"]))
    elements.append(Spacer(1, 5 * mm))

    # ── LÍNEAS CORREGIDAS ──
    corrected_lines = data.get("corrected_lines", [])
    if corrected_lines:
        elements.append(Paragraph("DETALLE DE CORRECCIONES", s["section"]))
        col_widths = [80 * mm, 35 * mm, 35 * mm]
        table_data = [
            [
                Paragraph("Descripción", s["header"]),
                Paragraph("Importe original", s["header"]),
                Paragraph("Importe corregido", s["header"]),
            ]
        ]
        for ln in corrected_lines:
            table_data.append(
                [
                    Paragraph(str(ln.get("description", "")), s["body"]),
                    Paragraph(f"{float(ln.get('original_amount', 0)):.2f} €", s["right"]),
                    Paragraph(
                        f"{float(ln.get('corrected_amount', 0)):.2f} €",
                        ParagraphStyle(
                            "CorrAmt",
                            parent=s["styles"]["Normal"],
                            fontSize=9,
                            fontName="Helvetica-Bold",
                            textColor=colors.HexColor(C["RED"]),
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            )
        lines_table = Table(table_data, colWidths=col_widths)
        lines_table.setStyle(TableStyle(_table_header_style() + [("ALIGN", (1, 0), (-1, -1), "RIGHT")]))
        elements.append(lines_table)
        elements.append(Spacer(1, 5 * mm))

    # ── TOTALES CORREGIDOS ──
    corrected_base = float(data.get("corrected_base", 0))
    corrected_tax = float(data.get("corrected_tax", 0))
    corrected_total = float(data.get("corrected_total", 0))

    totals_data = [
        [
            Paragraph("Base corregida:", s["right"]),
            Paragraph(f"{corrected_base:.2f} €", s["right"]),
        ],
        [Paragraph("IVA corregido:", s["right"]), Paragraph(f"{corrected_tax:.2f} €", s["right"])],
        [
            Paragraph(
                "TOTAL CORREGIDO:",
                ParagraphStyle(
                    "RectTotalLabel",
                    parent=s["styles"]["Normal"],
                    fontSize=12,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["RED"]),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(
                f"{corrected_total:.2f} €",
                ParagraphStyle(
                    "RectTotalVal",
                    parent=s["styles"]["Normal"],
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["RED"]),
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    totals_table = Table(totals_data, colWidths=[130 * mm, 40 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor(C["RED"])),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fef2f2")),
            ]
        )
    )
    elements.append(totals_table)

    # ── PIE LEGAL ──
    elements.extend(
        _invoice_footer(
            "Factura rectificativa emitida conforme al Art. 15 del RD 1619/2012. "
            "Este documento modifica y sustituye parcialmente la factura original indicada.",
            footer_color=C["RED"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# Factura con retención
# ---------------------------------------------------------------------------


def generate_retention_invoice_pdf(data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera PDF de factura con retención de IRPF.
    """
    if not REPORTLAB_AVAILABLE:
        return f"FACTURA CON RETENCIÓN {data.get('number', '')}\n".encode()

    s = _common_styles()
    C = s["C"]
    _accent = (theme_config or {}).get("accent_color") or C["INDIGO"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer, topMargin=8 * mm)
    elements = []

    company = data.get("company", {})
    client = data.get("client", {})

    # ── CABECERA ──
    elements.extend(_simple_header(company, data, s, _accent))

    # ── CLIENTE ──
    elements.extend(_client_block(client, s["header"], s["body"]))

    # ── LÍNEAS ──
    lines = data.get("lines", [])
    elements.append(_invoice_lines_table(lines, s["header"], s["body"], s["right"], theme=None))
    elements.append(Spacer(1, 6 * mm))

    # ── TOTALES CON RETENCIÓN ──
    base = float(data.get("amount_base", 0))
    tax = float(data.get("tax_amount", 0))
    ret_rate = float(data.get("retention_rate", 15))
    ret_amount = float(data.get("retention_amount", 0))
    total = float(data.get("amount_total", 0))

    totals_data = [
        [Paragraph("Base imponible:", s["right"]), Paragraph(f"{base:.2f} €", s["right"])],
        [Paragraph("IVA:", s["right"]), Paragraph(f"{tax:.2f} €", s["right"])],
        [
            Paragraph(f"Retención IRPF ({ret_rate:.0f}%):", s["right"]),
            Paragraph(
                f"-{ret_amount:.2f} €",
                ParagraphStyle(
                    "RetAmt",
                    parent=s["styles"]["Normal"],
                    fontSize=9,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["RED"]),
                    alignment=TA_RIGHT,
                ),
            ),
        ],
        [
            Paragraph(
                "TOTAL A PAGAR:",
                ParagraphStyle(
                    "RetTotalLabel",
                    parent=s["styles"]["Normal"],
                    fontSize=12,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["INDIGO"]),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(
                f"{total:.2f} €",
                ParagraphStyle(
                    "RetTotalVal",
                    parent=s["styles"]["Normal"],
                    fontSize=14,
                    fontName="Helvetica-Bold",
                    textColor=colors.HexColor(C["INDIGO"]),
                    alignment=TA_RIGHT,
                ),
            ),
        ],
    ]
    totals_table = Table(totals_data, colWidths=[130 * mm, 40 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LINEABOVE", (0, 3), (-1, 3), 1, colors.HexColor(C["LINE"])),
                ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#eef2ff")),
                ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#fef2f2")),
            ]
        )
    )
    elements.append(totals_table)

    # ── PIE ──
    elements.extend(_invoice_footer("Factura con retención de IRPF conforme a la normativa vigente."))

    doc.build(elements)
    return buffer.getvalue()
