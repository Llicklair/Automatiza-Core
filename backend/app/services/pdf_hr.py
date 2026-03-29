"""
Generación de PDFs de RRHH: nóminas / recibos de salario.
"""
import io
from datetime import datetime

from app.services._pdf_base import (
    REPORTLAB_AVAILABLE, _format_date, build_theme, table_style_commands,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_payroll_pdf(payroll_data: dict, theme_config: dict | None = None) -> bytes:
    """
    Genera un PDF de nómina/recibo de salario.

    payroll_data debe contener:
    - employee: dict con name, nif, position, department
    - company: dict con name, nif, address
    - period_start: str (ISO)
    - period_end: str (ISO)
    - issue_date: str (ISO)
    - base_salary: float
    - irpf: float
    - ss_employee: float
    - other_deductions: float
    - net_salary: float
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_payroll_text(payroll_data)

    th   = build_theme(theme_config)
    acc  = th["accent_color"]
    font = th["_font"]
    bold = th["_font_bold"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=0 if th["header_style"] in ("color_band", "dark_band") else 15*mm,
        bottomMargin=15*mm)
    styles = getSampleStyleSheet()

    title_sty  = ParagraphStyle('PT_title',  parent=styles['Normal'], fontSize=20, fontName=bold, textColor=colors.HexColor('#1e293b'))
    header_sty = ParagraphStyle('PT_header', parent=styles['Normal'], fontSize=8,  fontName=bold, textColor=colors.HexColor('#64748b'))
    body_sty   = ParagraphStyle('PT_body',   parent=styles['Normal'], fontSize=9,  fontName=font, textColor=colors.HexColor('#1e293b'))
    right_sty  = ParagraphStyle('PT_right',  parent=styles['Normal'], fontSize=9,  fontName=font, textColor=colors.HexColor('#1e293b'), alignment=TA_RIGHT)
    net_sty    = ParagraphStyle('PT_net',    parent=styles['Normal'], fontSize=13, fontName=bold, textColor=colors.HexColor(acc), alignment=TA_RIGHT)

    elements = []
    employee   = payroll_data.get('employee', {})
    company    = payroll_data.get('company', {})
    period_str = f"{_format_date(payroll_data.get('period_start', ''))} — {_format_date(payroll_data.get('period_end', ''))}"

    # ── CABECERA según header_style ──────────────────────────────────────────
    h_style = th["header_style"]
    if h_style in ("color_band", "dark_band"):
        bg_color  = acc if h_style == "color_band" else "#1e293b"
        txt_color = colors.white
        sub_color = colors.HexColor('#e0e7ff') if h_style == "color_band" else colors.HexColor('#94a3b8')
        hdr_sty = ParagraphStyle('PT_hdr',  parent=styles['Normal'], fontSize=18, fontName=bold, textColor=txt_color)
        sub_sty = ParagraphStyle('PT_sub',  parent=styles['Normal'], fontSize=8,  fontName=font, textColor=sub_color)
        nom_sty = ParagraphStyle('PT_nom',  parent=styles['Normal'], fontSize=20, fontName=bold, textColor=colors.HexColor(acc) if h_style == "dark_band" else txt_color, alignment=TA_RIGHT)
        nom_sub = ParagraphStyle('PT_noms', parent=styles['Normal'], fontSize=9,  fontName=font, textColor=sub_color, alignment=TA_RIGHT)
        left_col = [
            Paragraph(company.get('name') or 'Mi Empresa S.L.', hdr_sty),
            Spacer(1, 4),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')} · {company.get('address', '')}", sub_sty),
        ]
        right_col = [
            Paragraph('NÓMINA', nom_sty),
            Spacer(1, 4),
            Paragraph(f"Período: {period_str}", nom_sub),
            Paragraph(f"Emisión: {_format_date(payroll_data.get('issue_date', ''))}", nom_sub),
        ]
        band = Table([[left_col, right_col]], colWidths=[110*mm, 70*mm])
        band.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor(bg_color)),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
            ('TOPPADDING', (0,0), (-1,-1), 14),
            ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ]))
        elements.append(band)
        elements.append(Spacer(1, 6*mm))
    else:
        # line_only / none — layout clásico
        header_data = [[
            [
                Paragraph(company.get('name') or 'Mi Empresa S.L.', title_sty),
                Spacer(1, 10),
                Paragraph(f"NIF: {company.get('nif', 'B00000000')}", body_sty),
                Paragraph(company.get('address', ''), body_sty),
            ],
            [
                Paragraph('NÓMINA', ParagraphStyle('PT_ntitle', parent=styles['Normal'],
                    fontSize=18, fontName=bold, textColor=colors.HexColor(acc), alignment=TA_RIGHT)),
                Spacer(1, 10),
                Paragraph(f"Período: {period_str}", right_sty),
                Paragraph(f"Emisión: {_format_date(payroll_data.get('issue_date', ''))}", right_sty),
            ],
        ]]
        ht = Table(header_data, colWidths=[95*mm, 85*mm])
        ht.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        elements.append(ht)
        elements.append(Spacer(1, 5*mm))
        if h_style == "line_only":
            elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor(acc)))
        elements.append(Spacer(1, 5*mm))

    # ── DATOS EMPLEADO ────────────────────────────────────────────────────────
    elements.append(Paragraph('DATOS DEL TRABAJADOR', header_sty))
    elements.append(Spacer(1, 2*mm))
    emp_data = [
        ['Nombre:', employee.get('name', '—'), 'NIF:',    employee.get('nif', '—')],
        ['Cargo:',  employee.get('position', '—'), 'Depto.:', employee.get('department', '—')],
    ]
    emp_table = Table(emp_data, colWidths=[25*mm, 70*mm, 20*mm, 65*mm])
    emp_table.setStyle(TableStyle([
        ('FONTNAME',  (0,0), (0,-1), bold), ('FONTNAME', (2,0), (2,-1), bold),
        ('FONTSIZE',  (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#64748b')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#64748b')),
        ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 5*mm))

    # ── DEVENGOS Y DEDUCCIONES ────────────────────────────────────────────────
    base      = float(payroll_data.get('base_salary', 0))
    ss_cc     = float(payroll_data.get('ss_contingencias_comunes', 0))
    ss_des    = float(payroll_data.get('ss_desempleo', 0))
    ss_fp     = float(payroll_data.get('ss_formacion_profesional', 0))
    ss_mei    = float(payroll_data.get('ss_mei', 0))
    irpf      = float(payroll_data.get('irpf', 0))
    irpf_rate = float(payroll_data.get('irpf_rate', 15.0))
    other     = float(payroll_data.get('other_deductions', 0))
    net       = float(payroll_data.get('net_salary', 0))
    total_ded = ss_cc + ss_des + ss_fp + ss_mei + irpf + other

    concepts_data = [
        [Paragraph('CONCEPTO', header_sty), Paragraph('DEVENGOS', header_sty), Paragraph('DEDUCCIONES', header_sty)],
        ['Salario base', f'{base:.2f} €', ''],
        [Paragraph('Cotización SS — Contingencias comunes (4,70%)', body_sty), '', f'{ss_cc:.2f} €'],
        [Paragraph('Cotización SS — Desempleo (1,55%)', body_sty), '', f'{ss_des:.2f} €'],
        [Paragraph('Cotización SS — Formación profesional (0,10%)', body_sty), '', f'{ss_fp:.2f} €'],
        [Paragraph('Cotización SS — MEI (0,13%)', body_sty), '', f'{ss_mei:.2f} €'],
        [Paragraph(f'Retención IRPF ({irpf_rate:.1f}%)', body_sty), '', f'{irpf:.2f} €'],
    ]
    if other > 0:
        concepts_data.append(['Otras deducciones', '', f'{other:.2f} €'])
    concepts_data.append(['', f'{base:.2f} €', f'{total_ded:.2f} €'])

    # Estilo de tabla según tema (solo header, el resto es de la tabla de conceptos)
    th_cmds = table_style_commands(th, len(concepts_data) - 1)
    concepts_table = Table(concepts_data, colWidths=[100*mm, 45*mm, 45*mm])
    concepts_table.setStyle(TableStyle(th_cmds + [
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME',  (0,-1), (-1,-1), bold),
        ('BACKGROUND',(0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
    ]))
    elements.append(Paragraph('DEVENGOS Y DEDUCCIONES', header_sty))
    elements.append(Spacer(1, 2*mm))
    elements.append(concepts_table)
    elements.append(Spacer(1, 6*mm))

    # ── NETO ─────────────────────────────────────────────────────────────────
    net_bg = colors.HexColor(acc + '22') if len(acc) == 7 else colors.HexColor('#f0fdf4')
    net_data = [[
        Paragraph('LÍQUIDO TOTAL A PERCIBIR:', ParagraphStyle('PT_nlbl',
            parent=styles['Normal'], fontSize=11, fontName=bold,
            textColor=colors.HexColor('#1e293b'), alignment=TA_RIGHT)),
        Paragraph(f'{net:.2f} €', net_sty),
    ]]
    net_table = Table(net_data, colWidths=[130*mm, 50*mm], hAlign='RIGHT')
    net_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), net_bg),
        ('TOPPADDING',   (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',(0,0), (-1,-1), 10),
        ('LINEABOVE',    (0,0), (-1,0),  2, colors.HexColor(acc)),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 6*mm))

    # ── COTIZACIÓN EMPRESA (informativo) ──────────────────────────────────────
    emp_cc    = round(base * 0.2360, 2)
    emp_des   = round(base * 0.0550, 2)
    emp_fp    = round(base * 0.0060, 2)
    emp_mei   = round(base * 0.0013, 2)
    emp_at    = round(base * 0.0150, 2)
    emp_total = emp_cc + emp_des + emp_fp + emp_mei + emp_at

    info_sty  = ParagraphStyle('PT_info',  parent=styles['Normal'], fontSize=7, fontName=font, textColor=colors.HexColor('#64748b'))
    info_bold = ParagraphStyle('PT_infob', parent=styles['Normal'], fontSize=7, fontName=bold, textColor=colors.HexColor('#64748b'))
    elements.append(Paragraph('COTIZACIÓN A CARGO DE LA EMPRESA (informativo)', info_bold))
    elements.append(Spacer(1, 1.5*mm))
    emp_info = Table([
        [Paragraph('Contingencias comunes (23,60%)', info_sty), Paragraph(f'{emp_cc:.2f} €', info_sty)],
        [Paragraph('Desempleo (5,50%)',               info_sty), Paragraph(f'{emp_des:.2f} €', info_sty)],
        [Paragraph('Formación profesional (0,60%)',   info_sty), Paragraph(f'{emp_fp:.2f} €', info_sty)],
        [Paragraph('MEI (0,13%)',                     info_sty), Paragraph(f'{emp_mei:.2f} €', info_sty)],
        [Paragraph('AT y EP (~1,50%)',                info_sty), Paragraph(f'{emp_at:.2f} €', info_sty)],
        [Paragraph('TOTAL EMPRESA',                   info_bold),Paragraph(f'{emp_total:.2f} €', info_bold)],
    ], colWidths=[80*mm, 30*mm])
    emp_info.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2), ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('LINEABOVE', (0,-1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(emp_info)
    elements.append(Spacer(1, 6*mm))

    # ── PIE ───────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 3*mm))
    footer_text = th.get("footer_text") or (
        'Recibo de nómina generado automáticamente por AutomatizaPyme. '
        'Conforme al Estatuto de los Trabajadores y normativa vigente.'
    )
    elements.append(Paragraph(footer_text, ParagraphStyle('PT_foot',
        parent=styles['Normal'], fontSize=7, fontName=font,
        textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)))

    doc.build(elements)
    return buffer.getvalue()


def _generate_simple_payroll_text(payroll_data: dict) -> bytes:
    """Fallback si reportlab no está disponible."""
    emp = payroll_data.get('employee', {})
    content = (
        f"NÓMINA\n"
        f"Empleado: {emp.get('name', '')}\n"
        f"Período: {payroll_data.get('period_start', '')} - {payroll_data.get('period_end', '')}\n"
        f"Salario bruto: {payroll_data.get('base_salary', 0):.2f} EUR\n"
        f"Neto a percibir: {payroll_data.get('net_salary', 0):.2f} EUR\n"
    )
    return content.encode('utf-8')
