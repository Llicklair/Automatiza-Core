"""Importación y clasificación de archivos tabulares (CSV, Excel, JSON)."""

import json as json_mod
import logging
import os
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Task, TenantDocument
from app.services.documents._file_ops import save_file_to_disk

logger = logging.getLogger(__name__)


def parse_tabular_file(file_path: str, file_name: str) -> tuple[list[str], list[dict], str]:
    """Parsea archivo tabular. Retorna (columnas, filas, formato). Soporta csv/xlsx/xls/json/ods."""
    ext = os.path.splitext(file_name)[1].lower()

    if ext == ".csv":
        import csv

        with open(file_path, encoding="utf-8", errors="replace") as f:
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            reader = csv.DictReader(f, dialect=dialect)
            columns = reader.fieldnames or []
            rows = [row for row in reader]
        return columns, rows, "csv"

    elif ext in (".xlsx", ".xls", ".ods"):
        import openpyxl

        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        rows_raw = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows_raw:
            return [], [], "excel"
        columns = [str(c) if c else f"col_{i}" for i, c in enumerate(rows_raw[0])]
        rows = [
            {columns[j]: cell for j, cell in enumerate(row) if j < len(columns)}
            for row in rows_raw[1:]
        ]
        return columns, rows, "excel"

    elif ext == ".json":
        with open(file_path, encoding="utf-8") as f:
            data = json_mod.load(f)
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            columns = list(data[0].keys())
            return columns, data, "json"
        elif isinstance(data, dict):
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    columns = list(val[0].keys())
                    return columns, val, "json"
            columns = list(data.keys())
            return columns, [data], "json"
        return [], [], "json"

    return [], [], "unknown"


def auto_classify_tabular(columns: list[str]) -> str:
    """Clasifica categoría de un archivo tabular por nombres de columnas."""
    cols_lower = " ".join(c.lower() for c in columns)
    if any(k in cols_lower for k in ("factura", "invoice", "importe", "iva", "nif_cliente")):
        return "facturas"
    if any(k in cols_lower for k in ("nomina", "salario", "sueldo", "empleado", "payroll")):
        return "nominas"
    if any(k in cols_lower for k in ("correo", "email", "asunto", "subject", "inbox", "bandeja")):
        return "correos"
    if any(
        k in cols_lower for k in ("cliente", "customer", "telefono", "empresa", "lead", "contacto")
    ):
        return "crm"
    if any(k in cols_lower for k in ("banco", "iban", "movimiento", "saldo", "transferencia")):
        return "bancos"
    if any(k in cols_lower for k in ("producto", "articulo", "precio", "stock", "referencia")):
        return "crm"
    if any(k in cols_lower for k in ("contrato", "alta", "baja", "puesto", "departamento")):
        return "rrhh"
    if any(k in cols_lower for k in ("impuesto", "modelo", "trimestre", "declaracion")):
        return "fiscal"
    return "excels"


async def import_tabular_file(
    filename: str,
    contents: bytes,
    content_type: str | None,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> tuple[TenantDocument, list[str], int, str, uuid.UUID | None]:
    """Importa un archivo tabular. Retorna (doc, columns, row_count, auto_cat, task_id)."""
    ext = os.path.splitext(filename)[1].lower()
    file_path = save_file_to_disk(contents, ext)

    try:
        columns, rows, fmt = parse_tabular_file(file_path, filename)
    except Exception:
        columns, rows, fmt = [], [], "error"

    auto_cat = auto_classify_tabular(columns)

    doc = TenantDocument(
        tenant_id=tenant_id,
        uploaded_by=user_id,
        file_name=filename,
        file_type=content_type or "application/octet-stream",
        file_path=file_path,
        file_size=len(contents),
        category=auto_cat,
        status="uploaded",
        parsed_content=json_mod.dumps(
            {"format": fmt, "columns": columns, "row_count": len(rows), "sample_rows": rows[:5]},
            ensure_ascii=False,
            default=str,
        ),
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    task_id = None
    try:
        from app.services.workflow.task_dispatch import dispatch_orchestrator

        intent_summary = (
            f"Importar base de datos '{filename}' ({len(rows)} filas, "
            f"columnas: {', '.join(columns[:10])}). "
            f"Clasificar y crear los registros correspondientes en el sistema "
            f"(clientes, facturas, empleados, productos, etc. según el contenido)."
        )
        task = Task(
            tenant_id=tenant_id,
            created_by=user_id,
            domain="excel",
            user_intent=intent_summary,
            status="pending",
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        doc.task_id = task.id
        doc.status = "processing"
        await db.commit()
        await db.refresh(doc)
        task_id = task.id

        # Fase 3 (RLS): propagamos tenant_id al worker.
        await dispatch_orchestrator(str(task.id), tenant_id=str(tenant_id))
    except Exception as e:
        logger.warning("Orchestrator dispatch falló en import para doc %s: %s", doc.id, e)

    return doc, columns[:20], len(rows), auto_cat, task_id
