"""
pdf_reports package — re-exports all public generate_* functions
for backward compatibility with ``from app.services.pdf_reports import ...``.
"""

from app.services.pdf_reports._fiscal import (
    generate_fiscal_report_pdf,
    generate_modelo_303_pdf,
)
from app.services.pdf_reports._operational import (
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_rgpd_registry_pdf,
)
from app.services.pdf_reports._snapshot import (
    _snapshot_text_fallback,
    generate_snapshot_pdf,
    generate_text_report_pdf,
)

__all__ = [
    "generate_text_report_pdf",
    "generate_snapshot_pdf",
    "_snapshot_text_fallback",
    "generate_modelo_303_pdf",
    "generate_fiscal_report_pdf",
    "generate_rgpd_registry_pdf",
    "generate_cashflow_report_pdf",
    "generate_delinquency_report_pdf",
]
