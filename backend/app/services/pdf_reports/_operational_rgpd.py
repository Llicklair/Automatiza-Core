"""
Generación de PDF: Registro de Actividades de Tratamiento (Art. 30 RGPD).
"""

import io
import logging
from datetime import UTC, datetime

_logger = logging.getLogger(__name__)

from app.services.pdf.pdf_base import (
    REPORTLAB_AVAILABLE,
    _common_styles,
    _make_doc,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )


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
        return b"REGISTRO RGPD\n"

    s = _common_styles()
    C = s["C"]
    buffer = io.BytesIO()
    doc = _make_doc(buffer)
    elements = []

    company = data.get("company", {})
    dpo = data.get("dpo")

    # ── CABECERA ──
    elements.append(Paragraph("Registro de Actividades de Tratamiento", s["title"]))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            "Artículo 30 del Reglamento General de Protección de Datos (UE) 2016/679",
            ParagraphStyle(
                "RGPDSubtitle",
                parent=s["styles"]["Normal"],
                fontSize=9,
                fontName="Helvetica",
                textColor=colors.HexColor(C["GRAY"]),
            ),
        )
    )
    elements.append(Spacer(1, 5 * mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor(C["INDIGO"])))
    elements.append(Spacer(1, 5 * mm))

    # ── RESPONSABLE DEL TRATAMIENTO ──
    elements.append(Paragraph("RESPONSABLE DEL TRATAMIENTO", s["section"]))
    resp_data = [
        [Paragraph("Denominación:", s["header"]), Paragraph(company.get("name", "—"), s["body"])],
        [Paragraph("NIF/CIF:", s["header"]), Paragraph(company.get("nif", "—"), s["body"])],
        [Paragraph("Dirección:", s["header"]), Paragraph(company.get("address", "—"), s["body"])],
    ]
    if dpo:
        resp_data.append(
            [
                Paragraph("DPO:", s["header"]),
                Paragraph(f"{dpo.get('name', '—')} ({dpo.get('email', '')})", s["body"]),
            ]
        )

    resp_table = Table(resp_data, colWidths=[30 * mm, 145 * mm])
    resp_table.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#f1f5f9")),
            ]
        )
    )
    elements.append(resp_table)
    elements.append(Spacer(1, 6 * mm))

    # ── ACTIVIDADES DE TRATAMIENTO ──
    activities = data.get("activities", [])
    fields = [
        ("name", "Actividad de tratamiento"),
        ("purpose", "Finalidad"),
        ("legal_basis", "Base legal"),
        ("data_subjects", "Categorías de interesados"),
        ("data_categories", "Categorías de datos"),
        ("recipients", "Destinatarios"),
        ("international_transfers", "Transferencias internacionales"),
        ("retention_period", "Plazo de conservación"),
        ("security_measures", "Medidas de seguridad"),
    ]

    for i, activity in enumerate(activities):
        elements.append(Paragraph(f"ACTIVIDAD {i + 1}: {activity.get('name', '—')}", s["section"]))
        act_data = []
        for key, label in fields:
            if key == "name":
                continue
            val = activity.get(key, "—") or "—"
            act_data.append(
                [
                    Paragraph(label, s["header"]),
                    Paragraph(str(val), s["body"]),
                ]
            )

        act_table = Table(act_data, colWidths=[50 * mm, 125 * mm])
        act_table.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#f1f5f9")),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f8fafc")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(act_table)
        elements.append(Spacer(1, 4 * mm))

    # ── PIE ──
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(C["LINE"])))
    elements.append(Spacer(1, 3 * mm))
    elements.append(
        Paragraph(
            f"Registro generado el {datetime.now(UTC).strftime('%d/%m/%Y')} · AutomatizaCore",
            s["footer"],
        )
    )
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("Firma del Responsable del Tratamiento:", s["header"]))
    elements.append(Spacer(1, 20 * mm))
    elements.append(HRFlowable(width="60%", thickness=0.5, color=colors.HexColor(C["SLATE"])))

    doc.build(elements)
    return buffer.getvalue()
