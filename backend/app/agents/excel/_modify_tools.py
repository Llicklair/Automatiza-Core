"""
Excel modification and reading tools for the Excel agent.
Handles modify_excel and read_excel.
"""

import json
import logging
import os
import uuid

import openpyxl
from langchain_core.tools import tool
from sqlalchemy.future import select

from app.db.base import AsyncSessionLocal
from app.db.models.tenant import TenantDocument

from ._import_tools import _load_excel_doc

logger = logging.getLogger(__name__)


# ─── Private helpers ──────────────────────────────────────────────────────────


def _parse_mods_json(modifications_json: str) -> list | str:
    """Parsea el JSON de modificaciones. Devuelve la lista o un mensaje de error."""
    try:
        mods = json.loads(modifications_json)
    except (json.JSONDecodeError, TypeError):
        return 'Error: El formato de modificaciones no es JSON válido. Ejemplo: [{"cell": "B3", "value": 1500}]'
    if not isinstance(mods, list):
        return "Error: Las modificaciones deben ser una lista JSON."
    return mods


def _apply_mods_to_workbook(wb, mods: list, default_sheet: str) -> tuple[int, list[str]]:
    """Aplica una lista de modificaciones a un workbook openpyxl. Devuelve (applied, errors)."""
    applied, errors = 0, []
    for mod in mods:
        cell_ref = mod.get("cell", "")
        value = mod.get("value")
        sheet = mod.get("sheet", default_sheet or wb.sheetnames[0])
        if not cell_ref:
            errors.append("Modificación sin 'cell' especificada.")
            continue
        if sheet not in wb.sheetnames:
            errors.append(f"Hoja '{sheet}' no existe. Disponibles: {', '.join(wb.sheetnames)}")
            continue
        try:
            wb[sheet][cell_ref] = value
            applied += 1
        except Exception as e:
            errors.append(f"Error en {sheet}!{cell_ref}: {e}")
    return applied, errors


# ─── Tools ────────────────────────────────────────────────────────────────────


@tool
async def modify_excel(
    tenant_id: str,
    document_id: str,
    modifications: str = "",
    sheet_name: str = "",
) -> str:
    """
    Modifica celdas de un archivo Excel existente. Acepta instrucciones en formato JSON.
    Cada modificación especifica hoja (opcional), celda y nuevo valor.

    Args:
        tenant_id: ID del tenant
        document_id: ID del documento Excel a modificar (usar list_tenant_documents para obtenerlo)
        modifications: JSON con las modificaciones. Formato:
            [{"cell": "B3", "value": 1500}, {"cell": "A1", "value": "Nuevo título"}]
            o con hoja: [{"sheet": "Facturas", "cell": "C5", "value": 2000}]
        sheet_name: Hoja por defecto donde aplicar modificaciones (vacío = primera hoja)
    """
    return await _modify_excel_async(tenant_id, document_id, modifications, sheet_name)


async def _modify_excel_async(
    tenant_id: str,
    document_id: str,
    modifications_json: str,
    default_sheet: str,
) -> str:
    try:
        doc, err = await _load_excel_doc(tenant_id, document_id)
        if err:
            return err

        mods = _parse_mods_json(modifications_json)
        if isinstance(mods, str):
            return mods

        wb = openpyxl.load_workbook(doc.file_path)
        applied, errors = _apply_mods_to_workbook(wb, mods, default_sheet)
        wb.save(doc.file_path)
        wb.close()

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(TenantDocument).where(TenantDocument.id == uuid.UUID(document_id)))
            doc_upd = result.scalar_one_or_none()
            if doc_upd:
                doc_upd.file_size = os.path.getsize(doc.file_path)
                await db.commit()

        result_lines = ["Excel modificado correctamente.", f"Celdas actualizadas: {applied}"]
        if errors:
            result_lines.append(f"Errores: {'; '.join(errors[:5])}")
        return "\n".join(result_lines)
    except Exception as e:
        return f"Error modificando Excel: {e}"


@tool
async def read_excel(tenant_id: str, document_id: str, sheet_name: str = "", max_rows: int = 30) -> str:
    """
    Lee el contenido de un archivo Excel y lo devuelve en formato texto tabular.
    Útil para que el LLM vea los datos antes de decidir qué modificar.

    Args:
        tenant_id: ID del tenant
        document_id: ID del documento Excel
        sheet_name: Nombre de la hoja a leer (vacío = primera hoja)
        max_rows: Máximo de filas a devolver (por defecto 30)
    """
    return await _read_excel_async(tenant_id, document_id, sheet_name, max_rows)


async def _read_excel_async(tenant_id: str, document_id: str, sheet_name: str, max_rows: int) -> str:
    try:
        doc, err = await _load_excel_doc(tenant_id, document_id)
        if err:
            return err

        wb = openpyxl.load_workbook(doc.file_path, read_only=True, data_only=True)

        if sheet_name:
            if sheet_name not in wb.sheetnames:
                wb.close()
                return f"Error: Hoja '{sheet_name}' no encontrada. Disponibles: {', '.join(wb.sheetnames)}"
            ws = wb[sheet_name]
        else:
            ws = wb.active

        sheet_title = ws.title
        available_sheets = ", ".join(wb.sheetnames)
        rows = list(ws.iter_rows(values_only=True, max_row=max_rows + 1))
        wb.close()

        if not rows:
            return f"La hoja '{sheet_title}' está vacía."

        lines = [f"Hoja: {sheet_title} | Hojas disponibles: {available_sheets}"]
        for i, row in enumerate(rows):
            prefix = "HDR" if i == 0 else f"R{i}"
            cells = [str(c) if c is not None else "" for c in row]
            lines.append(f"  {prefix}: {' | '.join(cells)}")

        if len(rows) > max_rows:
            lines.append(f"  ... (mostrando {max_rows} de las filas disponibles)")

        return "\n".join(lines)
    except Exception as e:
        return f"Error leyendo Excel: {e}"
