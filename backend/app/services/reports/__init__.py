"""Reports domain services — aggregation, fiscal, cashflow, delinquency."""

from app.services.reports.aggregation import (
    aggregate,
    build_report_text,
    parse_month,
    parse_period,
)
from app.services.reports.cashflow import build_cashflow_data
from app.services.reports.delinquency import build_delinquency_data
from app.services.reports.fiscal import (
    aggregate_fiscal,
    build_libro_registro_csv,
    build_modelo_303_data,
)
from app.services.reports.summaries import (
    generate_resumen_ejecutivo,
    generate_resumen_fiscal,
)

__all__ = [
    "aggregate",
    "aggregate_fiscal",
    "build_cashflow_data",
    "build_delinquency_data",
    "build_libro_registro_csv",
    "build_modelo_303_data",
    "build_report_text",
    "generate_resumen_ejecutivo",
    "generate_resumen_fiscal",
    "parse_month",
    "parse_period",
]
