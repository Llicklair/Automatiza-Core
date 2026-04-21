"""
ERP data export tools for the Excel agent.
Handles export_erp_data and list_available_datasets.
"""

import logging
import os
import uuid
from datetime import datetime, timezone

from langchain_core.tools import tool

from app.db.base import AsyncSessionLocal
from app.db.models.tenant import TenantDocument

from ._fetchers import _FETCHER_MAP, _detect_datasets
from ._writer import _write_excel

logger = logging.getLogger(__name__)

UPLOADS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "uploads"))
os.makedirs(UPLOADS_DIR, exist_ok=True)


@tool
async def export_erp_data(tenant_id: str, datasets: str = "todos", user_request: str = "") -> str:
    """
    Exporta datos del ERP a un archivo Excel formateado (.xlsx).
    Genera un archivo con hojas separadas por cada tipo de dato solicitado.

    Args:
        tenant_id: ID del tenant
        datasets: Tipos de datos a exportar, separados por coma.
                  Opciones: facturas, clientes, empleados, nominas, productos, banco.
                  Ejemplo: "facturas,nominas" o "todos" para exportar todo.
        user_request: El mensaje original del usuario (para detectar datasets que falten).
    """
    return await _export_erp_data_async(tenant_id, datasets, user_request)


async def _export_erp_data_async(tenant_id: str, datasets_str: str, user_request: str = "") -> str:
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_filename = f"informe_{ts}.xlsx"
    output_path = os.path.join(UPLOADS_DIR, output_filename)

    if datasets_str.strip().lower() == "todos":
        dataset_keys = list(_FETCHER_MAP.keys())
    else:
        raw_keys = [d.strip().lower() for d in datasets_str.split(",")]
        dataset_keys = []
        for key in raw_keys:
            if key in _FETCHER_MAP:
                dataset_keys.append(key)
            else:
                detected = _detect_datasets(key)
                for dk in detected:
                    if dk not in dataset_keys:
                        dataset_keys.append(dk)

        if user_request:
            from_intent = _detect_datasets(user_request)
            for dk in from_intent:
                if dk not in dataset_keys:
                    logger.info("Dataset '%s' detectado del prompt original, añadiendo", dk)
                    dataset_keys.append(dk)

    sheets = {}
    for key in dataset_keys:
        fetcher = _FETCHER_MAP.get(key)
        if fetcher:
            df = await fetcher(tenant_id)
            sheets[key.capitalize()] = df

    if not sheets:
        return f"Error: No se reconocieron los datasets '{datasets_str}'. Opciones: {', '.join(_FETCHER_MAP.keys())}"

    from app.services.template_service import get_default_theme

    _theme = None
    try:
        async with AsyncSessionLocal() as _db:
            _theme = await get_default_theme(uuid.UUID(tenant_id), "excel", _db)
    except Exception as _e:
        logger.warning("Error cargando tema Excel para tenant %s: %s", tenant_id, _e)

    _write_excel(sheets, output_path, theme=_theme)

    async with AsyncSessionLocal() as db:
        doc = TenantDocument(
            tenant_id=uuid.UUID(tenant_id),
            file_name=output_filename,
            file_path=output_path,
            file_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            file_size=os.path.getsize(output_path),
            category="excels",
            status="completed",
            parsed_content=f"Excel exportado: {', '.join(sheets.keys())}",
        )
        db.add(doc)
        await db.commit()

    total_rows = sum(len(df) for df in sheets.values())
    sheet_summary = ", ".join(f"{name} ({len(df)} registros)" for name, df in sheets.items())
    return (
        f"Excel generado correctamente.\n"
        f"Archivo: {output_filename}\n"
        f"Hojas: {sheet_summary}\n"
        f"Total: {total_rows} registros\n"
        f"El archivo está disponible en la sección de Documentos."
    )


@tool
async def list_available_datasets(tenant_id: str) -> str:
    """
    Lista los tipos de datos disponibles para exportar a Excel y cuántos registros tiene cada uno.
    Útil para que el usuario sepa qué puede exportar antes de pedirlo.

    Args:
        tenant_id: ID del tenant
    """
    return await _list_available_datasets_async(tenant_id)


async def _list_available_datasets_async(tenant_id: str) -> str:
    lines = []
    for key, fetcher in _FETCHER_MAP.items():
        try:
            df = await fetcher(tenant_id)
            lines.append(f"- {key}: {len(df)} registros")
        except Exception:
            logger.debug("Error consultando dataset %s", key, exc_info=True)
            lines.append(f"- {key}: error al consultar")
    return "Datasets disponibles para exportar:\n" + "\n".join(lines)
