"""
Generación de PDFs fiscales — re-export facade.

La lógica vive en:
  - _fiscal_modelo303.py  → generate_modelo_303_pdf
  - _fiscal_report.py     → generate_fiscal_report_pdf, save_fiscal_report_to_db
"""

from app.services.pdf_reports._fiscal_modelo303 import generate_modelo_303_pdf  # noqa: F401
from app.services.pdf_reports._fiscal_report import (  # noqa: F401
    generate_fiscal_report_pdf,
    save_fiscal_report_to_db,
)

__all__ = [
    "generate_modelo_303_pdf",
    "generate_fiscal_report_pdf",
    "save_fiscal_report_to_db",
]
