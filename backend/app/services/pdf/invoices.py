"""
Generación de PDFs de facturación: factura estándar, rectificativa y con retención.
"""

import io
from datetime import datetime

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
    _client_block,
    _common_styles,
    _format_date,
    _invoice_footer,
    _make_doc,
    _table_header_style,
    build_theme,
    table_style_commands,
)

if REPORTLAB_AVAILABLE:
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


# ---------------------------------------------------------------------------
# Helpers internos de facturación
# ---------------------------------------------------------------------------


def _invoice_lines_table(lines: list, header_sty, body_sty, right_sty, theme: dict) -> Table:
    """Tabla de líneas de factura reutilizable."""
    col_widths = [80 * mm, 20 * mm, 22 * mm, 20 * mm, 26 * mm]
    table_data = [
        [
            Paragraph("Descripción", header_sty),
            Paragraph("Cant.", header_sty),
            Paragraph("Precio unit.", header_sty),
            Paragraph("IVA", header_sty),
            Paragraph("Total", right_sty),
        ]
    ]
    for ln in lines:
        table_data.append(
            [
                Paragraph(str(ln.get("description", "")), body_sty),
                Paragraph(str(ln.get("quantity", 1)), body_sty),
                Paragraph(f"{float(ln.get('unit_price', 0)):.2f} €", body_sty),
                Paragraph(f"{float(ln.get('tax_percentage', 21)):.0f}%", body_sty),
                Paragraph(f"{float(ln.get('total', 0)):.2f} €", right_sty),
            ]
        )
    tbl = Table(table_data, colWidths=col_widths)
    if theme:
        tbl.setStyle(
            TableStyle(
                table_style_commands(theme, len(lines)) + [("ALIGN", (-1, 0), (-1, -1), "RIGHT")]
            )
        )
    else:
        tbl.setStyle(
            TableStyle(
                _table_header_style() + [("ALIGN", (-1, 0), (-1, -1), "RIGHT")]
            )
        )
    return tbl


def _simple_header(company: dict, data: dict, s, accent: str, doc_title: str = "FACTURA") -> list:
    """Cabecera simple (line_only / rectificativa / retención) sin banda de color."""
    title_color = accent
    header_data = [
        [
            [
                Paragraph(company.get("name", "Mi Empresa S.L."), s["title"]),
                Spacer(1, 15),
                Paragraph(f"NIF: {company.get('nif', 'B00000000')}", s["body"]),
                Paragraph(company.get("address", ""), s["body"]),
                Paragraph(company.get("phone", ""), s["body"]),
            ],
            [
                Spacer(1, 4),
                Paragraph(
                    doc_title,
                    ParagraphStyle(
                        "SH_title",
                        parent=s["styles"]["Normal"],
                        fontSize=18,
                        fontName="Helvetica-Bold",
                        textColor=colors.HexColor(title_color),
                        alignment=TA_RIGHT,
                    ),
                ),
                Spacer(1, 6),
                Paragraph(f"Nº {data.get('number', 'F-0001')}", s["right"]),
                Paragraph(f"Fecha: {_format_date(data.get('date', ''))}", s["right"]),
            ],
        ]
    ]
    header_table = Table(header_data, colWidths=[100 * mm, 80 * mm])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    C = s["C"]
    return [
        header_table,
        Spacer(1, 5 * mm),
        HRFlowable(width="100%", thickness=1, color=colors.HexColor(C["LINE"])),
        Spacer(1, 5 * mm),
    ]


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
        "T_title", parent=styles["Normal"], fontSize=20, fontName=bold,
        textColor=colors.HexColor("#1e293b"),
    )
    header_sty = ParagraphStyle(
        "T_header", parent=styles["Normal"], fontSize=9, fontName=bold,
        textColor=colors.HexColor("#64748b"),
    )
    body_sty = ParagraphStyle(
        "T_body", parent=styles["Normal"], fontSize=9, fontName=font,
        textColor=colors.HexColor("#1e293b"),
    )
    right_sty = ParagraphStyle(
        "T_right", parent=styles["Normal"], fontSize=9, fontName=font,
        textColor=colors.HexColor("#1e293b"), alignment=TA_RIGHT,
    )
    total_sty = ParagraphStyle(
        "T_total", parent=styles["Normal"], fontSize=14, fontName=bold,
        textColor=colors.HexColor(acc), alignment=TA_RIGHT,
    )

    elements = []
    company = invoice_data.get("company", {})
    client = invoice_data.get("client", {})

    # ── CABECERA según header_style ──
    elements.extend(
        _themed_header(invoice_data, company, th, styles, title_sty, body_sty, right_sty, bold, font, acc)
    )

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
                    "T_tlbl", parent=styles["Normal"], fontSize=12, fontName=bold,
                    textColor=colors.HexColor(acc), alignment=TA_RIGHT,
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

    # ── PIE ──
    footer_text = (
        th.get("footer_text")
        or "Documento generado automáticamente por AutomatizaPyme · Gracias por su confianza."
    )
    elements.extend(_invoice_footer(footer_text, font=font))

    doc.build(elements)
    return buffer.getvalue()


def _generate_simple_text_pdf(invoice_data: dict) -> bytes:
    """Fallback minimalista si reportlab no está disponible."""
    content = f"""FACTURA {invoice_data.get("number", "")}
Fecha: {invoice_data.get("date", "")}
Cliente: {invoice_data.get("client", {}).get("name", "")}
Total: {invoice_data.get("amount_total", 0):.2f} EUR
"""
    return content.encode("utf-8")


def _themed_header(invoice_data, company, th, styles, title_sty, body_sty, right_sty, bold, font, acc):
    """Genera la cabecera según el header_style del theme (color_band, dark_band, line_only)."""
    h_style = th["header_style"]
    elements = []

    if h_style == "color_band":
        band_sty = ParagraphStyle(
            "T_band", parent=styles["Normal"], fontSize=18, fontName=bold, textColor=colors.white
        )
        band_sub = ParagraphStyle(
            "T_bandsub", parent=styles["Normal"], fontSize=8, fontName=font,
            textColor=colors.HexColor("#e0e7ff"),
        )
        band_right = ParagraphStyle(
            "T_bandr", parent=styles["Normal"], fontSize=20, fontName=bold,
            textColor=colors.white, alignment=TA_RIGHT,
        )
        band_rsub = ParagraphStyle(
            "T_bandrs", parent=styles["Normal"], fontSize=9, fontName=font,
            textColor=colors.HexColor("#e0e7ff"), alignment=TA_RIGHT,
        )

        logo_col = [
            Paragraph(company.get("name") or "Mi Empresa S.L.", band_sty),
            Spacer(1, 4),
            Paragraph(
                f"NIF: {company.get('nif', 'B00000000')} · {company.get('address', '')}", band_sub
            ),
            Paragraph(
                company.get("phone", "")
                + (" · " + company.get("email", "") if company.get("email") else ""),
                band_sub,
            ),
        ]
        inv_col = [
            Paragraph(invoice_data.get("doc_title", "FACTURA"), band_right),
            Spacer(1, 4),
            Paragraph(f"Nº {invoice_data.get('number', 'F-0001')}", band_rsub),
            Paragraph(f"Fecha: {_format_date(invoice_data.get('date', ''))}", band_rsub),
        ]
        band_table = Table([[logo_col, inv_col]], colWidths=[110 * mm, 70 * mm])
        band_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(acc)),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ]
            )
        )
        elements.append(band_table)
        elements.append(Spacer(1, 6 * mm))

    elif h_style == "dark_band":
        dark_sty = ParagraphStyle(
            "T_dark", parent=styles["Normal"], fontSize=18, fontName=bold, textColor=colors.white
        )
        dark_sub = ParagraphStyle(
            "T_darks", parent=styles["Normal"], fontSize=8, fontName=font,
            textColor=colors.HexColor("#94a3b8"),
        )
        dark_r = ParagraphStyle(
            "T_darkr", parent=styles["Normal"], fontSize=20, fontName=bold,
            textColor=colors.HexColor(acc), alignment=TA_RIGHT,
        )
        dark_rsub = ParagraphStyle(
            "T_darkrs", parent=styles["Normal"], fontSize=9, fontName=font,
            textColor=colors.HexColor("#94a3b8"), alignment=TA_RIGHT,
        )
        logo_col = [
            Paragraph(company.get("name") or "Mi Empresa S.L.", dark_sty),
            Spacer(1, 4),
            Paragraph(
                f"NIF: {company.get('nif', 'B00000000')} · {company.get('address', '')}", dark_sub
            ),
            Paragraph(company.get("phone", ""), dark_sub),
        ]
        inv_col = [
            Paragraph(invoice_data.get("doc_title", "FACTURA"), dark_r),
            Spacer(1, 4),
            Paragraph(f"Nº {invoice_data.get('number', 'F-0001')}", dark_rsub),
            Paragraph(f"Fecha: {_format_date(invoice_data.get('date', ''))}", dark_rsub),
        ]
        band_table = Table([[logo_col, inv_col]], colWidths=[110 * mm, 70 * mm])
        band_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 12),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                ]
            )
        )
        elements.append(band_table)
        elements.append(Spacer(1, 6 * mm))

    else:
        # line_only / none — layout clásico/minimal
        logo_pos = th["logo_position"]
        company_block = [
            Paragraph(company.get("name") or "Mi Empresa S.L.", title_sty),
            Spacer(1, 8),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')}", body_sty),
            Paragraph(company.get("address", ""), body_sty),
            Paragraph(company.get("phone", ""), body_sty),
        ]
        inv_block = [
            Spacer(1, 4),
            Paragraph(
                invoice_data.get("doc_title", "FACTURA"),
                ParagraphStyle(
                    "T_ftitle", parent=styles["Normal"], fontSize=18, fontName=bold,
                    textColor=colors.HexColor(acc), alignment=TA_RIGHT,
                ),
            ),
            Spacer(1, 6),
            Paragraph(f"Nº {invoice_data.get('number', 'F-0001')}", right_sty),
            Paragraph(f"Fecha: {_format_date(invoice_data.get('date', ''))}", right_sty),
        ]
        if logo_pos == "right":
            cols = [inv_block, company_block]
            widths = [80 * mm, 100 * mm]
        elif logo_pos == "center":
            center_sty = ParagraphStyle(
                "T_ccenter", parent=styles["Normal"], fontSize=20, fontName=bold,
                textColor=colors.HexColor("#1e293b"), alignment=TA_CENTER,
            )
            center_sub = ParagraphStyle(
                "T_ccsub", parent=styles["Normal"], fontSize=9, fontName=font,
                textColor=colors.HexColor("#64748b"), alignment=TA_CENTER,
            )
            center_block = [
                Paragraph(company.get("name") or "Mi Empresa S.L.", center_sty),
                Spacer(1, 4),
                Paragraph(f"NIF: {company.get('nif', 'B00000000')}", center_sub),
                Paragraph(company.get("address", ""), center_sub),
            ]
            cols = [center_block, inv_block]
            widths = [100 * mm, 80 * mm]
        else:
            cols = [company_block, inv_block]
            widths = [100 * mm, 80 * mm]

        ht = Table([cols], colWidths=widths)
        ht.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        elements.append(ht)
        elements.append(Spacer(1, 5 * mm))
        if h_style == "line_only":
            line_color = (
                colors.HexColor(acc)
                if th["layout_style"] == "minimal"
                else colors.HexColor("#e2e8f0")
            )
            thickness = 1.5 if th["layout_style"] == "minimal" else 1
            elements.append(HRFlowable(width="100%", thickness=thickness, color=line_color))
        elements.append(Spacer(1, 5 * mm))

    return elements


# ---------------------------------------------------------------------------
# Factura rectificativa
# ---------------------------------------------------------------------------


def generate_rectificative_invoice_pdf(data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera PDF de factura rectificativa (Art. 15 RD 1619/2012).
    """
    if not REPORTLAB_AVAILABLE:
        return f"FACTURA RECTIFICATIVA {data.get('number', '')}\n".encode("utf-8")

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
                    "OrigTotal", parent=s["styles"]["Normal"], fontSize=10,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["SLATE"]),
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
                            "CorrAmt", parent=s["styles"]["Normal"], fontSize=9,
                            fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                            alignment=TA_RIGHT,
                        ),
                    ),
                ]
            )
        lines_table = Table(table_data, colWidths=col_widths)
        lines_table.setStyle(
            TableStyle(_table_header_style() + [("ALIGN", (1, 0), (-1, -1), "RIGHT")])
        )
        elements.append(lines_table)
        elements.append(Spacer(1, 5 * mm))

    # ── TOTALES CORREGIDOS ──
    corrected_base = float(data.get("corrected_base", 0))
    corrected_tax = float(data.get("corrected_tax", 0))
    corrected_total = float(data.get("corrected_total", 0))

    totals_data = [
        [Paragraph("Base corregida:", s["right"]), Paragraph(f"{corrected_base:.2f} €", s["right"])],
        [Paragraph("IVA corregido:", s["right"]), Paragraph(f"{corrected_tax:.2f} €", s["right"])],
        [
            Paragraph(
                "TOTAL CORREGIDO:",
                ParagraphStyle(
                    "RectTotalLabel", parent=s["styles"]["Normal"], fontSize=12,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(
                f"{corrected_total:.2f} €",
                ParagraphStyle(
                    "RectTotalVal", parent=s["styles"]["Normal"], fontSize=14,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
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
        return f"FACTURA CON RETENCIÓN {data.get('number', '')}\n".encode("utf-8")

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
                    "RetAmt", parent=s["styles"]["Normal"], fontSize=9,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["RED"]),
                    alignment=TA_RIGHT,
                ),
            ),
        ],
        [
            Paragraph(
                "TOTAL A PAGAR:",
                ParagraphStyle(
                    "RetTotalLabel", parent=s["styles"]["Normal"], fontSize=12,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["INDIGO"]),
                    alignment=TA_RIGHT,
                ),
            ),
            Paragraph(
                f"{total:.2f} €",
                ParagraphStyle(
                    "RetTotalVal", parent=s["styles"]["Normal"], fontSize=14,
                    fontName="Helvetica-Bold", textColor=colors.HexColor(C["INDIGO"]),
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
    elements.extend(
        _invoice_footer("Factura con retención de IRPF conforme a la normativa vigente.")
    )

    doc.build(elements)
    return buffer.getvalue()
