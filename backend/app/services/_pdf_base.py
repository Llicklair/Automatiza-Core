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


_FONT_MAP = {
    "helvetica": ("Helvetica", "Helvetica-Bold"),
    "times":     ("Times-Roman", "Times-Bold"),
    "courier":   ("Courier", "Courier-Bold"),
}

DEFAULT_THEME: dict = {
    "accent_color":  "#6366f1",
    "font_family":   "helvetica",
    "layout_style":  "modern",
    "logo_position": "left",
    "header_style":  "color_band",
    "table_style":   "striped",
    "footer_text":   None,
}

# Paleta de presets — sustituye colores y fuentes a la vez
_PRESET_OVERRIDES: dict[str, dict] = {
    "modern":  {},
    "classic": {"font_family": "times",  "header_style": "line_only",   "table_style": "bordered", "logo_position": "center"},
    "minimal": {"font_family": "helvetica", "header_style": "line_only", "table_style": "clean",    "logo_position": "right"},
    "bold":    {"font_family": "helvetica", "header_style": "dark_band", "table_style": "accent_header", "logo_position": "left"},
}


def build_theme(config: dict | None = None) -> dict:
    """Fusiona config de plantilla con defaults. Devuelve tema completo listo para usar."""
    t = dict(DEFAULT_THEME)
    # 1. Aplicar preset del layout_style elegido (por encima de defaults)
    layout = (config or {}).get("layout_style", DEFAULT_THEME["layout_style"])
    preset = _PRESET_OVERRIDES.get(layout, {})
    t.update(preset)
    # 2. Aplicar valores explícitos del config (accent_color, font_family, etc.)
    if config:
        t.update({k: v for k, v in config.items() if v is not None and v != ""})
    # Resolver nombres de fuentes ReportLab
    font_regular, font_bold = _FONT_MAP.get(t["font_family"], ("Helvetica", "Helvetica-Bold"))
    t["_font"]      = font_regular
    t["_font_bold"] = font_bold
    return t


def table_style_commands(theme: dict, num_data_rows: int = 1) -> list:
    """Devuelve lista de comandos TableStyle según el estilo de tabla del tema."""
    if not REPORTLAB_AVAILABLE:
        return []
    acc = theme.get("accent_color", "#6366f1")
    style = theme.get("table_style", "striped")
    font  = theme.get("_font", "Helvetica")
    bold  = theme.get("_font_bold", "Helvetica-Bold")

    base = [
        ('FONTNAME',   (0, 0), (-1,  0), bold),
        ('FONTSIZE',   (0, 0), (-1,  0), 8),
        ('FONTNAME',   (0, 1), (-1, -1), font),
        ('FONTSIZE',   (0, 1), (-1, -1), 9),
        ('TOPPADDING',    (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
    ]
    if style == "striped":
        base += [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor('#64748b')),
            ('LINEBELOW',  (0, 0), (-1, 0), 1, colors.HexColor('#e2e8f0')),
            ('LINEBELOW',  (0, 1), (-1, -1), 0.5, colors.HexColor('#f1f5f9')),
        ]
        for i in range(2, num_data_rows + 1, 2):
            base.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#fafafa')))
    elif style == "bordered":
        base += [
            ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#374151')),
            ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
            ('GRID',        (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
        ]
    elif style == "clean":
        base += [
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.HexColor('#64748b')),
            ('LINEBELOW',  (0, 0), (-1, 0), 1.5, colors.HexColor('#1e293b')),
            ('LINEBELOW',  (0, 1), (-1, -1), 0.3, colors.HexColor('#e2e8f0')),
        ]
    elif style == "accent_header":
        base += [
            ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor(acc)),
            ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
            ('LINEBELOW',   (0, 1), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]
    return base


def _format_date(date_str: str) -> str:
    if not date_str:
        return datetime.now().strftime('%d/%m/%Y')
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%d/%m/%Y')
    except Exception:
        return date_str
