"""Generacion de PDF de finiquito con formato oficial espanol."""

import io

from app.services.documents._pdf_base import (
    _TRAD_BORDER,
    REPORTLAB_AVAILABLE,
    _format_date,
    _trad_table_style,
    _traditional_styles,
)
from app.services.pdf._hr_common import _eur, _generate_simple_text, _make_hr_doc

if REPORTLAB_AVAILABLE:
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle


def generate_finiquito_pdf(finiquito_data: dict) -> bytes:
    """
    Genera PDF de finiquito con formato oficial.

    finiquito_data:
      employee: {name, nif}
      company: {name, nif, address}
      fecha_baja: str (ISO)
      causa_baja: str
      conceptos: [{concepto: str, importe: float}]
      total_percepciones: float
      total_deducciones: float
      liquido: float
      fecha: str (ISO)
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_text("FINIQUITO", finiquito_data)

    S = _traditional_styles()
    buffer = io.BytesIO()
    doc = _make_hr_doc(buffer)
    elements: list = []

    employee = finiquito_data.get("employee", {})
    company = finiquito_data.get("company", {})
    fecha = _format_date(finiquito_data.get("fecha", ""))
    fecha_baja = _format_date(finiquito_data.get("fecha_baja", ""))

    # Titulo
    elements.append(Spacer(1, 10 * mm))
    elements.append(Paragraph("<b>FINIQUITO</b>", S["title"]))
    elements.append(Spacer(1, 10 * mm))

    # Parrafo narrativo
    causa = finiquito_data.get("causa_baja", "baja voluntaria")
    narrative = (
        f"D./D\u00f1a. <b>{employee.get('name', '')}</b>, "
        f"con N.I.F. <b>{employee.get('nif', '')}</b>, "
        f"trabajando al servicio de la empresa "
        f"<b>{company.get('name', '')}</b>, "
        f"con C.I.F. <b>{company.get('nif', '')}</b>, "
        f"manifiesta mediante el presente documento:"
    )
    elements.append(Paragraph(narrative, S["body"]))
    elements.append(Spacer(1, 4 * mm))

    elements.append(
        Paragraph(
            f"Que con esta fecha queda por completo <b>rescindida</b> la "
            f"relaci\u00f3n laboral que ten\u00edamos concertada, "
            f"por causa de: <b>{causa}</b>, con efectos de <b>{fecha_baja}</b>.",
            S["body"],
        )
    )
    elements.append(Spacer(1, 4 * mm))

    elements.append(
        Paragraph(
            "Que en este acto, la empresa hace entrega al trabajador, "
            "en concepto de liquidaci\u00f3n de haberes, las cantidades que "
            "a continuaci\u00f3n se detallan:",
            S["body"],
        )
    )
    elements.append(Spacer(1, 6 * mm))

    # Desglose
    elements.append(Paragraph("<b>DESGLOSE DEL FINIQUITO</b>", S["section"]))
    elements.append(Spacer(1, 2 * mm))

    right_sty = ParagraphStyle("fq_r", parent=S["small"], alignment=TA_RIGHT)

    conceptos = finiquito_data.get("conceptos", [])
    desglose = [["Concepto", "Importe"]]
    for c in conceptos:
        desglose.append(
            [
                c.get("concepto", ""),
                Paragraph(_eur(float(c.get("importe", 0))), right_sty),
            ]
        )

    total_perc = float(finiquito_data.get("total_percepciones", 0))
    total_ded = float(finiquito_data.get("total_deducciones", 0))
    liquido = float(finiquito_data.get("liquido", 0))

    desglose.append(["", ""])
    desglose.append(["Total Percepciones", Paragraph(f"<b>{_eur(total_perc)}</b>", right_sty)])
    desglose.append(["Total Deducciones", Paragraph(f"<b>{_eur(total_ded)}</b>", right_sty)])

    desg_tbl = Table(desglose, colWidths=[120 * mm, 50 * mm])
    desg_tbl.setStyle(
        TableStyle(
            _trad_table_style(has_header=True, grid=False)
            + [
                ("LINEBELOW", (0, -3), (-1, -3), 0.5, _TRAD_BORDER),
                ("FONTNAME", (0, -2), (0, -1), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(desg_tbl)
    elements.append(Spacer(1, 4 * mm))

    # Total liquido
    net_row = [
        [
            Paragraph("<b>Total L\u00edquido:</b>", S["body_bold"]),
            Paragraph(
                f"<b>{_eur(liquido)}</b>",
                ParagraphStyle("fqn", parent=S["body_bold"], alignment=TA_RIGHT),
            ),
        ]
    ]
    net_tbl = Table(net_row, colWidths=[120 * mm, 50 * mm])
    net_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, _TRAD_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(net_tbl)
    elements.append(Spacer(1, 8 * mm))

    # Conformidad
    elements.append(
        Paragraph(
            "Y en prueba de conformidad con cuanto antecede firmamos el presente finiquito:",
            S["body"],
        )
    )
    elements.append(Spacer(1, 2 * mm))

    elements.append(Paragraph("Recib\u00ed:", S["body"]))
    elements.append(Spacer(1, 8 * mm))
    elements.append(
        Paragraph(
            f"Fdo: {employee.get('name', '')}",
            S["body"],
        )
    )
    elements.append(Spacer(1, 2 * mm))
    elements.append(Paragraph(f"Fecha: {fecha}", S["body"]))
    elements.append(Spacer(1, 10 * mm))

    # Pie legal
    elements.append(HRFlowable(width="100%", thickness=0.5, color=_TRAD_BORDER))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            "El/la trabajador/a manifiesta que no ha hecho uso del derecho a la "
            "presencia de un/a representante legal de los trabajadores, "
            "por lo que siquiera la firma del mismo a tenor del art. 49.2 "
            "del Estatuto de los Trabajadores.",
            S["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()
