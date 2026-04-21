"""
Generación de PDFs: informe de texto genérico y snapshot mensual de gestión.

Re-export facade — la lógica vive en:
  - _snapshot_text.py    → generate_text_report_pdf
  - _snapshot_monthly.py → generate_snapshot_pdf
"""

from app.services.pdf_reports._snapshot_monthly import generate_snapshot_pdf  # noqa: F401
from app.services.pdf_reports._snapshot_text import generate_text_report_pdf  # noqa: F401

__all__ = [
    "generate_text_report_pdf",
    "generate_snapshot_pdf",
]
