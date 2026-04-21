"""Helpers de formato y estilos para los PDFs de snapshot."""

from app.services.documents._pdf_base import REPORTLAB_AVAILABLE

if REPORTLAB_AVAILABLE:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer

# ── Paleta de colores ────────────────────────────────────────────────────────

C_INDIGO = None
C_EMERALD = None
C_RED = None
C_AMBER = None
C_BLUE = None
C_SLATE = None
C_GRAY = None
C_LIGHT = None
C_LINE = None
C_FOOTER = None

if REPORTLAB_AVAILABLE:
    C_INDIGO = colors.HexColor("#6366f1")
    C_EMERALD = colors.HexColor("#10b981")
    C_RED = colors.HexColor("#ef4444")
    C_AMBER = colors.HexColor("#f59e0b")
    C_BLUE = colors.HexColor("#3b82f6")
    C_SLATE = colors.HexColor("#1e293b")
    C_GRAY = colors.HexColor("#64748b")
    C_LIGHT = colors.HexColor("#f8fafc")
    C_LINE = colors.HexColor("#e2e8f0")
    C_FOOTER = colors.HexColor("#94a3b8")


# ── Funciones de formato ─────────────────────────────────────────────────────


def fmt_eur(v) -> str:
    return f"{v:,.2f} \u20ac".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_int(v) -> str:
    return str(int(v))


# ── Factory de estilos ───────────────────────────────────────────────────────


def sty(name: str, **kw) -> "ParagraphStyle":
    """Shortcut para crear ParagraphStyle basado en Normal."""
    styles = getSampleStyleSheet()
    return ParagraphStyle(name, parent=styles["Normal"], **kw)


def get_snapshot_styles() -> dict:
    """Devuelve dict con todos los estilos usados en el snapshot PDF."""
    return {
        "s_company": sty("Co", fontSize=20, fontName="Helvetica-Bold", textColor=C_SLATE),
        "s_badge": sty("Ba", fontSize=9, fontName="Helvetica-Bold", textColor=C_INDIGO),
        "s_month": sty(
            "Mo", fontSize=13, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT
        ),
        "s_generated": sty(
            "Ge", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_RIGHT
        ),
        "s_section": sty(
            "Se",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=C_GRAY,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "s_body": sty("Bo", fontSize=9, fontName="Helvetica", textColor=C_SLATE, leading=13),
        "s_resumen": sty(
            "Re",
            fontSize=9,
            fontName="Helvetica",
            textColor=colors.HexColor("#334155"),
            leading=14,
            leftIndent=4 * mm,
            rightIndent=4 * mm,
        ),
        "s_kpi_lbl": sty(
            "Kl", fontSize=7, fontName="Helvetica", textColor=C_GRAY, alignment=TA_CENTER
        ),
        "s_footer": sty(
            "Fo", fontSize=7, fontName="Helvetica", textColor=C_FOOTER, alignment=TA_CENTER
        ),
        "s_row_lbl": sty("Rl", fontSize=8, fontName="Helvetica", textColor=C_GRAY),
        "s_row_val": sty(
            "Rv", fontSize=8, fontName="Helvetica-Bold", textColor=C_SLATE, alignment=TA_RIGHT
        ),
        "s_row_val_em": sty(
            "Rve", fontSize=8, fontName="Helvetica-Bold", textColor=C_INDIGO, alignment=TA_RIGHT
        ),
    }


def kpi_cell(val: str, lbl: str, color, s_kpi_lbl) -> list:
    """Genera contenido de una celda KPI (valor + etiqueta)."""
    return [
        Paragraph(
            val,
            sty(
                "kv2",
                fontSize=14,
                fontName="Helvetica-Bold",
                textColor=color,
                alignment=TA_CENTER,
            ),
        ),
        Spacer(1, 2),
        Paragraph(lbl, s_kpi_lbl),
    ]
