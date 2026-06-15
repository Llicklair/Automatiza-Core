"""
PDF generation subpackage.

Re-exports all public functions so that existing imports like
  from app.services.pdf import generate_invoice_pdf
  from app.services.pdf import generate_albaran_pdf
  from app.services.pdf import parse_pdf
all work seamlessly.
"""

# ── HR documents ────────────────────────────────────────────────────────────
# ── Base utilities (re-exported for legacy pdf_service importers) ─────────────
# ── Albaranes ───────────────────────────────────────────────────────────────
from app.services.pdf.albaranes import generate_albaran_pdf  # noqa: F401
from app.services.pdf.hr import (  # noqa: F401
    generate_finiquito_pdf,
    generate_liquidacion_finiquito_pdf,
    generate_payroll_pdf,
    generate_registro_jornada_pdf,
)

# ── Invoicing ───────────────────────────────────────────────────────────────
from app.services.pdf.invoices import (  # noqa: F401
    generate_invoice_pdf,
    generate_rectificative_invoice_pdf,
    generate_retention_invoice_pdf,
)

# ── PDF Parser ───────────────────────────────────────────────────────────────
from app.services.pdf.parser import (  # noqa: F401
    ParsedDocument,
    ParsedElement,
    parse_pdf,
)
from app.services.pdf.pdf_base import (  # noqa: F401
    REPORTLAB_AVAILABLE,
    _common_styles,
    _fmt_eur,
    _format_date,
    _make_doc,
    _table_header_style,
)

# ── Reports (lazy re-export para evitar ciclo pdf ↔ pdf_reports) ────────────
# pdf_reports importa indirectamente de pdf.parser via services.documents.smart_chunker.
# Antes hacíamos un import top-level aquí que cerraba el ciclo y reventaba a
# scripts standalone con `ImportError: cannot import name 'generate_cashflow_report_pdf'
# from partially initialized module 'app.services.pdf_reports'`. En el backend
# producción no se notaba porque el orden de imports lo evitaba por suerte.
# Con __getattr__ (PEP 562) cargamos pdf_reports solo cuando alguien accede a
# uno de estos símbolos, rompiendo el ciclo en module init.
_LAZY_REPORT_EXPORTS = {
    "generate_cashflow_report_pdf",
    "generate_delinquency_report_pdf",
    "generate_modelo_303_pdf",
    "generate_rgpd_registry_pdf",
    "generate_snapshot_pdf",
    "generate_text_report_pdf",
}


def __getattr__(name: str):
    if name in _LAZY_REPORT_EXPORTS:
        import importlib

        mod = importlib.import_module("app.services.pdf_reports")
        return getattr(mod, name)
    raise AttributeError(f"module 'app.services.pdf' has no attribute {name!r}")
