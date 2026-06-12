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
from app.services.pdf_reports.agent_report import (
    Report,
    render_agent_report,
    render_markdown_report,
)

_logger = logging.getLogger(__name__)


def _resolve_upload_dir(category: str = "") -> str:
    """Devuelve la carpeta donde guardar uploads del tenant.

    Estrategia (en orden):
      1. Si UPLOAD_DIR está definida y NO es la ruta-Linux por defecto
         "/app/uploads" → respeta lo que el operador haya configurado.
      2. En Windows → AppData/Roaming/AutomatizaCore/uploads (carpeta
         estándar de datos de usuario en Electron).
      3. Otros SO → ./uploads relativo al cwd.

    Si se pasa `category`, se crea una subcarpeta sanitizada (letras,
    números, guiones) — los informes acaban en uploads/informes/, los
    contratos en uploads/contratos/, etc.
    """
    env = os.environ.get("UPLOAD_DIR", "").strip()
    if env and env != "/app/uploads":
        upload_dir = env
    elif os.name == "nt":
        from app.core.paths import app_data_dir
        upload_dir = str(app_data_dir("uploads"))
    else:
        upload_dir = os.path.abspath("uploads")

    if category:
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in category.strip().lower())
        safe = safe.strip("_")[:30] or "general"
        upload_dir = os.path.join(upload_dir, safe)

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

        upload_dir = _resolve_upload_dir(category)
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


@tool
async def create_pdf_text_report(
    tenant_id: str,
    title: str,
    body: str,
    author: str = "Asistente IA",
    subtitle: str = "",
    category: str = "informes",
) -> str:
    """
    Genera un informe PDF profesional a partir de un cuerpo en MARKDOWN.

    Más simple que `create_pdf_report` — el LLM solo emite dos strings
    (title y body). Pensado para informes textuales tipo whitepaper o
    estudio de mercado: títulos, párrafos, listas, tablas markdown,
    blockquotes y línea horizontal.

    El cuerpo debe ser MARKDOWN ESTÁNDAR. Soporta:
      - Encabezados: # H1, ## H2, ### H3
      - Párrafos (separados por línea en blanco)
      - Listas con `- ` o `* ` o numeradas `1. `
      - **negrita**, *cursiva*, `código en línea`
      - Tablas markdown:
            | Columna A | Columna B |
            |-----------|-----------|
            | dato 1    | dato 2    |
      - Blockquote con `>`
      - Línea horizontal con `---`

    Para informes con KPIs en tarjetas o gráficos usa `create_pdf_report`
    (esquema JSON estructurado, requiere provider con function calling).

    Args:
        tenant_id: ID del tenant
        title: Título del informe (aparece en portada y nombre del archivo)
        body: Cuerpo en markdown
        author: Quién firma el informe (rol o nombre)
        subtitle: Subtítulo opcional para la portada
        category: Categoría en el Gestor (default: "informes")
    """
    if not title or not title.strip():
        return "Error: 'title' no puede estar vacío."
    if not body or not body.strip():
        return "Error: 'body' no puede estar vacío. Pasa al menos un párrafo en markdown."

    try:
        async with AsyncSessionLocal() as db:
            t_res = await db.execute(
                select(Tenant.name, Tenant.logo_path).where(Tenant.id == UUID(tenant_id))
            )
            row = t_res.first()
            tenant_name = (row[0] if row else None) or ""
            logo_path = row[1] if row else None

        try:
            pdf_bytes = render_markdown_report(
                title=title,
                body=body,
                author=author or "Asistente IA",
                subtitle=subtitle.strip() or None,
                tenant_name=tenant_name,
                logo_path=logo_path,
            )
        except RuntimeError as e:
            return f"Error generando PDF: {e}"

        upload_dir = _resolve_upload_dir(category)
        slug = _slugify(title)

        # Dedup en ventana corta: cuando el orchestrator decompone una
        # petición unitaria de "informe PDF" en multi-agents, los sub-agents
        # pueden llamar la tool con títulos LIGERAMENTE distintos (ej:
        # "Q1 2026" vs "Q1-Q2 2026") en pocos segundos. Si ya hay CUALQUIER
        # PDF de la misma categoría para el mismo tenant en los últimos 90s,
        # sobrescribimos ese archivo y reusamos la fila — el segundo
        # contenido del LLM suele ser más completo que el primero.
        from datetime import timedelta
        async with AsyncSessionLocal() as db:
            cutoff = datetime.now() - timedelta(seconds=90)
            recent = await db.execute(
                select(TenantDocument)
                .where(
                    TenantDocument.tenant_id == UUID(tenant_id),
                    TenantDocument.category == category,
                    TenantDocument.file_type == "application/pdf",
                    TenantDocument.created_at >= cutoff,
                )
                .order_by(TenantDocument.created_at.desc())
                .limit(1)
            )
            existing = recent.scalars().first()

        # task_id del contexto async actual — permite que el guard cross-dispatcher
        # de create_document detecte que ya hay un documento de esta task y no
        # duplique con un .md.
        from app.core.tenant_context import get_current_task
        current_task_id = get_current_task()
        task_uuid = UUID(current_task_id) if current_task_id else None

        if existing:
            file_path = existing.file_path
            file_name = existing.file_name
            with open(file_path, "wb") as f:
                f.write(pdf_bytes)
            async with AsyncSessionLocal() as db:
                # refresh tamaño/timestamp + task_id si aún no estaba seteado
                from sqlalchemy import update
                values = {"file_size": len(pdf_bytes), "processed_at": datetime.now()}
                if task_uuid is not None and existing.task_id is None:
                    values["task_id"] = task_uuid
                await db.execute(
                    update(TenantDocument)
                    .where(TenantDocument.id == existing.id)
                    .values(**values)
                )
                await db.commit()
            return (
                f"Informe PDF '{file_name}' actualizado (dedup). "
                f"ID: {existing.id} en la categoría '{category}'. "
                f"{len(pdf_bytes)} bytes."
            )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{slug}_{ts}.pdf"
        file_path = os.path.join(upload_dir, file_name)
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)

        async with AsyncSessionLocal() as db:
            doc = TenantDocument(
                tenant_id=UUID(tenant_id),
                task_id=task_uuid,
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
            f"{len(pdf_bytes)} bytes."
        )
    except Exception as e:
        _logger.exception("Error creando PDF text report")
        return f"Error creando el informe: {e}"
