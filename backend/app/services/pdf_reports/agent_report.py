"""Fachada del renderer de informes PDF (compatibilidad de imports).

Implementación dividida en:
- ``_structured.py``: informe estructurado (objeto ``Report`` → flowables ReportLab).
- ``_markdown.py``: informe desde markdown (markdown-it → HTML → xhtml2pdf).
"""

from app.services.pdf_reports._markdown import render_markdown_report
from app.services.pdf_reports._structured import (
    Callout,
    ChartData,
    ChartSeries,
    Kpi,
    Report,
    Section,
    TableData,
    render_agent_report,
)

__all__ = [
    "Callout",
    "ChartData",
    "ChartSeries",
    "Kpi",
    "Report",
    "Section",
    "TableData",
    "render_agent_report",
    "render_markdown_report",
]
