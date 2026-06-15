"""
Generación de PDF: informe de texto genérico.
"""

import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)

from app.services.pdf.pdf_base import REPORTLAB_AVAILABLE

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
    )


def generate_text_report_pdf(title: str, content: str, category: str = "Informe") -> bytes:
    """
    Genera un PDF profesional a partir de un bloque de texto.
    Ideal para informes de banca, fiscalidad, resúmenes de email, etc.
    """
    if not REPORTLAB_AVAILABLE:
        return content.encode("utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=10,
    )
    category_style = ParagraphStyle(
        "ReportCat",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#6366f1"),
        textTransform="uppercase",
        spaceAfter=5,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        fontName="Helvetica",
        textColor=colors.HexColor("#334155"),
        leading=14,
    )
    date_style = ParagraphStyle(
        "ReportDate",
        parent=styles["Normal"],
        fontSize=8,
        fontName="Helvetica",
        textColor=colors.HexColor("#94a3b8"),
        alignment=TA_RIGHT,
    )

    elements = []

    elements.append(Paragraph(datetime.now().strftime("%d/%m/%Y %H:%M"), date_style))
    elements.append(Paragraph(category, category_style))
    elements.append(Paragraph(title, title_style))
    elements.append(
        HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=15)
    )

    for line in content.split("\n"):
        if not line.strip():
            elements.append(Spacer(1, 3 * mm))
            continue
        if line.strip().startswith(("•", "-", "*")):
            p_style = ParagraphStyle("Bullet", parent=body_style, leftIndent=5 * mm)
            elements.append(Paragraph(line.strip(), p_style))
        else:
            elements.append(Paragraph(line.strip(), body_style))
            elements.append(Spacer(1, 2 * mm))

    elements.append(Spacer(1, 10 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f1f5f9")))
    elements.append(
        Paragraph(
            "Generado por el Sistema de Inteligencia Artificial de AutomatizaCore",
            ParagraphStyle(
                "Footer",
                parent=styles["Normal"],
                fontSize=7,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#cbd5e1"),
            ),
        )
    )

    doc.build(elements)
    return buffer.getvalue()
