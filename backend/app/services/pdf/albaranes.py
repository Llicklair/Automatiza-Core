"""
PDF generation for albaranes (delivery notes).
Uses the same _pdf_base infrastructure as pdf_invoices.py.
"""

import io

from app.services.documents._pdf_base import (
    REPORTLAB_AVAILABLE,
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


def generate_albaran_pdf(albaran_data: dict, theme_config: dict | None = None) -> bytes:
    """
    Generate a delivery note PDF.

    albaran_data keys: albaran_number, date, status, client_name, client_nif,
                       issuer_name, issuer_nif, issuer_address, notes, lines,
                       amount_base, tax_amount, amount_total
    lines items: description, quantity, unit_price, tax_percentage, total
    """
    if not REPORTLAB_AVAILABLE:
        content = (
            f"ALBARÁN {albaran_data.get('albaran_number', '')}\n"
            f"Fecha: {albaran_data.get('date', '')}\n"
            f"Cliente: {albaran_data.get('client_name', '')}\n"
            f"Total: {albaran_data.get('amount_total', 0):.2f} EUR\n"
        )
        return content.encode("utf-8")

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
        topMargin=8 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    title_sty = ParagraphStyle(
        "A_title",
        parent=styles["Normal"],
        fontSize=20,
        fontName=bold,
        textColor=colors.HexColor("#1e293b"),
    )
    header_sty = ParagraphStyle(
        "A_header",
        parent=styles["Normal"],
        fontSize=9,
        fontName=bold,
        textColor=colors.HexColor("#64748b"),
    )
    body_sty = ParagraphStyle(
        "A_body",
        parent=styles["Normal"],
        fontSize=9,
        fontName=font,
        textColor=colors.HexColor("#1e293b"),
    )
    right_sty = ParagraphStyle(
        "A_right",
        parent=styles["Normal"],
        fontSize=9,
        fontName=font,
        textColor=colors.HexColor("#1e293b"),
        alignment=TA_RIGHT,
    )
    total_sty = ParagraphStyle(
        "A_total",
        parent=styles["Normal"],
        fontSize=14,
        fontName=bold,
        textColor=colors.HexColor(acc),
        alignment=TA_RIGHT,
    )

    elements = []

    # ── CABECERA ────────────────────────────────────────────────────────────────
    issuer_name = albaran_data.get("issuer_name", "")
    issuer_nif = albaran_data.get("issuer_nif", "")
    issuer_address = albaran_data.get("issuer_address", "")
    alb_number = albaran_data.get("albaran_number", "")
    alb_date = albaran_data.get("date", "")

    company_block = [
        Paragraph(issuer_name or "Mi Empresa S.L.", title_sty),
        Spacer(1, 8),
        Paragraph(f"NIF: {issuer_nif}" if issuer_nif else "", body_sty),
        Paragraph(issuer_address or "", body_sty),
    ]
    inv_block = [
        Spacer(1, 4),
        Paragraph(
            "ALBARÁN",
            ParagraphStyle(
                "A_ftitle",
                parent=styles["Normal"],
                fontSize=18,
                fontName=bold,
                textColor=colors.HexColor(acc),
                alignment=TA_RIGHT,
            ),
        ),
        Spacer(1, 6),
        Paragraph(f"Nº {alb_number}", right_sty),
        Paragraph(f"Fecha: {alb_date}", right_sty),
    ]
    ht = Table([[company_block, inv_block]], colWidths=[100 * mm, 80 * mm])
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
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor(acc)))
    elements.append(Spacer(1, 5 * mm))

    # ── CLIENTE ─────────────────────────────────────────────────────────────────
    client_name = albaran_data.get("client_name", "")
    client_nif = albaran_data.get("client_nif", "")
    if client_name:
        elements.append(Paragraph("DESTINATARIO:", header_sty))
        elements.append(Spacer(1, 2 * mm))
        elements.append(
            Paragraph(
                client_name,
                ParagraphStyle(
                    "A_cname",
                    parent=styles["Normal"],
                    fontSize=11,
                    fontName=bold,
                    textColor=colors.HexColor("#1e293b"),
                ),
            )
        )
        if client_nif:
            elements.append(Paragraph(f"NIF/CIF: {client_nif}", body_sty))
        elements.append(Spacer(1, 6 * mm))

    # ── LÍNEAS ──────────────────────────────────────────────────────────────────
    col_widths = [80 * mm, 20 * mm, 22 * mm, 20 * mm, 26 * mm]
    alb_lines = albaran_data.get("lines", [])
    table_data = [
        [
            Paragraph("Descripción", header_sty),
            Paragraph("Cant.", header_sty),
            Paragraph("Precio unit.", header_sty),
            Paragraph("IVA", header_sty),
            Paragraph("Total", right_sty),
        ]
    ]
    for line in alb_lines:
        table_data.append(
            [
                Paragraph(str(line.get("description", "")), body_sty),
                Paragraph(str(line.get("quantity", 1)), body_sty),
                Paragraph(f"{float(line.get('unit_price', 0)):.2f} €", body_sty),
                Paragraph(f"{float(line.get('tax_percentage', 21)):.0f}%", body_sty),
                Paragraph(f"{float(line.get('total', 0)):.2f} €", right_sty),
            ]
        )
    lines_table = Table(table_data, colWidths=col_widths)
    lines_table.setStyle(
        TableStyle(
            table_style_commands(th, len(alb_lines)) + [("ALIGN", (-1, 0), (-1, -1), "RIGHT")]
        )
    )
    elements.append(lines_table)
    elements.append(Spacer(1, 6 * mm))

    # ── TOTALES ─────────────────────────────────────────────────────────────────
    base = float(albaran_data.get("amount_base", 0))
    tax = float(albaran_data.get("tax_amount", 0))
    total = float(albaran_data.get("amount_total", 0))

    total_bg = colors.HexColor(acc + "22") if len(acc) == 7 else colors.HexColor("#eef2ff")
    totals_data = [
        [Paragraph("Base imponible:", right_sty), Paragraph(f"{base:.2f} €", right_sty)],
        [Paragraph("IVA:", right_sty), Paragraph(f"{tax:.2f} €", right_sty)],
        [
            Paragraph(
                "TOTAL:",
                ParagraphStyle(
                    "A_tlbl",
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

    # ── NOTAS ───────────────────────────────────────────────────────────────────
    notes = albaran_data.get("notes") or ""
    if notes:
        elements.append(Spacer(1, 8 * mm))
        elements.append(Paragraph("OBSERVACIONES", header_sty))
        elements.append(Spacer(1, 1.5 * mm))
        elements.append(Paragraph(str(notes), body_sty))

    # ── PIE ─────────────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 3 * mm))
    footer_text = (
        th.get("footer_text")
        or "Documento generado automáticamente por AutomatizaCore · Gracias por su confianza."
    )
    elements.append(
        Paragraph(
            footer_text,
            ParagraphStyle(
                "A_foot",
                parent=styles["Normal"],
                fontSize=7,
                fontName=font,
                textColor=colors.HexColor("#94a3b8"),
                alignment=TA_CENTER,
            ),
        )
    )

    doc.build(elements)
    return buffer.getvalue()
