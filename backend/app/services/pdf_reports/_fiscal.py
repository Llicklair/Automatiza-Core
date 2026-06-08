"""
Generación de PDFs fiscales — re-export facade.

La lógica vive en:
  - _fiscal_modelo303.py  → generate_modelo_303_pdf
  - _fiscal_modelos.py    → generate_modelo_{130,111,190,347,390}_pdf
  - _fiscal_report.py     → generate_fiscal_report_pdf, save_fiscal_report_to_db
"""

from app.services.pdf_reports._fiscal_modelo303 import generate_modelo_303_pdf  # noqa: F401
from app.services.pdf_reports._fiscal_modelos import (  # noqa: F401
    generate_modelo_111_pdf,
    generate_modelo_115_pdf,
    generate_modelo_130_pdf,
    generate_modelo_190_pdf,
    generate_modelo_347_pdf,
    generate_modelo_349_pdf,
    generate_modelo_390_pdf,
)
from app.services.pdf_reports._fiscal_report import (  # noqa: F401
    generate_fiscal_report_pdf,
    save_fiscal_report_to_db,
)

__all__ = [
    "generate_modelo_303_pdf",
    "generate_modelo_130_pdf",
    "generate_modelo_111_pdf",
    "generate_modelo_115_pdf",
    "generate_modelo_190_pdf",
    "generate_modelo_347_pdf",
    "generate_modelo_349_pdf",
    "generate_modelo_390_pdf",
    "generate_fiscal_report_pdf",
    "save_fiscal_report_to_db",
]
