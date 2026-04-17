"""
Generación de PDFs operativos: RGPD, tesorería y morosidad.

Re-export facade — la lógica vive en:
  - _operational_rgpd.py      → generate_rgpd_registry_pdf
  - _operational_treasury.py  → generate_cashflow_report_pdf, generate_delinquency_report_pdf
"""

from app.services.pdf_reports._operational_rgpd import generate_rgpd_registry_pdf  # noqa: F401
from app.services.pdf_reports._operational_treasury import (  # noqa: F401
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
)

__all__ = [
    "generate_rgpd_registry_pdf",
    "generate_cashflow_report_pdf",
    "generate_delinquency_report_pdf",
]
