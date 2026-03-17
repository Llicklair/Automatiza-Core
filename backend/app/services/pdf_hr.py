"""
Generación de PDFs de RRHH: nóminas / recibos de salario.
"""
import io
from datetime import datetime

from app.services._pdf_base import (
    REPORTLAB_AVAILABLE, _format_date,
)

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_payroll_pdf(payroll_data: dict) -> bytes:
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

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=15*mm, bottomMargin=15*mm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('PTitle', parent=styles['Normal'],
        fontSize=20, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'))
    header_style = ParagraphStyle('PHeader', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica-Bold', textColor=colors.HexColor('#64748b'))
    body_style = ParagraphStyle('PBody', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#1e293b'))
    right_style = ParagraphStyle('PRight', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica', textColor=colors.HexColor('#1e293b'), alignment=TA_RIGHT)
    green_style = ParagraphStyle('PGreen', parent=styles['Normal'],
        fontSize=13, fontName='Helvetica-Bold', textColor=colors.HexColor('#16a34a'), alignment=TA_RIGHT)

    elements = []
    employee = payroll_data.get('employee', {})
    company  = payroll_data.get('company', {})

    # ── CABECERA ──
    period_str = f"{_format_date(payroll_data.get('period_start', ''))} — {_format_date(payroll_data.get('period_end', ''))}"
    header_data = [[
        [
            Paragraph(company.get('name') or 'Mi Empresa S.L.', title_style),
            Spacer(1, 10),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')}", body_style),
            Paragraph(company.get('address', ''), body_style),
        ],
        [
            Paragraph('NÓMINA', ParagraphStyle('NTitle', parent=styles['Normal'],
                fontSize=18, fontName='Helvetica-Bold',
                textColor=colors.HexColor('#10b981'), alignment=TA_RIGHT)),
            Spacer(1, 10),
            Paragraph(f"Período: {period_str}", right_style),
            Paragraph(f"Emisión: {_format_date(payroll_data.get('issue_date', ''))}", right_style),
        ],
    ]]
    header_table = Table(header_data, colWidths=[95*mm, 85*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width='100%', thickness=1, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 5*mm))

    # ── DATOS EMPLEADO ──
    elements.append(Paragraph('DATOS DEL TRABAJADOR', header_style))
    elements.append(Spacer(1, 2*mm))
    emp_data = [
        ['Nombre:', employee.get('name', '—'), 'NIF:', employee.get('nif', '—')],
        ['Cargo:', employee.get('position', '—'), 'Depto.:', employee.get('department', '—')],
    ]
    emp_table = Table(emp_data, colWidths=[25*mm, 70*mm, 20*mm, 65*mm])
    emp_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TEXTCOLOR', (0,0), (0,-1), colors.HexColor('#64748b')),
        ('TEXTCOLOR', (2,0), (2,-1), colors.HexColor('#64748b')),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(emp_table)
    elements.append(Spacer(1, 5*mm))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 5*mm))

    # ── DEVENGOS Y DEDUCCIONES ──
    base = float(payroll_data.get('base_salary', 0))
    ss_cc = float(payroll_data.get('ss_contingencias_comunes', 0))
    ss_des = float(payroll_data.get('ss_desempleo', 0))
    ss_fp = float(payroll_data.get('ss_formacion_profesional', 0))
    ss_mei = float(payroll_data.get('ss_mei', 0))
    irpf = float(payroll_data.get('irpf', 0))
    irpf_rate = float(payroll_data.get('irpf_rate', 15.0))
    other = float(payroll_data.get('other_deductions', 0))
    net  = float(payroll_data.get('net_salary', 0))
    total_ss = ss_cc + ss_des + ss_fp + ss_mei
    total_ded = total_ss + irpf + other

    concepts_data = [
        [Paragraph('CONCEPTO', header_style), Paragraph('DEVENGOS', header_style), Paragraph('DEDUCCIONES', header_style)],
        ['Salario base', f'{base:.2f} €', ''],
        [Paragraph('Cotización SS — Contingencias comunes (4,70%)', body_style), '', f'{ss_cc:.2f} €'],
        [Paragraph('Cotización SS — Desempleo (1,55%)', body_style), '', f'{ss_des:.2f} €'],
        [Paragraph('Cotización SS — Formación profesional (0,10%)', body_style), '', f'{ss_fp:.2f} €'],
        [Paragraph('Cotización SS — MEI (0,13%)', body_style), '', f'{ss_mei:.2f} €'],
        [Paragraph(f'Retención IRPF ({irpf_rate:.1f}%)', body_style), '', f'{irpf:.2f} €'],
    ]
    if other > 0:
        concepts_data.append(['Otras deducciones', '', f'{other:.2f} €'])

    concepts_data.append(['', f'{base:.2f} €', f'{total_ded:.2f} €'])  # Totales

    col_w = [100*mm, 45*mm, 45*mm]
    concepts_table = Table(concepts_data, colWidths=col_w)
    concepts_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f8fafc')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#e2e8f0')),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#f1f5f9')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(Paragraph('DEVENGOS Y DEDUCCIONES', header_style))
    elements.append(Spacer(1, 2*mm))
    elements.append(concepts_table)
    elements.append(Spacer(1, 6*mm))

    # ── NETO ──
    net_data = [
        [Paragraph('LÍQUIDO TOTAL A PERCIBIR:', ParagraphStyle('NLabel', parent=styles['Normal'],
            fontSize=11, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'), alignment=TA_RIGHT)),
         Paragraph(f'{net:.2f} €', green_style)],
    ]
    net_table = Table(net_data, colWidths=[130*mm, 50*mm], hAlign='RIGHT')
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEABOVE', (0,0), (-1,0), 2, colors.HexColor('#16a34a')),
        ('ROUNDEDCORNERS', (0,0), (-1,-1), 4),
    ]))
    elements.append(net_table)
    elements.append(Spacer(1, 6*mm))

    # ── COTIZACIÓN EMPRESA (informativo) ──
    emp_cc = round(base * 0.2360, 2)
    emp_des = round(base * 0.0550, 2)
    emp_fp = round(base * 0.0060, 2)
    emp_mei = round(base * 0.0013, 2)
    emp_at = round(base * 0.0150, 2)
    emp_total = emp_cc + emp_des + emp_fp + emp_mei + emp_at

    info_style = ParagraphStyle('PInfo', parent=styles['Normal'],
        fontSize=7, fontName='Helvetica', textColor=colors.HexColor('#64748b'))
    info_bold = ParagraphStyle('PInfoB', parent=styles['Normal'],
        fontSize=7, fontName='Helvetica-Bold', textColor=colors.HexColor('#64748b'))

    elements.append(Paragraph('COTIZACIÓN A CARGO DE LA EMPRESA (informativo)', info_bold))
    elements.append(Spacer(1, 1.5*mm))
    emp_concepts = [
        [Paragraph('Contingencias comunes (23,60%)', info_style), Paragraph(f'{emp_cc:.2f} €', info_style)],
        [Paragraph('Desempleo (5,50%)', info_style), Paragraph(f'{emp_des:.2f} €', info_style)],
        [Paragraph('Formación profesional (0,60%)', info_style), Paragraph(f'{emp_fp:.2f} €', info_style)],
        [Paragraph('MEI (0,13%)', info_style), Paragraph(f'{emp_mei:.2f} €', info_style)],
        [Paragraph('AT y EP (~1,50%)', info_style), Paragraph(f'{emp_at:.2f} €', info_style)],
        [Paragraph('TOTAL EMPRESA', info_bold), Paragraph(f'{emp_total:.2f} €', info_bold)],
    ]
    emp_table_info = Table(emp_concepts, colWidths=[80*mm, 30*mm])
    emp_table_info.setStyle(TableStyle([
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('LINEABOVE', (0,-1), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
    ]))
    elements.append(emp_table_info)
    elements.append(Spacer(1, 6*mm))

    # ── PIE LEGAL ──
    elements.append(HRFlowable(width='100%', thickness=0.5, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        'Recibo de nómina generado automáticamente por AutomatizaPyme. '
        'Conforme al Estatuto de los Trabajadores y normativa vigente.',
        ParagraphStyle('PFooter', parent=styles['Normal'],
            fontSize=7, fontName='Helvetica',
            textColor=colors.HexColor('#94a3b8'), alignment=TA_CENTER)
    ))

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
