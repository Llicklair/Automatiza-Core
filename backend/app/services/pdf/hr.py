"""
Generacion de PDFs de RRHH con formato oficial espanol.
- Nominas (recibo de salario)
- Finiquito
- Liquidacion y finiquito
- Registro de jornada
"""

import calendar
import io
from datetime import datetime

from app.services.documents._pdf_base import (
    _TRAD_BORDER,
    REPORTLAB_AVAILABLE,
    _format_date,
    _month_name_es,
    _signature_block,
    _trad_table_style,
    _traditional_styles,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
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
# Helpers internos
# ---------------------------------------------------------------------------


def _make_hr_doc(buffer, **kw):
    defaults = dict(
        pagesize=A4,
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    defaults.update(kw)
    return SimpleDocTemplate(buffer, **defaults)


def _parse_date(date_str: str | None) -> datetime | None:
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except Exception:
        return None


def _period_label(start_str: str, end_str: str) -> str:
    """Formato: 'del 1 al 31 de enero de 2026'."""
    s = _parse_date(start_str)
    e = _parse_date(end_str)
    if not s or not e:
        return f"{_format_date(start_str)} - {_format_date(end_str)}"
    return f"del {s.day} al {e.day} de {_month_name_es(e.month)} de {e.year}"


def _info_row(label: str, value: str, sty_lbl, sty_val) -> list:
    return [Paragraph(label, sty_lbl), Paragraph(str(value or ""), sty_val)]


def _eur(v: float) -> str:
    return f"{v:,.2f} \u20ac".replace(",", "X").replace(".", ",").replace("X", ".")


# ===========================================================================
# 1. NOMINA
# ===========================================================================


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
    total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + anticipos + other
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
            "y Orden ESS/2098/2014. Generado por AutomatizaPyme.",
            S["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ===========================================================================
# 2. FINIQUITO
# ===========================================================================


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


# ===========================================================================
# 3. LIQUIDACION Y FINIQUITO
# ===========================================================================


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


# ===========================================================================
# 4. REGISTRO DE JORNADA
# ===========================================================================


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
            "Generado por AutomatizaPyme.",
            S["footer"],
        )
    )

    doc.build(elements)
    return buffer.getvalue()


# ===========================================================================
# Fallbacks texto plano
# ===========================================================================


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


def _generate_simple_text(doc_type: str, data: dict) -> bytes:
    """Fallback generico para documentos HR."""
    emp = data.get("employee", {})
    content = f"{doc_type}\nEmpleado: {emp.get('name', '')}\n"
    if "liquido" in data:
        content += f"Liquido: {data['liquido']:.2f} EUR\n"
    return content.encode("utf-8")
