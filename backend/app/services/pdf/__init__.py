"""
PDF generation subpackage.

Re-exports all public functions so that existing imports like
  from app.services.pdf import generate_invoice_pdf
  from app.services.pdf import generate_albaran_pdf
  from app.services.pdf import parse_pdf
all work seamlessly.
"""

# ── HR documents ────────────────────────────────────────────────────────────
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

# ── Albaranes ───────────────────────────────────────────────────────────────
from app.services.pdf.albaranes import generate_albaran_pdf  # noqa: F401

# ── PDF Parser ───────────────────────────────────────────────────────────────
from app.services.pdf.parser import (  # noqa: F401
    ParsedDocument,
    ParsedElement,
    parse_pdf,
)

# ── Base utilities (re-exported for legacy pdf_service importers) ─────────────
from app.services.documents._pdf_base import (  # noqa: F401
    REPORTLAB_AVAILABLE,
    _common_styles,
    _fmt_eur,
    _format_date,
    _make_doc,
    _table_header_style,
)

# ── Reports ──────────────────────────────────────────────────────────────────
from app.services.pdf_reports import (  # noqa: F401
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_modelo_303_pdf,
    generate_rgpd_registry_pdf,
    generate_snapshot_pdf,
    generate_text_report_pdf,
)
