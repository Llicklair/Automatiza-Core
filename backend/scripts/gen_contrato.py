from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

doc = SimpleDocTemplate(
    "/tmp/contrato_prueba_automatizacore.pdf",
    pagesize=A4,
    leftMargin=2.5*cm, rightMargin=2.5*cm,
    topMargin=2.5*cm, bottomMargin=2.5*cm,
)

styles = getSampleStyleSheet()
title_style = ParagraphStyle("title", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=12)
section_style = ParagraphStyle("section", parent=styles["Normal"], fontSize=10, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)
body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=4, alignment=TA_JUSTIFY)
mono_style = ParagraphStyle("mono", parent=styles["Normal"], fontSize=9, fontName="Courier", spaceAfter=2)

def s(text): return Spacer(1, 0.3*cm)
def p(text, style=body_style): return Paragraph(text, style)
def h(text): return Paragraph(text, section_style)

story = [
    p("CONTRATO DE PRESTACI&Oacute;N DE SERVICIOS", title_style),
    p("En Madrid, a 25 de febrero de 2026"),
    s(1),
    h("REUNIDOS"),
    p("De una parte, <b>TECH SOLUTIONS SL</b>, con CIF B-12345678, domicilio social en Calle Gran V&iacute;a 45, 2&ordf; Planta, 28013 Madrid, representada por D. Alejandro Garc&iacute;a Mart&iacute;nez, Administrador &Uacute;nico (<i>en adelante, &ldquo;EL CLIENTE&rdquo;</i>)."),
    p("De otra parte, <b>AUTOMATIZA CORE SL</b>, con CIF B-87654321, domicilio social en Calle Serrano 22, Planta 3, 28001 Madrid, representada por D. Marcos L&oacute;pez Fern&aacute;ndez, Administrador (<i>en adelante, &ldquo;EL PROVEEDOR&rdquo;</i>)."),
    s(1),
    h("ESTIPULACIONES"),
    h("PRIMERA. OBJETO"),
    p("El presente contrato tiene por objeto la prestaci&oacute;n de servicios de automatizaci&oacute;n empresarial mediante inteligencia artificial, incluyendo:"),
    p("&nbsp;&nbsp;&nbsp;a) Agente de Facturaci&oacute;n."),
    p("&nbsp;&nbsp;&nbsp;b) Gesti&oacute;n Documental automatizada (OCR y clasificaci&oacute;n)."),
    p("&nbsp;&nbsp;&nbsp;c) Agente Bancario (PSD2 / GoCardless)."),
    p("&nbsp;&nbsp;&nbsp;d) Cumplimiento Fiscal (modelos AEAT 303, 130, 111)."),
    p("&nbsp;&nbsp;&nbsp;e) Panel de supervisi&oacute;n con aprobaciones humanas (Human-in-the-Loop)."),
    h("SEGUNDA. DURACI&Oacute;N"),
    p("El contrato tendr&aacute; vigencia de doce (12) meses desde el 1 de marzo de 2026 hasta el 28 de febrero de 2027, con pr&oacute;rroga autom&aacute;tica anual salvo preaviso de 30 d&iacute;as."),
    h("TERCERA. PRECIO Y PAGO"),
    p("Precio mensual: <b>999,00 EUR + IVA 21% = 1.208,79 EUR/mes</b>."),
    p("Pago mediante transferencia bancaria en los primeros 5 d&iacute;as naturales de cada mes:"),
    p("IBAN: ES91 2100 0418 4001 2345 6789 &mdash; CaixaBank (titular: AUTOMATIZA CORE SL)", mono_style),
    h("CUARTA. OBLIGACIONES DEL PROVEEDOR"),
    p("a) Disponibilidad m&iacute;nima del servicio: 99% mensual. &nbsp; b) Soporte t&eacute;cnico L-V de 9:00 a 18:00h. &nbsp; c) Actualizaciones peri&oacute;dicas y confidencialidad de datos (RGPD / LOPDGDD)."),
    h("QUINTA. OBLIGACIONES DEL CLIENTE"),
    p("a) Proporcionar acceso y credenciales necesarias. &nbsp; b) Designar un interlocutor t&eacute;cnico. &nbsp; c) Abonar puntualmente. &nbsp; d) No ceder acceso a terceros sin autorizaci&oacute;n escrita."),
    h("SEXTA. PROTECCI&Oacute;N DE DATOS"),
    p("En cumplimiento del RGPD (UE) 2016/679 y LOPDGDD 3/2018, EL PROVEEDOR actuar&aacute; como Encargado del Tratamiento. Se suscribir&aacute; el correspondiente Acuerdo de Tratamiento de Datos (ATD)."),
    h("S&Eacute;PTIMA. JURISDICCI&Oacute;N"),
    p("Legislaci&oacute;n espa&ntilde;ola. Para cualquier controversia, las partes se someten a los Juzgados y Tribunales de Madrid."),
    Spacer(1, 1.2*cm),
    p("<b>EL CLIENTE</b> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; <b>EL PROVEEDOR</b>"),
    Spacer(1, 1.5*cm),
    p("_______________________________&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; _______________________________", mono_style),
    p("D. Alejandro Garc&iacute;a Mart&iacute;nez &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; D. Marcos L&oacute;pez Fern&aacute;ndez"),
    p("TECH SOLUTIONS SL &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; AUTOMATIZA CORE SL"),
    p("CIF: B-12345678 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; CIF: B-87654321"),
    Spacer(1, 1*cm),
    h("ANEXO I &mdash; SLA (Service Level Agreement)"),
    p("Disponibilidad garantizada: 99% mensual | Tiempo m&aacute;ximo de respuesta: 60 s/tarea"),
    p("Soporte: <b>soporte@automatizacore.com</b> | Tel: <b>+34 91 555 12 34</b> | Horario: L-V 9:00-18:00h"),
]

doc.build(story)
print("PDF generado: /tmp/contrato_prueba_automatizacore.pdf")
