"""
Tool compartida para que los agentes IA generen informes PDF profesionales.

El agente devuelve un JSON Report (validado con Pydantic) y la tool lo
renderiza con la paleta corporativa, lo persiste en disco y crea la
fila correspondiente en TenantDocument para que aparezca en el Gestor.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from uuid import UUID

from langchain_core.tools import tool
from pydantic import ValidationError
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.auth import Tenant
from app.db.models.models import TenantDocument
from app.services.pdf_reports.agent_report import Report, render_agent_report

_logger = logging.getLogger(__name__)


def _resolve_upload_dir() -> str:
    upload_dir = os.environ.get("UPLOAD_DIR", "/app/uploads")
    if not os.path.exists(upload_dir) and os.name == "nt":
        upload_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads")
        )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def _slugify(text: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in text.strip())
    return safe[:60] or "informe"


@tool
async def create_pdf_report(
    tenant_id: str, report: dict | str, category: str = "informes"
) -> str:
    """
    Genera un informe PDF profesional a partir de un objeto Report en JSON.
    Útil para entregar análisis profundos con KPIs, tablas, callouts y gráficos.

    El JSON debe seguir este esquema:
      {
        "title": "Análisis de tesorería Q1 2026",
        "subtitle": "Liquidez, gastos y proyección",  // opcional
        "author": "Asistente Financiero",
        "sections": [
          {
            "heading": "Liquidez",
            "body": "Texto del análisis en párrafos separados por \\n\\n.",
            "kpis": [
              {"label": "Caja", "value": "82.300 €", "trend": "up", "delta": "+15% vs Q4"}
            ],
            "table": {
              "columns": ["Cuenta", "Saldo"],
              "rows": [["BBVA", "50.300 €"], ["Santander", "32.000 €"]],
              "caption": "Saldos al cierre"
            },
            "callouts": [
              {"type": "warning", "text": "Vencimientos de IVA próximos."}
            ],
            "chart": {
              "type": "bar",
              "title": "Ingresos por mes",
              "labels": ["Ene", "Feb", "Mar"],
              "series": [{"name": "Ingresos", "values": [12000, 15000, 18000]}]
            }
          }
        ],
        "conclusions": "Cierre del informe en 1-3 párrafos."  // opcional
      }

    Tipos de gráfico soportados: "bar", "line", "pie".
    Tipos de callout: "info", "warning", "success", "danger".
    Trend de KPI: "up", "down", "flat", "none".

    Args:
        tenant_id: ID del tenant
        report: el objeto Report. Pásalo como dict siguiendo el esquema
            de arriba. Si lo pasas como string también vale (se parsea).
        category: Categoría donde clasificarlo en el Gestor (default: "informes")
    """
    try:
        if isinstance(report, str):
            data = json.loads(report)
        elif isinstance(report, dict):
            data = report
        else:
            return f"Error: 'report' debe ser dict o JSON string, llegó {type(report).__name__}."
        # Algunos modelos envuelven el payload en {"report": {...}} o {"input": {...}}
        if isinstance(data, dict) and len(data) == 1:
            only_key = next(iter(data))
            if only_key in ("report", "input", "data", "payload") and isinstance(data[only_key], dict):
                data = data[only_key]
        report = Report.model_validate(data)
    except json.JSONDecodeError as e:
        return f"Error: el string no es JSON válido. Detalle: {e}"
    except ValidationError as e:
        return f"Error: el objeto no cumple el esquema Report. Detalle: {e}"
    except Exception as e:
        return f"Error procesando report: {e}"

    try:
        async with AsyncSessionLocal() as db:
            t_res = await db.execute(
                select(Tenant.name, Tenant.logo_path).where(Tenant.id == UUID(tenant_id))
            )
            row = t_res.first()
            tenant_name = (row[0] if row else None) or ""
            logo_path = row[1] if row else None

        try:
            pdf_bytes = render_agent_report(
                report, tenant_name=tenant_name, logo_path=logo_path
            )
        except RuntimeError as e:
            return f"Error generando PDF: {e}"

        upload_dir = _resolve_upload_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{_slugify(report.title)}_{ts}.pdf"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            doc = TenantDocument(
                tenant_id=UUID(tenant_id),
                file_name=file_name,
                file_path=file_path,
                file_type="application/pdf",
                file_size=len(pdf_bytes),
                category=category,
                status="completed",
                parsed_content=None,
            )
            db.add(doc)
            await db.commit()
            await db.refresh(doc)

        return (
            f"Informe PDF '{file_name}' generado correctamente. "
            f"ID: {doc.id} en la categoría '{category}'. "
            f"{len(report.sections)} secciones, {len(pdf_bytes)} bytes."
        )
    except Exception as e:
        _logger.exception("Error creando PDF report")
        return f"Error creando el informe: {e}"
