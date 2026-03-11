"""
Servicio de generación de PDFs para facturas y documentos del sistema.
Usa reportlab para generar PDFs en memoria y retornarlos como bytes.
"""
import io
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
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
        KeepTogether,
    )
    from reportlab.graphics.shapes import Drawing, Rect, String, Line
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.graphics import renderPDF
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_invoice_pdf(invoice_data: dict) -> bytes:
    """
    Genera un PDF de factura a partir de los datos del invoice.
    
    invoice_data debe contener:
    - number: str (número de factura)
    - date: str (fecha en ISO)
    - client: dict con name, nif, address, email
    - lines: list de dict con description, quantity, unit_price, tax_percentage, total
    - amount_base: float
    - tax_amount: float
    - amount_total: float
    - company: dict con name, nif, address, phone (datos del emisor)
    """
    if not REPORTLAB_AVAILABLE:
        return _generate_simple_text_pdf(invoice_data)
    
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15*mm,
        leftMargin=15*mm,
        topMargin=8*mm,
        bottomMargin=15*mm,
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'Title', parent=styles['Normal'],
        fontSize=20, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e293b'),
    )
    header_style = ParagraphStyle(
        'Header', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#64748b'),
    )
    body_style = ParagraphStyle(
        'Body', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=colors.HexColor('#1e293b'),
    )
    right_style = ParagraphStyle(
        'Right', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica',
        textColor=colors.HexColor('#1e293b'),
        alignment=TA_RIGHT,
    )
    total_style = ParagraphStyle(
        'Total', parent=styles['Normal'],
        fontSize=14, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#6366f1'),
        alignment=TA_RIGHT,
    )
    
    elements = []
    
    # ── CABECERA ────────────────────────────────────────────────────────────────
    company = invoice_data.get('company', {})
    client = invoice_data.get('client', {})
    
    header_data = [
        [
            # Col izquierda: empresa emisora
            [
                Paragraph(company.get('name') or 'Mi Empresa S.L.', title_style),
                Spacer(1, 15),
                Paragraph(f"NIF: {company.get('nif', 'B00000000')}", body_style),
                Paragraph(company.get('address', ''), body_style),
                Paragraph(company.get('phone', ''), body_style),
                Paragraph(company.get('email', ''), body_style) if company.get('email') else Spacer(1, 0),
            ],
            # Col derecha: datos de factura
            [
                Spacer(1, 4),
                Paragraph("FACTURA", ParagraphStyle('FTitle', parent=styles['Normal'],
                    fontSize=18, fontName='Helvetica-Bold',
                    textColor=colors.HexColor('#6366f1'), alignment=TA_RIGHT)),
                Spacer(1, 6),
                Paragraph(f"Nº {invoice_data.get('number', 'F-0001')}", right_style),
                Paragraph(f"Fecha: {_format_date(invoice_data.get('date', ''))}", right_style),
            ],
        ]
    ]
    
    header_table = Table(header_data, colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 6*mm))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 6*mm))
    
    # ── CLIENTE ─────────────────────────────────────────────────────────────────
    elements.append(Paragraph("FACTURAR A:", header_style))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(client.get('name', '—'), ParagraphStyle(
        'ClientName', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e293b'),
    )))
    if client.get('nif'):
        elements.append(Paragraph(f"NIF/CIF: {client['nif']}", body_style))
    if client.get('email'):
        elements.append(Paragraph(f"Email: {client['email']}", body_style))
    if client.get('address'):
        elements.append(Paragraph(client['address'], body_style))
    
    elements.append(Spacer(1, 6*mm))
    
    # ── LÍNEAS DE FACTURA ────────────────────────────────────────────────────────
    col_widths = [80*mm, 20*mm, 22*mm, 20*mm, 26*mm]
    table_data = [
        [
            Paragraph('Descripción', header_style),
            Paragraph('Cant.', header_style),
            Paragraph('Precio unit.', header_style),
            Paragraph('IVA', header_style),
            Paragraph('Total', right_style),
        ]
    ]
    
    for line in invoice_data.get('lines', []):
        table_data.append([
            Paragraph(str(line.get('description', '')), body_style),
            Paragraph(str(line.get('quantity', 1)), body_style),
            Paragraph(f"{float(line.get('unit_price', 0)):.2f} €", body_style),
            Paragraph(f"{float(line.get('tax_percentage', 21)):.0f}%", body_style),
            Paragraph(f"{float(line.get('total', 0)):.2f} €", right_style),
        ])
    
    lines_table = Table(table_data, colWidths=col_widths)
    lines_table.setStyle(TableStyle([
        # Cabecera
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#64748b')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        # Filas de datos
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        # Líneas separadoras
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0')),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(lines_table)
    elements.append(Spacer(1, 6*mm))
    
    # ── TOTALES ──────────────────────────────────────────────────────────────────
    base = float(invoice_data.get('amount_base', 0))
    tax = float(invoice_data.get('tax_amount', 0))
    total = float(invoice_data.get('amount_total', 0))
    
    totals_data = [
        [Paragraph('Base imponible:', right_style), Paragraph(f'{base:.2f} €', right_style)],
        [Paragraph('IVA:', right_style), Paragraph(f'{tax:.2f} €', right_style)],
        [Paragraph('TOTAL:', ParagraphStyle('TotalLabel', parent=styles['Normal'],
            fontSize=12, fontName='Helvetica-Bold',
            textColor=colors.HexColor('#6366f1'), alignment=TA_RIGHT)),
         Paragraph(f'{total:.2f} €', total_style)],
    ]
    
    totals_table = Table(totals_data, colWidths=[130*mm, 40*mm], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LINEABOVE', (0, 2), (-1, 2), 1, colors.HexColor('#e2e8f0')),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#eef2ff')),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 6*mm))

    # ── NOTAS Y FORMA DE PAGO ───────────────────────────────────────────────────
    payment_terms = invoice_data.get('payment_terms') or ""
    notes = invoice_data.get('notes') or ""
    if payment_terms or notes:
        elements.append(Spacer(1, 15*mm))
        if payment_terms:
            elements.append(Paragraph("FORMA DE PAGO", header_style))
            elements.append(Spacer(1, 1.5*mm))
            elements.append(Paragraph(str(payment_terms), body_style))
            elements.append(Spacer(1, 4*mm))
        if notes:
            elements.append(Paragraph("NOTAS", header_style))
            elements.append(Spacer(1, 1.5*mm))
            elements.append(Paragraph(str(notes), body_style))
        elements.append(Spacer(1, 8*mm))

    # ── PIE ──────────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e2e8f0')))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Documento generado automáticamente por AutomatizaPyme · Gracias por su confianza.",
        ParagraphStyle('Footer', parent=styles['Normal'],
            fontSize=7, fontName='Helvetica',
            textColor=colors.HexColor('#94a3b8'),
            alignment=TA_CENTER)
    ))
    
    doc.build(elements)
    return buffer.getvalue()


def _format_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime('%d/%m/%Y')
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return date_str


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

    # ── CABECERA ────────────────────────────────────────────────────────────────
    period_str = f"{_format_date(payroll_data.get('period_start', ''))} — {_format_date(payroll_data.get('period_end', ''))}"
    header_data = [[
        [
            Paragraph(company.get('name') or 'Mi Empresa S.L.', title_style),
            Spacer(1, 3),
            Paragraph(f"NIF: {company.get('nif', 'B00000000')}", body_style),
            Paragraph(company.get('address', ''), body_style),
        ],
        [
            Paragraph('NÓMINA', ParagraphStyle('NTitle', parent=styles['Normal'],
                fontSize=18, fontName='Helvetica-Bold',
                textColor=colors.HexColor('#10b981'), alignment=TA_RIGHT)),
            Spacer(1, 4),
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

    # ── DATOS EMPLEADO ──────────────────────────────────────────────────────────
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

    # ── DEVENGOS ────────────────────────────────────────────────────────────────
    base = float(payroll_data.get('base_salary', 0))
    irpf = float(payroll_data.get('irpf', 0))
    ss   = float(payroll_data.get('ss_employee', 0))
    other = float(payroll_data.get('other_deductions', 0))
    net  = float(payroll_data.get('net_salary', 0))
    total_ded = irpf + ss + other

    concepts_data = [
        [Paragraph('CONCEPTO', header_style), Paragraph('DEVENGOS', header_style), Paragraph('DEDUCCIONES', header_style)],
        ['Salario base', f'{base:.2f} €', ''],
        ['Retención IRPF (~15%)', '', f'{irpf:.2f} €'],
        ['Seguridad Social (~6.35%)', '', f'{ss:.2f} €'],
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

    # ── NETO ──────────────────────────────────────────────────────────────────
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
    elements.append(Spacer(1, 10*mm))

    # ── PIE LEGAL ──────────────────────────────────────────────────────────────
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


def generate_text_report_pdf(title: str, content: str, category: str = "Informe") -> bytes:
    """
    Genera un PDF profesional a partir de un bloque de texto.
    Ideal para informes de banca, fiscalidad, resúmenes de email, etc.
    """
    if not REPORTLAB_AVAILABLE:
        return content.encode('utf-8')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    styles = getSampleStyleSheet()

    # Estilos
    title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'],
        fontSize=18, fontName='Helvetica-Bold', textColor=colors.HexColor('#1e293b'),
        spaceAfter=10)
    category_style = ParagraphStyle('ReportCat', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor('#6366f1'),
        textTransform='uppercase', spaceAfter=5)
    body_style = ParagraphStyle('ReportBody', parent=styles['Normal'],
        fontSize=10, fontName='Helvetica', textColor=colors.HexColor('#334155'),
        leading=14)
    date_style = ParagraphStyle('ReportDate', parent=styles['Normal'],
        fontSize=8, fontName='Helvetica', textColor=colors.HexColor('#94a3b8'),
        alignment=TA_RIGHT)

    elements = []
    
    # Fecha y Categoría
    elements.append(Paragraph(datetime.now().strftime('%d/%m/%Y %H:%M'), date_style))
    elements.append(Paragraph(category, category_style))
    
    # Título
    elements.append(Paragraph(title, title_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

    # Cuerpo (procesar saltos de línea)
    for line in content.split('\n'):
        if not line.strip():
            elements.append(Spacer(1, 3*mm))
            continue
        
        # Detectar "bullet points" simples
        if line.strip().startswith(('•', '-', '*')):
            p_style = ParagraphStyle('Bullet', parent=body_style, leftIndent=5*mm)
            elements.append(Paragraph(line.strip(), p_style))
        else:
            elements.append(Paragraph(line.strip(), body_style))
            elements.append(Spacer(1, 2*mm))

    # Pie
    elements.append(Spacer(1, 10*mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#f1f5f9')))
    elements.append(Paragraph(
        "Generado por el Sistema de Inteligencia Artificial de AutomatizaPyme",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor('#cbd5e1'))
    ))

    doc.build(elements)
    return buffer.getvalue()


def generate_snapshot_pdf(snap: dict, company_name: str, month: str) -> bytes:
    """
    Genera el informe mensual con gráficas de barras y circular.

    snap: dict con estructura igual a CompanySnapshot:
      snap["facturas"], snap["banca"], snap["rrhh"], snap["clientes"], snap["resumen_ejecutivo"]
    """
    if not REPORTLAB_AVAILABLE:
        return _snapshot_text_fallback(snap, company_name, month)

    # ── Paleta de colores ────────────────────────────────────────────────────────
    C_INDIGO  = colors.HexColor('#6366f1')
    C_EMERALD = colors.HexColor('#10b981')
    C_RED     = colors.HexColor('#ef4444')
    C_AMBER   = colors.HexColor('#f59e0b')
    C_BLUE    = colors.HexColor('#3b82f6')
    C_SLATE   = colors.HexColor('#1e293b')
    C_GRAY    = colors.HexColor('#64748b')
    C_LIGHT   = colors.HexColor('#f8fafc')
    C_LINE    = colors.HexColor('#e2e8f0')
    C_FOOTER  = colors.HexColor('#94a3b8')

    # ── Datos ────────────────────────────────────────────────────────────────────
    f = snap.get("facturas", {})
    b = snap.get("banca", {})
    h = snap.get("rrhh", {})
    c = snap.get("clientes", {})
    resumen = snap.get("resumen_ejecutivo", "")

    ingresos   = float(f.get("ingresos_total", 0))
    gastos     = float(f.get("gastos_total", 0))
    margen     = float(f.get("margen_bruto", 0))
    margen_pct = float(f.get("margen_pct", 0))
    pendiente  = float(f.get("importe_pendiente_cobro", 0))
    n_emitidas = int(f.get("facturas_emitidas", 0))
    n_recibidas = int(f.get("facturas_recibidas", 0))
    n_pend     = int(f.get("facturas_pendientes_cobro", 0))

    bank_in    = float(b.get("total_ingresos", 0))
    bank_out   = float(b.get("total_gastos", 0))
    bank_neto  = float(b.get("saldo_neto", 0))
    n_tx       = int(b.get("transacciones", 0))
    n_rec      = int(b.get("reconciliadas", 0))

    empleados  = int(h.get("empleados_activos", 0))
    nominas    = float(h.get("coste_nominas", 0))
    nom_pagadas = int(h.get("nominas_pagadas", 0))
    nom_pend   = int(h.get("nominas_pendientes", 0))

    total_cli  = int(c.get("total_clientes", 0))
    nuevos_cli = int(c.get("nuevos_periodo", 0))
    top_name   = c.get("top_client_name") or ""
    top_amt    = float(c.get("top_client_amount", 0))

    # ── Mes legible ─────────────────────────────────────────────────────────────
    try:
        y, mo = month.split("-")
        meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                 "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
        month_label = f"{meses[int(mo)-1]} {y}"
    except Exception:
        month_label = month

    # ── Documento ────────────────────────────────────────────────────────────────
    buffer = io.BytesIO()
    PAGE_W, PAGE_H = A4
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        rightMargin=15*mm, leftMargin=15*mm,
        topMargin=12*mm, bottomMargin=12*mm,
    )
    styles = getSampleStyleSheet()

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    s_company  = sty("Co", fontSize=20, fontName="Helvetica-Bold", textColor=C_SLATE)
    s_badge    = sty("Ba", fontSize=9,  fontName="Helvetica-Bold", textColor=C_INDIGO)
    s_month    = sty("Mo", fontSize=13, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_generated = sty("Ge", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_RIGHT)
    s_section  = sty("Se", fontSize=10, fontName="Helvetica-Bold", textColor=C_GRAY,
                     spaceBefore=8, spaceAfter=4)
    s_body     = sty("Bo", fontSize=9,  fontName="Helvetica", textColor=C_SLATE, leading=13)
    s_resumen  = sty("Re", fontSize=9,  fontName="Helvetica", textColor=colors.HexColor("#334155"),
                     leading=14, leftIndent=4*mm, rightIndent=4*mm)
    s_kpi_val  = sty("Kv", fontSize=16, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_CENTER)
    s_kpi_lbl  = sty("Kl", fontSize=7,  fontName="Helvetica",      textColor=C_GRAY,  alignment=TA_CENTER)
    s_footer   = sty("Fo", fontSize=7,  fontName="Helvetica", textColor=C_FOOTER, alignment=TA_CENTER)
    s_row_lbl  = sty("Rl", fontSize=8,  fontName="Helvetica", textColor=C_GRAY)
    s_row_val  = sty("Rv", fontSize=8,  fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT)
    s_row_val_em = sty("Rve", fontSize=8, fontName="Helvetica-Bold", textColor=C_INDIGO, alignment=TA_RIGHT)

    fmt_eur = lambda v: f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
    fmt_int = lambda v: str(int(v))

    elements = []

    # ══════════════════════════════════════════════════════════════════════════════
    # CABECERA
    # ══════════════════════════════════════════════════════════════════════════════
    header_data = [[
        [
            Paragraph(company_name, s_company),
            Spacer(1, 3),
            Paragraph("INFORME MENSUAL DE GESTIÓN", s_badge),
        ],
        [
            Paragraph(month_label, s_month),
            Spacer(1, 3),
            Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", s_generated),
        ],
    ]]
    header_table = Table(header_data, colWidths=[110*mm, 65*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 0),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width="100%", thickness=2, color=C_INDIGO))
    elements.append(Spacer(1, 4*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # RESUMEN EJECUTIVO (caja)
    # ══════════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("RESUMEN EJECUTIVO", s_section))
    resumen_box = Table(
        [[Paragraph(resumen, s_resumen)]],
        colWidths=[175*mm],
    )
    resumen_box.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#eef2ff")),
        ("LINEABOVE",  (0,0), (-1, 0), 2, C_INDIGO),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(resumen_box)
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # KPI CARDS — fila de 4 tarjetas
    # ══════════════════════════════════════════════════════════════════════════════
    def kpi_cell(val: str, lbl: str, color):
        return [
            Paragraph(val, sty("kv2", fontSize=14, fontName="Helvetica-Bold",
                                textColor=color, alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(lbl, s_kpi_lbl),
        ]

    kpi_data = [[
        kpi_cell(fmt_eur(ingresos),  "Ingresos",      C_EMERALD),
        kpi_cell(fmt_eur(gastos),    "Gastos",         C_RED),
        kpi_cell(fmt_eur(margen),    f"Margen ({margen_pct:.1f}%)", C_INDIGO),
        kpi_cell(fmt_eur(pendiente), f"Pendiente cobro\n({n_pend} fact.)", C_AMBER),
    ]]
    kpi_table = Table(kpi_data, colWidths=[43.75*mm]*4)
    kpi_table.setStyle(TableStyle([
        ("BOX",         (0,0), (0,0), 0.5, C_EMERALD),
        ("BOX",         (1,0), (1,0), 0.5, C_RED),
        ("BOX",         (2,0), (2,0), 0.5, C_INDIGO),
        ("BOX",         (3,0), (3,0), 0.5, C_AMBER),
        ("BACKGROUND",  (0,0), (0,0), colors.HexColor("#f0fdf4")),
        ("BACKGROUND",  (1,0), (1,0), colors.HexColor("#fef2f2")),
        ("BACKGROUND",  (2,0), (2,0), colors.HexColor("#eef2ff")),
        ("BACKGROUND",  (3,0), (3,0), colors.HexColor("#fffbeb")),
        ("TOPPADDING",  (0,0), (-1,-1), 8),
        ("BOTTOMPADDING",(0,0),(-1,-1), 8),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0), (-1,-1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 6*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # GRÁFICA 1 — Barra: Ingresos / Gastos / Margen
    # ══════════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("1. ANÁLISIS DE FACTURACIÓN", s_section))

    def _bar_chart(labels, values, bar_colors, width=175*mm, height=55*mm) -> Drawing:
        d = Drawing(width, height)
        chart = VerticalBarChart()
        chart.x = 40
        chart.y = 20
        chart.width  = width  - 55
        chart.height = height - 30

        chart.data       = [values]
        chart.categoryAxis.categoryNames = labels
        chart.categoryAxis.labels.fontSize = 8
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.textColor = colors.HexColor("#64748b")
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.labels.fontName  = "Helvetica"
        chart.valueAxis.labels.textColor = colors.HexColor("#64748b")
        chart.valueAxis.visibleGrid = True
        chart.valueAxis.gridStrokeColor = colors.HexColor("#f1f5f9")
        chart.valueAxis.gridStrokeWidth = 0.5
        chart.valueAxis.forceZero = True

        # Formatear eje Y en miles
        max_v = max(abs(v) for v in values) if values else 1
        chart.valueAxis.valueMax = max_v * 1.25
        chart.valueAxis.valueMin = min(0, min(values) * 1.1)

        chart.bars[0].fillColor = bar_colors[0]
        chart.bars[0].strokeColor = colors.white
        chart.bars[0].strokeWidth = 0.5

        # Colores individuales por barra
        for i, c_ in enumerate(bar_colors):
            chart.bars[(0, i)].fillColor = c_

        d.add(chart)
        return d

    bar_labels = ["Ingresos", "Gastos", "Margen bruto"]
    bar_values = [ingresos, gastos, margen]
    bar_colors_list = [C_EMERALD, C_RED, C_INDIGO if margen >= 0 else C_RED]

    bar_drawing = _bar_chart(bar_labels, bar_values, bar_colors_list)

    # Tabla de detalle facturación al lado derecho
    fac_detail = [
        [Paragraph("Concepto", s_row_lbl), Paragraph("Valor", s_row_val)],
        [Paragraph("Facturas emitidas", s_row_lbl), Paragraph(fmt_int(n_emitidas), s_row_val)],
        [Paragraph("Facturas recibidas", s_row_lbl), Paragraph(fmt_int(n_recibidas), s_row_val)],
        [Paragraph("Pend. de cobro", s_row_lbl), Paragraph(f"{n_pend} · {fmt_eur(pendiente)}", s_row_val)],
        [Paragraph("Margen bruto", s_row_lbl), Paragraph(fmt_eur(margen), s_row_val_em)],
    ]
    fac_tbl = Table(fac_detail, colWidths=[35*mm, 25*mm])
    fac_tbl.setStyle(TableStyle([
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("LINEBELOW",   (0,0), (-1,0),  0.5, C_LINE),
        ("LINEBELOW",   (0,1), (-1,-2), 0.3, colors.HexColor("#f1f5f9")),
        ("BACKGROUND",  (0,0), (-1,0),  C_LIGHT),
        ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
    ]))

    combined_fac = Table([[bar_drawing, fac_tbl]], colWidths=[120*mm, 65*mm])
    combined_fac.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
    ]))
    elements.append(combined_fac)
    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # GRÁFICA 2 — Circular: Distribución de costes
    # ══════════════════════════════════════════════════════════════════════════════
    elements.append(Paragraph("2. DISTRIBUCIÓN DE COSTES", s_section))

    # Datos: gastos facturación + nóminas + banca salidas (si hay datos)
    pie_data_raw = [
        ("Gastos facturación", gastos,  C_RED),
        ("Nóminas",            nominas, C_AMBER),
        ("Salidas bancarias",  bank_out, C_BLUE),
    ]
    pie_data_raw = [(lbl, v, c_) for lbl, v, c_ in pie_data_raw if v > 0]
    total_costes = sum(v for _, v, _ in pie_data_raw)

    def _pie_chart(items, width=80*mm, height=65*mm) -> Drawing:
        d = Drawing(width, height)
        pie = Pie()
        pie.x = 10
        pie.y = 10
        pie.width  = height - 20
        pie.height = height - 20
        pie.data   = [v for _, v, _ in items]
        pie.labels = [
            f"{lbl}\n{(v/total_costes*100):.1f}%"
            for lbl, v, _ in items
        ] if total_costes > 0 else [lbl for lbl, _, _ in items]
        pie.sideLabels     = True
        pie.slices.strokeWidth = 0.5
        pie.slices.strokeColor = colors.white
        pie.labelRadius    = 1.3
        for i, (_, _, c_) in enumerate(items):
            pie.slices[i].fillColor = c_
        pie.slices.fontSize    = 7
        pie.slices.fontName    = "Helvetica"
        d.add(pie)
        return d

    if pie_data_raw:
        pie_drawing = _pie_chart(pie_data_raw, width=90*mm, height=65*mm)

        # Leyenda + detalle bancario / RRHH al lado
        right_sections = []
        # Banca
        right_sections.append([Paragraph("BANCA", sty("bs", fontSize=8, fontName="Helvetica-Bold", textColor=C_BLUE)), ""])
        right_sections.append([Paragraph("Entradas", s_row_lbl), Paragraph(fmt_eur(bank_in), s_row_val)])
        right_sections.append([Paragraph("Salidas", s_row_lbl), Paragraph(fmt_eur(bank_out), s_row_val)])
        right_sections.append([Paragraph("Saldo neto", s_row_lbl), Paragraph(fmt_eur(bank_neto), s_row_val_em)])
        right_sections.append([Paragraph(f"Movimientos: {n_tx}  Reconciliados: {n_rec}", s_row_lbl), ""])
        right_sections.append(["", ""])
        # RRHH
        right_sections.append([Paragraph("RRHH", sty("rs", fontSize=8, fontName="Helvetica-Bold", textColor=C_AMBER)), ""])
        right_sections.append([Paragraph("Empleados activos", s_row_lbl), Paragraph(fmt_int(empleados), s_row_val)])
        right_sections.append([Paragraph("Coste nóminas", s_row_lbl), Paragraph(fmt_eur(nominas), s_row_val)])
        right_sections.append([Paragraph(f"Pagadas: {nom_pagadas}  Pendientes: {nom_pend}", s_row_lbl), ""])

        right_tbl = Table(right_sections, colWidths=[50*mm, 30*mm])
        right_tbl.setStyle(TableStyle([
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("TOPPADDING",  (0,0), (-1,-1), 3),
            ("BOTTOMPADDING",(0,0),(-1,-1), 3),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0), (-1,-1), 0),
            ("SPAN",        (0,0), (1,0)),
            ("SPAN",        (0,4), (1,4)),
            ("SPAN",        (0,5), (1,5)),
            ("SPAN",        (0,6), (1,6)),
            ("SPAN",        (0,9), (1,9)),
            ("LINEBELOW",   (0,0), (1,0), 0.5, C_BLUE),
            ("LINEBELOW",   (0,6), (1,6), 0.5, C_AMBER),
        ]))

        combined_pie = Table([[pie_drawing, right_tbl]], colWidths=[95*mm, 85*mm])
        combined_pie.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 0),
            ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ]))
        elements.append(combined_pie)
    else:
        elements.append(Paragraph("Sin datos de costes para este período.", s_body))

    elements.append(Spacer(1, 5*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # SECCIÓN 3 — CLIENTES
    # ══════════════════════════════════════════════════════════════════════════════
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph("3. CLIENTES", s_section))

    cli_data = [
        [Paragraph("Clientes totales", s_row_lbl), Paragraph(fmt_int(total_cli), s_row_val)],
        [Paragraph("Nuevos este período", s_row_lbl), Paragraph(fmt_int(nuevos_cli), s_row_val)],
    ]
    if top_name:
        cli_data.append([
            Paragraph("Cliente principal", s_row_lbl),
            Paragraph(f"{top_name}  ·  {fmt_eur(top_amt)}", s_row_val_em),
        ])
    cli_tbl = Table(cli_data, colWidths=[60*mm, 115*mm])
    cli_tbl.setStyle(TableStyle([
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 0),
        ("RIGHTPADDING",(0,0), (-1,-1), 0),
        ("LINEBELOW",   (0,0), (-1,-2), 0.3, colors.HexColor("#f1f5f9")),
    ]))
    elements.append(cli_tbl)
    elements.append(Spacer(1, 8*mm))

    # ══════════════════════════════════════════════════════════════════════════════
    # PIE
    # ══════════════════════════════════════════════════════════════════════════════
    elements.append(HRFlowable(width="100%", thickness=0.5, color=C_LINE))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Informe generado automáticamente por el motor de IA de AutomatizaPyme · "
        f"Período: {month_label} · {datetime.now().strftime('%d/%m/%Y')}",
        s_footer,
    ))

    doc.build(elements)
    return buffer.getvalue()


def _snapshot_text_fallback(snap: dict, company_name: str, month: str) -> bytes:
    """Fallback de texto plano si ReportLab no está disponible."""
    f = snap.get("facturas", {})
    lines = [
        f"INFORME MENSUAL {month} — {company_name}",
        f"Ingresos: {f.get('ingresos_total', 0):.2f} EUR",
        f"Gastos: {f.get('gastos_total', 0):.2f} EUR",
        f"Margen: {f.get('margen_bruto', 0):.2f} EUR",
    ]
    return "\n".join(lines).encode("utf-8")


def _generate_simple_text_pdf(invoice_data: dict) -> bytes:
    """Fallback minimalista si reportlab no está disponible."""
    content = f"""FACTURA {invoice_data.get('number', '')}
Fecha: {invoice_data.get('date', '')}
Cliente: {invoice_data.get('client', {}).get('name', '')}
Total: {invoice_data.get('amount_total', 0):.2f} EUR
"""
    return content.encode('utf-8')
