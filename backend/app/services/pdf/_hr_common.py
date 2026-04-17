"""Helpers compartidos por los generadores de PDF de RRHH."""

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
    from reportlab.lib.enums import TA_RIGHT  # noqa: F401
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle  # noqa: F401
    from reportlab.lib.units import mm  # noqa: F401
    from reportlab.platypus import (
        HRFlowable,  # noqa: F401
        Paragraph,  # noqa: F401
        SimpleDocTemplate,
        Spacer,  # noqa: F401
        Table,  # noqa: F401
        TableStyle,  # noqa: F401
    )


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


def _info_row(label: str, value: str, sty_lbl, sty_val) -> list:
    return [Paragraph(label, sty_lbl), Paragraph(str(value or ""), sty_val)]


def _eur(v: float) -> str:
    return f"{v:,.2f} \u20ac".replace(",", "X").replace(".", ",").replace("X", ".")


def _generate_simple_text(doc_type: str, data: dict) -> bytes:
    """Fallback generico para documentos HR."""
    emp = data.get("employee", {})
    content = f"{doc_type}\nEmpleado: {emp.get('name', '')}\n"
    if "liquido" in data:
        content += f"Liquido: {data['liquido']:.2f} EUR\n"
    return content.encode("utf-8")
