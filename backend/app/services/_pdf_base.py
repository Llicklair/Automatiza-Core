"""
Utilidades compartidas para la generación de PDFs.
Importaciones de ReportLab + helpers de estilo reutilizables.
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


def _common_styles():
    """Devuelve dict de estilos comunes para todas las plantillas PDF."""
    if not REPORTLAB_AVAILABLE:
        return {}
    styles = getSampleStyleSheet()

    C = {
        'INDIGO': '#6366f1', 'EMERALD': '#10b981', 'RED': '#ef4444',
        'AMBER': '#f59e0b', 'BLUE': '#3b82f6', 'SLATE': '#1e293b',
        'GRAY': '#64748b', 'LIGHT': '#f8fafc', 'LINE': '#e2e8f0',
        'FOOTER': '#94a3b8',
    }

    def sty(name, **kw):
        return ParagraphStyle(name, parent=styles['Normal'], **kw)

    return {
        'styles': styles,
        'C': C,
        'title': sty('CTitle', fontSize=20, fontName='Helvetica-Bold', textColor=colors.HexColor(C['SLATE'])),
        'header': sty('CHeader', fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(C['GRAY'])),
        'body': sty('CBody', fontSize=9, fontName='Helvetica', textColor=colors.HexColor(C['SLATE'])),
        'right': sty('CRight', fontSize=9, fontName='Helvetica', textColor=colors.HexColor(C['SLATE']), alignment=TA_RIGHT),
        'right_bold': sty('CRightBold', fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor(C['SLATE']), alignment=TA_RIGHT),
        'footer': sty('CFooter', fontSize=7, fontName='Helvetica', textColor=colors.HexColor(C['FOOTER']), alignment=TA_CENTER),
        'section': sty('CSection', fontSize=10, fontName='Helvetica-Bold', textColor=colors.HexColor(C['GRAY']), spaceBefore=8, spaceAfter=4),
        'kpi_val': sty('CKpiVal', fontSize=16, fontName='Helvetica-Bold', textColor=colors.HexColor(C['SLATE']), alignment=TA_CENTER),
        'kpi_lbl': sty('CKpiLbl', fontSize=7, fontName='Helvetica', textColor=colors.HexColor(C['GRAY']), alignment=TA_CENTER),
    }


def _fmt_eur(v: float) -> str:
    return f"{v:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")


def _make_doc(buffer, **kw):
    defaults = dict(pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
    defaults.update(kw)
    return SimpleDocTemplate(buffer, **defaults)


def _table_header_style():
    """Estilo estándar para cabeceras de tabla."""
    return [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#64748b')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LINEBELOW', (0, 1), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]


def _format_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime('%d/%m/%Y')
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return date_str
