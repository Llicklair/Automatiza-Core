"""
Helpers internos de construcción de secciones PDF para facturas.
No importar directamente — usar app.services.pdf (paquete).

I18N.PDF: cada helper acepta `locale` opcional (default `es`) y usa
`app.i18n.translate()` para los labels visibles. El callsite externo
(`generate_invoice_pdf`) pasa el locale resuelto desde
`services.i18n.tenant_locale.resolve_locale()`.
"""

from app.i18n import translate
from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _format_date,
    _table_header_style,
    table_style_commands,
)

if REPORTLAB_AVAILABLE:
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


def _invoice_lines_table(
    lines: list,
    header_sty,
    body_sty,
    right_sty,
    theme: dict,
    locale: str = "es",
) -> "Table":
    """Tabla de líneas de factura reutilizable.

    I18N.PDF: headers traducidos via `translate(key, locale)`.
    """
    col_widths = [80 * mm, 20 * mm, 22 * mm, 20 * mm, 26 * mm]
    table_data = [
        [
            Paragraph(translate("invoice.concept", locale), header_sty),
            Paragraph(translate("invoice.quantity", locale), header_sty),
            Paragraph(translate("invoice.unit_price", locale), header_sty),
            Paragraph(translate("invoice.tax_rate", locale), header_sty),
            Paragraph(translate("invoice.total", locale), right_sty),
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
        tbl.setStyle(TableStyle(table_style_commands(theme, len(lines)) + [("ALIGN", (-1, 0), (-1, -1), "RIGHT")]))
    else:
        tbl.setStyle(TableStyle(_table_header_style() + [("ALIGN", (-1, 0), (-1, -1), "RIGHT")]))
    return tbl


def _simple_header(company: dict, data: dict, s, accent: str, doc_title: str = "FACTURA") -> list:
    """Cabecera simple (line_only / rectificativa / retención) sin banda de color."""
    title_color = accent
    # Una proforma impone su propio título ("PROFORMA / BORRADOR") vía data y una
    # etiqueta de número no fiscal ("Ref." en vez de "Nº") para que no se lea como
    # una factura fiscal.
    doc_title = data.get("doc_title") or doc_title
    num_label = data.get("number_label", "Nº")
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
                Paragraph(f"{num_label} {data.get('number', '—')}", s["right"]),
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
    # "Ref." (no "Nº") para proformas: nunca una numeración de factura fiscal.
    num_label = invoice_data.get("number_label", "Nº")
    elements = []

    if h_style == "color_band":
        band_sty = ParagraphStyle("T_band", parent=styles["Normal"], fontSize=18, fontName=bold, textColor=colors.white)
        band_sub = ParagraphStyle(
            "T_bandsub",
            parent=styles["Normal"],
            fontSize=8,
            fontName=font,
            textColor=colors.HexColor("#e0e7ff"),
        )
        band_right = ParagraphStyle(
            "T_bandr",
            parent=styles["Normal"],
            fontSize=20,
            fontName=bold,
            textColor=colors.white,
            alignment=TA_RIGHT,
        )
        band_rsub = ParagraphStyle(
            "T_bandrs",
            parent=styles["Normal"],
            fontSize=9,
            fontName=font,
            textColor=colors.HexColor("#e0e7ff"),
            alignment=TA_RIGHT,
        )

        logo_col = [
            Paragraph(company.get("name") or "Mi Empresa S.L.", band_sty),
            Spacer(1, 4),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')} · {company.get('address', '')}", band_sub),
            Paragraph(
                company.get("phone", "") + (" · " + company.get("email", "") if company.get("email") else ""),
                band_sub,
            ),
        ]
        inv_col = [
            Paragraph(invoice_data.get("doc_title", "FACTURA"), band_right),
            Spacer(1, 4),
            Paragraph(f"{num_label} {invoice_data.get('number', '—')}", band_rsub),
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
        dark_sty = ParagraphStyle("T_dark", parent=styles["Normal"], fontSize=18, fontName=bold, textColor=colors.white)
        dark_sub = ParagraphStyle(
            "T_darks",
            parent=styles["Normal"],
            fontSize=8,
            fontName=font,
            textColor=colors.HexColor("#94a3b8"),
        )
        dark_r = ParagraphStyle(
            "T_darkr",
            parent=styles["Normal"],
            fontSize=20,
            fontName=bold,
            textColor=colors.HexColor(acc),
            alignment=TA_RIGHT,
        )
        dark_rsub = ParagraphStyle(
            "T_darkrs",
            parent=styles["Normal"],
            fontSize=9,
            fontName=font,
            textColor=colors.HexColor("#94a3b8"),
            alignment=TA_RIGHT,
        )
        logo_col = [
            Paragraph(company.get("name") or "Mi Empresa S.L.", dark_sty),
            Spacer(1, 4),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')} · {company.get('address', '')}", dark_sub),
            Paragraph(company.get("phone", ""), dark_sub),
        ]
        inv_col = [
            Paragraph(invoice_data.get("doc_title", "FACTURA"), dark_r),
            Spacer(1, 4),
            Paragraph(f"{num_label} {invoice_data.get('number', '—')}", dark_rsub),
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
                    "T_ftitle",
                    parent=styles["Normal"],
                    fontSize=18,
                    fontName=bold,
                    textColor=colors.HexColor(acc),
                    alignment=TA_RIGHT,
                ),
            ),
            Spacer(1, 6),
            Paragraph(f"{num_label} {invoice_data.get('number', '—')}", right_sty),
            Paragraph(f"Fecha: {_format_date(invoice_data.get('date', ''))}", right_sty),
        ]
        if logo_pos == "right":
            cols = [inv_block, company_block]
            widths = [80 * mm, 100 * mm]
        elif logo_pos == "center":
            center_sty = ParagraphStyle(
                "T_ccenter",
                parent=styles["Normal"],
                fontSize=20,
                fontName=bold,
                textColor=colors.HexColor("#1e293b"),
                alignment=TA_CENTER,
            )
            center_sub = ParagraphStyle(
                "T_ccsub",
                parent=styles["Normal"],
                fontSize=9,
                fontName=font,
                textColor=colors.HexColor("#64748b"),
                alignment=TA_CENTER,
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
            line_color = colors.HexColor(acc) if th["layout_style"] == "minimal" else colors.HexColor("#e2e8f0")
            thickness = 1.5 if th["layout_style"] == "minimal" else 1
            elements.append(HRFlowable(width="100%", thickness=thickness, color=line_color))
        elements.append(Spacer(1, 5 * mm))

    return elements


def _draft_safety_marker(width_mm: float = 180.0) -> list:
    """Sello visible "SIN VALOR FISCAL" para proformas/borradores.

    Barrera anti-confusión: garantiza que una proforma no pueda hacerse pasar
    por una factura. Se inserta en la cabecera de todo documento no fiscal
    generado por el ERP.
    """
    if not REPORTLAB_AVAILABLE:
        return []
    marker_sty = ParagraphStyle(
        "DraftSafetyMarker",
        fontSize=11,
        fontName="Helvetica-Bold",
        textColor=colors.white,
        alignment=TA_CENTER,
    )
    banner = Table(
        [[Paragraph("SIN VALOR FISCAL — no es una factura", marker_sty)]],
        colWidths=[width_mm * mm],
    )
    banner.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#dc2626")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [banner, Spacer(1, 4 * mm)]
