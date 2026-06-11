"""
pdf_reports package — re-exports all public generate_* functions
for backward compatibility with ``from app.services.pdf_reports import ...``.
"""

from app.services.pdf_reports._fiscal import (
    generate_fiscal_report_pdf,
    generate_modelo_100_pdf,
    generate_modelo_111_pdf,
    generate_modelo_115_pdf,
    generate_modelo_130_pdf,
    generate_modelo_190_pdf,
    generate_modelo_200_pdf,
    generate_modelo_303_pdf,
    generate_modelo_347_pdf,
    generate_modelo_349_pdf,
    generate_modelo_390_pdf,
    save_fiscal_report_to_db,
)
from app.services.pdf_reports._operational import (
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
    generate_rgpd_registry_pdf,
)
from app.services.pdf_reports._snapshot import (
    generate_snapshot_pdf,
    generate_text_report_pdf,
)
from app.services.pdf_reports._snapshot_monthly import _snapshot_text_fallback  # noqa: F401

__all__ = [
    "generate_text_report_pdf",
    "generate_snapshot_pdf",
    "_snapshot_text_fallback",
    "generate_modelo_303_pdf",
    "generate_modelo_100_pdf",
    "generate_modelo_130_pdf",
    "generate_modelo_111_pdf",
    "generate_modelo_115_pdf",
    "generate_modelo_190_pdf",
    "generate_modelo_200_pdf",
    "generate_modelo_347_pdf",
    "generate_modelo_349_pdf",
    "generate_modelo_390_pdf",
    "generate_fiscal_report_pdf",
    "generate_rgpd_registry_pdf",
    "generate_cashflow_report_pdf",
    "generate_delinquency_report_pdf",
    "save_fiscal_report_to_db",
]
