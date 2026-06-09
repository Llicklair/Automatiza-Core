"""Generacion de PDF de registro mensual de jornada."""

import calendar
import io
from datetime import datetime

from app.services.documents._pdf_base import (
    _TRAD_BORDER,
    REPORTLAB_AVAILABLE,
    _month_name_es,
    _signature_block,
    _trad_table_style,
    _traditional_styles,
)
from app.services.pdf._hr_common import _generate_simple_text, _make_hr_doc

if REPORTLAB_AVAILABLE:
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, Spacer, Table, TableStyle


def generate_registro_jornada_pdf(registro_data: dict) -> bytes:
    """
    Genera PDF de registro mensual de jornada.

    registro_data:
      employee: {name, nif}
      company: {name, nif, centro_trabajo}
      mes: int
      anio: int
      registros: [{dia, entrada, salida, horas_ordinarias, incidencias, horas_extras}]
      total_horas_ordinarias: float
      total_horas_extras: float
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_text("REGISTRO DE JORNADA", registro_data)

    S = _traditional_styles()
    buffer = io.BytesIO()
    doc = _make_hr_doc(buffer)
    elements: list = []

    employee = registro_data.get("employee", {})
    company = registro_data.get("company", {})
    mes = int(registro_data.get("mes", 1))
    anio = int(registro_data.get("anio", datetime.now().year))

    # Titulo
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("<b>Listado Resumen mensual del registro de jornada</b>", S["title"]))
    elements.append(Spacer(1, 6 * mm))

    # Cabecera info
    info_data = [
        ["Empresa:", company.get("name", ""), "Trabajador:", employee.get("name", "")],
        ["CIF:", company.get("nif", ""), "NIF:", employee.get("nif", "")],
        [
            "Centro de trabajo:",
            company.get("centro_trabajo", ""),
            "Mes/A\u00f1o:",
            f"{_month_name_es(mes).capitalize()} {anio}",
        ],
    ]
    info_tbl = Table(info_data, colWidths=[30 * mm, 55 * mm, 25 * mm, 55 * mm])
    info_tbl.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
            ]
        )
    )
    elements.append(info_tbl)
    elements.append(Spacer(1, 5 * mm))

    # Tabla de registros
    header = [
        "D\u00cdA",
        "HORA ENTRADA",
        "HORA SALIDA",
        "HORAS ORDINARIAS",
        "INCIDENCIAS",
        "HORAS EXTRAS",
    ]
    rows = [header]

    registros = registro_data.get("registros", [])
    days_in_month = calendar.monthrange(anio, mes)[1]

    # Crear dict para lookup rapido
    reg_dict = {}
    for r in registros:
        reg_dict[int(r.get("dia", 0))] = r

    for dia in range(1, days_in_month + 1):
        r = reg_dict.get(dia, {})
        rows.append(
            [
                str(dia),
                r.get("entrada", ""),
                r.get("salida", ""),
                f"{float(r.get('horas_ordinarias', 0)):.2f}" if r.get("horas_ordinarias") else "",
                r.get("incidencias", ""),
                f"{float(r.get('horas_extras', 0)):.2f}" if r.get("horas_extras") else "",
            ]
        )

    # Fila TOTAL
    total_ord = float(registro_data.get("total_horas_ordinarias", 0))
    total_ext = float(registro_data.get("total_horas_extras", 0))
    rows.append(["TOTAL", "", "", f"{total_ord:.2f}", "", f"{total_ext:.2f}"])

    reg_tbl = Table(rows, colWidths=[12 * mm, 28 * mm, 28 * mm, 30 * mm, 40 * mm, 25 * mm])
    reg_tbl.setStyle(
        TableStyle(
            _trad_table_style(has_header=True, grid=True)
            + [
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (1, 0), (2, -1), "CENTER"),
                ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                ("ALIGN", (5, 0), (5, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.75, _TRAD_BORDER),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
            ]
        )
    )
    elements.append(reg_tbl)
    elements.append(Spacer(1, 6 * mm))

    # Firmas
    elements.append(_signature_block(["Firma de la empresa", "Firma del trabajador"]))
    elements.append(Spacer(1, 6 * mm))

    # Localidad y fecha
    elements.append(
        Paragraph(
            f"A {datetime.now().day} de {_month_name_es(datetime.now().month)} de {datetime.now().year}",
            S["body"],
        )
    )
    elements.append(Spacer(1, 4 * mm))

    # Pie legal
    elements.append(HRFlowable(width="100%", thickness=0.5, color=_TRAD_BORDER))
    elements.append(Spacer(1, 2 * mm))
    elements.append(
        Paragraph(
            "Registro en cumplimiento del art. 34.9 del Estatuto de los Trabajadores. "
            "La empresa deber\u00e1 conservar los registros de jornada durante cuatro a\u00f1os. "
            "Generado por AutomatizaCore.",
            S["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()
