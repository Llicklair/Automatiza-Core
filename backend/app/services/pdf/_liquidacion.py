"""Generacion de PDF de liquidacion y finiquito con formato oficial espanol."""

import io

from app.services.documents._pdf_base import (
    _TRAD_BORDER,
    REPORTLAB_AVAILABLE,
    _format_date,
    _signature_block,
    _trad_table_style,
    _traditional_styles,
)
from app.services.pdf._hr_common import _eur, _generate_simple_text, _make_hr_doc

if REPORTLAB_AVAILABLE:
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle


def generate_liquidacion_finiquito_pdf(liquidacion_data: dict) -> bytes:
    """
    Genera PDF de documento de liquidacion y finiquito.

    liquidacion_data:
      employee: {name, nif, naf, fecha_alta, categoria}
      company: {name, nif, address, ccc}
      fecha_baja: str
      causa_baja: str
      conceptos: [{concepto, unidad, devengos, deducciones}]
      total_devengos: float
      total_deducciones: float
      liquido: float
      fecha: str
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_text("LIQUIDACION Y FINIQUITO", liquidacion_data)

    S = _traditional_styles()
    buffer = io.BytesIO()
    doc = _make_hr_doc(buffer)
    elements: list = []

    employee = liquidacion_data.get("employee", {})
    company = liquidacion_data.get("company", {})
    fecha = _format_date(liquidacion_data.get("fecha", ""))

    # Titulo
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph("<b>DOCUMENTO DE LIQUIDACI\u00d3N Y FINIQUITO</b>", S["title"]))
    elements.append(Spacer(1, 8 * mm))

    # Datos empresa
    elements.append(Paragraph("<b>DATOS DE LA EMPRESA</b>", S["section"]))
    emp_data = [
        ["Empresa:", company.get("name", ""), "N.I.F.:", company.get("nif", "")],
        ["Domicilio:", company.get("address", ""), "C.C.C.:", company.get("ccc", "")],
    ]
    emp_tbl = Table(emp_data, colWidths=[22 * mm, 65 * mm, 15 * mm, 65 * mm])
    emp_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(emp_tbl)
    elements.append(Spacer(1, 4 * mm))

    # Datos trabajador
    elements.append(Paragraph("<b>DATOS DEL TRABAJADOR</b>", S["section"]))
    trab_data = [
        ["Apellidos y nombre:", employee.get("name", ""), "N.I.F.:", employee.get("nif", "")],
        [
            "N\u00ba Afil. SS:",
            employee.get("naf", ""),
            "Fecha alta:",
            _format_date(employee.get("fecha_alta", "")),
        ],
        ["Categor\u00eda:", employee.get("categoria", ""), "", ""],
    ]
    trab_tbl = Table(trab_data, colWidths=[30 * mm, 57 * mm, 20 * mm, 60 * mm])
    trab_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(trab_tbl)
    elements.append(Spacer(1, 4 * mm))

    # Causa y fecha baja
    elements.append(
        Paragraph(
            f"<b>Motivo:</b> {liquidacion_data.get('causa_baja', '')} &nbsp;&nbsp; "
            f"<b>Fecha de baja:</b> {_format_date(liquidacion_data.get('fecha_baja', ''))}",
            S["body"],
        )
    )
    elements.append(Spacer(1, 6 * mm))

    # Desglose
    elements.append(Paragraph("<b>DESGLOSE DE LA LIQUIDACI\u00d3N</b>", S["section"]))
    elements.append(Spacer(1, 2 * mm))

    right_sty = ParagraphStyle("lq_r", parent=S["small"], alignment=TA_RIGHT)
    conceptos = liquidacion_data.get("conceptos", [])
    desg_header = ["Concepto", "Unidad", "Devengos", "Deducciones"]
    desg_rows = [desg_header]
    for c in conceptos:
        desg_rows.append(
            [
                c.get("concepto", ""),
                str(c.get("unidad", "")),
                Paragraph(_eur(float(c.get("devengos", 0))), right_sty)
                if float(c.get("devengos", 0))
                else "",
                Paragraph(_eur(float(c.get("deducciones", 0))), right_sty)
                if float(c.get("deducciones", 0))
                else "",
            ]
        )

    total_dev = float(liquidacion_data.get("total_devengos", 0))
    total_ded = float(liquidacion_data.get("total_deducciones", 0))
    liquido = float(liquidacion_data.get("liquido", 0))

    desg_rows.append(
        [
            "TOTALES",
            "",
            Paragraph(f"<b>{_eur(total_dev)}</b>", right_sty),
            Paragraph(f"<b>{_eur(total_ded)}</b>", right_sty),
        ]
    )

    desg_tbl = Table(desg_rows, colWidths=[75 * mm, 20 * mm, 35 * mm, 35 * mm])
    desg_tbl.setStyle(
        TableStyle(
            _trad_table_style(has_header=True, grid=True)
            + [
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, _TRAD_BORDER),
            ]
        )
    )
    elements.append(desg_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Liquido
    net_row = [
        [
            Paragraph("<b>IMPORTE L\u00cdQUIDO A PERCIBIR:</b>", S["body_bold"]),
            Paragraph(
                f"<b>{_eur(liquido)}</b>",
                ParagraphStyle("lqn", parent=S["body_bold"], alignment=TA_RIGHT),
            ),
        ]
    ]
    net_tbl = Table(net_row, colWidths=[120 * mm, 50 * mm])
    net_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, _TRAD_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(net_tbl)
    elements.append(Spacer(1, 6 * mm))

    # Fecha y firmas
    elements.append(Paragraph(f"Fecha: {fecha}", S["body"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(
        _signature_block(
            [
                "Sello y firma de la empresa",
                "Firma del trabajador",
                "Firma del representante legal",
            ]
        )
    )

    doc.build(elements)
    return buffer.getvalue()
