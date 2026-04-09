"""
Servicio de generación de PDFs — re-exportador.

Este módulo mantiene la API pública original re-exportando desde los módulos
especializados. Todos los imports existentes siguen funcionando sin cambios.

Módulos internos:
  _pdf_base.py      — imports reportlab, estilos compartidos, helpers
  pdf_invoices.py   — factura estándar, rectificativa, retención
  pdf_hr.py         — nóminas
  pdf_reports.py    — text_report, snapshot, modelo_303, rgpd, cashflow, morosidad
"""

# ── Utilidades base ──────────────────────────────────────────────────────────
from app.services._pdf_base import (  # noqa: F401
    REPORTLAB_AVAILABLE,
    _common_styles,
    _fmt_eur,
    _make_doc,
    _table_header_style,
    _format_date,
)

# ── Facturación ──────────────────────────────────────────────────────────────
from app.services.pdf_invoices import (  # noqa: F401
    generate_invoice_pdf,
    generate_rectificative_invoice_pdf,
    generate_retention_invoice_pdf,
)

# ── RRHH ─────────────────────────────────────────────────────────────────────
from app.services.pdf_hr import (  # noqa: F401
    generate_payroll_pdf,
    generate_finiquito_pdf,
    generate_liquidacion_finiquito_pdf,
    generate_registro_jornada_pdf,
)

# ── Informes ─────────────────────────────────────────────────────────────────
from app.services.pdf_reports import (  # noqa: F401
    generate_text_report_pdf,
    generate_snapshot_pdf,
    generate_modelo_303_pdf,
    generate_rgpd_registry_pdf,
    generate_cashflow_report_pdf,
    generate_delinquency_report_pdf,
)
