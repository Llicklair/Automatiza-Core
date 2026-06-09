"""Generacion de PDF de nomina (recibo de salario) con formato oficial espanol."""

import io

from app.services.documents._pdf_base import (
    _TRAD_BORDER,
    REPORTLAB_AVAILABLE,
    _format_date,
    _month_name_es,
    _signature_block,
    _trad_table_style,
    _traditional_styles,
)
from app.services.pdf._hr_common import _eur, _info_row, _make_hr_doc, _parse_date

if REPORTLAB_AVAILABLE:
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, Table, TableStyle


def _period_label(start_str: str, end_str: str) -> str:
    """Formato: 'del 1 al 31 de enero de 2026'."""
    s = _parse_date(start_str)
    e = _parse_date(end_str)
    if not s or not e:
        return f"{_format_date(start_str)} - {_format_date(end_str)}"
    return f"del {s.day} al {e.day} de {_month_name_es(e.month)} de {e.year}"


def generate_payroll_pdf(payroll_data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera PDF de nomina con formato oficial espanol.
    Firma compatible con version anterior (theme_config se ignora).
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_payroll_text(payroll_data)

    S = _traditional_styles()
    buffer = io.BytesIO()
    doc = _make_hr_doc(buffer)
    elements: list = []

    employee = payroll_data.get("employee", {})
    company = payroll_data.get("company", {})

    # -- Datos numericos --
    base = float(payroll_data.get("base_salary", 0))
    gross = float(payroll_data.get("gross_salary") or base)
    ss_cc = float(payroll_data.get("ss_contingencias_comunes", 0))
    ss_des = float(payroll_data.get("ss_desempleo", 0))
    ss_fp = float(payroll_data.get("ss_formacion_profesional", 0))
    ss_mei = float(payroll_data.get("ss_mei", 0))
    cuota_sol = float(payroll_data.get("cuota_solidaridad", 0))
    irpf = float(payroll_data.get("irpf", 0))
    irpf_rate = float(payroll_data.get("pct_irpf") or payroll_data.get("irpf_rate", 15.0))
    pct_cc = float(payroll_data.get("pct_cc", 4.70))
    pct_des = float(payroll_data.get("pct_desempleo", 1.55))
    pct_fp = float(payroll_data.get("pct_fp", 0.10))
    pct_mei = float(payroll_data.get("pct_mei", 0.10))
    anticipos = float(payroll_data.get("anticipos", 0))
    other = float(payroll_data.get("other_deductions", 0))
    net = float(payroll_data.get("net_salary", 0))
    devengos = payroll_data.get("devengos_json") or {}
    total_dev = gross
    total_ded = ss_cc + ss_des + ss_fp + ss_mei + cuota_sol + irpf + anticipos + other
    base_cc = float(payroll_data.get("base_cotizacion_cc") or gross)
    base_irpf = float(payroll_data.get("base_irpf") or gross)
    cuotas = payroll_data.get("cuotas_empresa_json") or {}

    # Calcular dias del periodo
    ps = _parse_date(payroll_data.get("period_start", ""))
    pe = _parse_date(payroll_data.get("period_end", ""))
    total_dias = (pe - ps).days + 1 if ps and pe else 30

    # =====================================================================
    # CABECERA: Empresa (izq) | Trabajador (der)
    # =====================================================================
    emp_info = [
        _info_row("Empresa:", company.get("name", ""), S["small_bold"], S["small"]),
        _info_row("CIF/NIF:", company.get("nif", ""), S["small_bold"], S["small"]),
        _info_row("Domicilio:", company.get("address", ""), S["small_bold"], S["small"]),
        _info_row("CCC:", company.get("ccc", ""), S["small_bold"], S["small"]),
    ]
    emp_table = Table(emp_info, colWidths=[18 * mm, 68 * mm])
    emp_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    trab_info = [
        _info_row("Trabajador:", employee.get("name", ""), S["small_bold"], S["small"]),
        _info_row("NIF/NIE:", employee.get("nif", ""), S["small_bold"], S["small"]),
        _info_row(
            "N\u00ba Afil. SS:",
            employee.get("numero_afiliacion_ss", ""),
            S["small_bold"],
            S["small"],
        ),
        _info_row(
            "Grupo Prof.:",
            employee.get("categoria_profesional") or employee.get("position", ""),
            S["small_bold"],
            S["small"],
        ),
        _info_row("Grupo Cot.:", employee.get("grupo_cotizacion", ""), S["small_bold"], S["small"]),
    ]
    trab_table = Table(trab_info, colWidths=[20 * mm, 66 * mm])
    trab_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    header = Table([[emp_table, trab_table]], colWidths=[90 * mm, 90 * mm])
    header.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    elements.append(header)
    elements.append(Spacer(1, 3 * mm))

    # =====================================================================
    # PERIODO DE LIQUIDACION
    # =====================================================================
    period_text = _period_label(
        payroll_data.get("period_start", ""),
        payroll_data.get("period_end", ""),
    )
    period_data = [
        [
            Paragraph(f"<b>Per\u00edodo de liquidaci\u00f3n:</b> {period_text}", S["small"]),
            Paragraph(f"<b>Total d\u00edas:</b> {total_dias}", S["small"]),
        ]
    ]
    period_tbl = Table(period_data, colWidths=[140 * mm, 40 * mm])
    period_tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements.append(period_tbl)
    elements.append(Spacer(1, 4 * mm))

    # =====================================================================
    # I. DEVENGOS + II. DEDUCCIONES  (tabla unica, 3 columnas)
    # =====================================================================
    hdr = [
        Paragraph("<b>CONCEPTO</b>", S["small_bold"]),
        Paragraph(
            "<b>DEVENGOS</b>", ParagraphStyle("dh", parent=S["small_bold"], alignment=TA_RIGHT)
        ),
        Paragraph(
            "<b>DEDUCCIONES</b>", ParagraphStyle("ddh", parent=S["small_bold"], alignment=TA_RIGHT)
        ),
    ]
    rows = [hdr]

    right_sty = ParagraphStyle("rv", parent=S["small"], alignment=TA_RIGHT)

    # -- I. DEVENGOS --
    rows.append([Paragraph("<b>I. DEVENGOS</b>", S["small_bold"]), "", ""])

    # Percepciones salariales
    rows.append([Paragraph("<i>1. Percepciones salariales</i>", S["small"]), "", ""])
    rows.append([Paragraph("Salario base", S["small"]), Paragraph(_eur(base), right_sty), ""])
    for concepto, importe in (devengos or {}).items():
        if concepto != "salario_base" and float(importe or 0) != 0:
            label = concepto.replace("_", " ").capitalize()
            rows.append(
                [Paragraph(label, S["small"]), Paragraph(_eur(float(importe)), right_sty), ""]
            )

    # Percepciones no salariales (placeholder)
    rows.append([Paragraph("<i>2. Percepciones no salariales</i>", S["small"]), "", ""])

    # A. TOTAL DEVENGADO
    rows.append(
        [
            Paragraph("<b>A. TOTAL DEVENGADO</b>", S["small_bold"]),
            Paragraph(
                f"<b>{_eur(total_dev)}</b>",
                ParagraphStyle("td", parent=S["small_bold"], alignment=TA_RIGHT),
            ),
            "",
        ]
    )

    # -- II. DEDUCCIONES --
    rows.append([Paragraph("<b>II. DEDUCCIONES</b>", S["small_bold"]), "", ""])

    # SS trabajador
    ded_items = [
        (f"Cot. contingencias comunes ({pct_cc:.2f}%)", ss_cc),
        (f"Cot. desempleo ({pct_des:.2f}%)", ss_des),
        (f"Cot. formaci\u00f3n profesional ({pct_fp:.2f}%)", ss_fp),
        (f"Cot. MEI ({pct_mei:.2f}%)", ss_mei),
        (f"Retenci\u00f3n IRPF ({irpf_rate:.1f}%)", irpf),
    ]
    if cuota_sol > 0:
        ded_items.append(("Cuota de solidaridad", cuota_sol))
    if anticipos > 0:
        ded_items.append(("Anticipos", anticipos))
    if other > 0:
        ded_items.append(("Otras deducciones", other))

    for label, val in ded_items:
        rows.append([Paragraph(label, S["small"]), "", Paragraph(_eur(val), right_sty)])

    # B. TOTAL A DEDUCIR
    rows.append(
        [
            Paragraph("<b>B. TOTAL A DEDUCIR</b>", S["small_bold"]),
            "",
            Paragraph(
                f"<b>{_eur(total_ded)}</b>",
                ParagraphStyle("tdd", parent=S["small_bold"], alignment=TA_RIGHT),
            ),
        ]
    )

    concepts_tbl = Table(rows, colWidths=[100 * mm, 40 * mm, 40 * mm])
    concepts_tbl.setStyle(
        TableStyle(
            _trad_table_style(has_header=True, grid=False)
            + [
                ("LINEABOVE", (0, 0), (-1, 0), 0.75, _TRAD_BORDER),
                ("LINEBELOW", (0, 0), (-1, 0), 0.75, _TRAD_BORDER),
                ("BOX", (0, 0), (-1, -1), 0.5, _TRAD_BORDER),
            ]
        )
    )
    elements.append(concepts_tbl)
    elements.append(Spacer(1, 3 * mm))

    # =====================================================================
    # LIQUIDO TOTAL A PERCIBIR
    # =====================================================================
    net_row = [
        [
            Paragraph("<b>L\u00cdQUIDO TOTAL A PERCIBIR (A\u2212B):</b>", S["body_bold"]),
            Paragraph(
                f"<b>{_eur(net)}</b>",
                ParagraphStyle("net", parent=S["body_bold"], alignment=TA_RIGHT),
            ),
        ]
    ]
    net_tbl = Table(net_row, colWidths=[130 * mm, 50 * mm])
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
    elements.append(Spacer(1, 5 * mm))

    # =====================================================================
    # DETERMINACION DE BASES DE COTIZACION
    # =====================================================================
    elements.append(
        Paragraph(
            "<b>DETERMINACI\u00d3N DE LAS BASES DE COTIZACI\u00d3N A LA S.S. "
            "Y CONCEPTOS DE RECAUDACI\u00d3N CONJUNTA</b>",
            S["small_bold"],
        )
    )
    elements.append(Spacer(1, 2 * mm))

    # Cuotas empresa
    emp_cc = float(cuotas.get("cc") or round(base_cc * 0.2360, 2))
    emp_des = float(cuotas.get("desempleo") or round(base_cc * 0.0550, 2))
    emp_fp = float(cuotas.get("fp") or round(base_cc * 0.0060, 2))
    emp_mei = float(cuotas.get("mei") or round(base_cc * 0.0050, 2))
    emp_fogasa = float(cuotas.get("fogasa") or round(base_cc * 0.0020, 2))
    emp_at = float(cuotas.get("at_ep") or round(base_cc * 0.0150, 2))

    bc_header = [
        "Concepto",
        "Base",
        "% Empresa",
        "Aport. Empresa",
        "% Trabajador",
        "Aport. Trabajador",
    ]
    bc_rows = [bc_header]
    bc_rows.append(
        [
            "Contingencias comunes",
            _eur(base_cc),
            "23,60",
            _eur(emp_cc),
            f"{pct_cc:.2f}",
            _eur(ss_cc),
        ]
    )
    bc_rows.append(["AT y EP", _eur(base_cc), "variable", _eur(emp_at), "", ""])
    bc_rows.append(
        ["Desempleo", _eur(base_cc), "5,50", _eur(emp_des), f"{pct_des:.2f}", _eur(ss_des)]
    )
    bc_rows.append(
        [
            "Formaci\u00f3n profesional",
            _eur(base_cc),
            "0,60",
            _eur(emp_fp),
            f"{pct_fp:.2f}",
            _eur(ss_fp),
        ]
    )
    bc_rows.append(["MEI", _eur(base_cc), "0,50", _eur(emp_mei), f"{pct_mei:.2f}", _eur(ss_mei)])
    bc_rows.append(["FOGASA", _eur(base_cc), "0,20", _eur(emp_fogasa), "", ""])

    emp_total = emp_cc + emp_des + emp_fp + emp_mei + emp_fogasa + emp_at
    bc_rows.append(["", "", "Total coste empresa:", _eur(emp_total), "", ""])

    bc_tbl = Table(bc_rows, colWidths=[35 * mm, 25 * mm, 20 * mm, 25 * mm, 22 * mm, 25 * mm])
    bc_tbl.setStyle(
        TableStyle(
            _trad_table_style(has_header=True, grid=True)
            + [
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ]
        )
    )
    elements.append(bc_tbl)
    elements.append(Spacer(1, 4 * mm))

    # =====================================================================
    # BASE IRPF
    # =====================================================================
    irpf_row = [
        [
            Paragraph(
                f"<b>Base sujeta a retenci\u00f3n del IRPF:</b> {_eur(base_irpf)}", S["small_bold"]
            ),
        ]
    ]
    irpf_tbl = Table(irpf_row, colWidths=[180 * mm])
    irpf_tbl.setStyle(
        TableStyle(
            [
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(irpf_tbl)
    elements.append(Spacer(1, 6 * mm))

    # =====================================================================
    # FECHA Y FIRMAS
    # =====================================================================
    issue_date = _format_date(payroll_data.get("issue_date", ""))
    elements.append(Paragraph(f"Fecha: {issue_date}", S["body"]))
    elements.append(Spacer(1, 3 * mm))
    elements.append(_signature_block(["Sello y firma de la empresa", "Recib\u00ed del trabajador"]))
    elements.append(Spacer(1, 4 * mm))

    # Pie legal
    elements.append(
        Paragraph(
            "Recibo de salario conforme al art. 29.1 del Estatuto de los Trabajadores "
            "y Orden ESS/2098/2014. Generado por AutomatizaCore.",
            S["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


def _generate_simple_payroll_text(payroll_data: dict) -> bytes:
    """Fallback si reportlab no esta disponible."""
    emp = payroll_data.get("employee", {})
    content = (
        f"NOMINA\n"
        f"Empleado: {emp.get('name', '')}\n"
        f"Periodo: {payroll_data.get('period_start', '')} - {payroll_data.get('period_end', '')}\n"
        f"Salario bruto: {payroll_data.get('base_salary', 0):.2f} EUR\n"
        f"Neto a percibir: {payroll_data.get('net_salary', 0):.2f} EUR\n"
    )
    return content.encode("utf-8")
