"""Integración de archivos tabulares (Excel/CSV/JSON) → entidades del ERP.

A diferencia del importador del agente (`agents/excel/_import_tools.py`, que
persiste a ciegas con salida de texto), esto ofrece **preview + commit** para
que el usuario revise antes de crear nada:

  - `preview_import(...)` → mapea columnas a campos del modelo, detecta el
    target, y devuelve una muestra + cuántas filas son importables. NO escribe.
  - `apply_import(...)` → crea los registros (Product/Client/Employee) en una
    sola transacción. Salta filas sin los campos requeridos.

Targets soportados: productos, clientes (incl. proveedores), empleados.
Todos requieren solo `name`; el resto de campos son opcionales.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from sqlalchemy import select

from app.db.models.crm import Client
from app.db.models.hr import Employee
from app.db.models.inventory import Product
from app.db.models.tenant import TenantDocument
from app.services.documents._tabular import parse_tabular_file

logger = logging.getLogger(__name__)

# header (en minúsculas) → campo del modelo
IMPORT_TARGETS: dict[str, dict] = {
    "productos": {
        "label": "Productos (catálogo)",
        "model": Product,
        "fields": {
            "nombre": "name",
            "name": "name",
            "producto": "name",
            "articulo": "name",
            "artículo": "name",
            "descripcion": "description",
            "descripción": "description",
            "description": "description",
            "sku": "sku",
            "referencia": "sku",
            "ref": "sku",
            "codigo": "sku",
            "código": "sku",
            "barcode": "barcode",
            "ean": "barcode",
            "codigo de barras": "barcode",
            "precio": "price",
            "pvp": "price",
            "price": "price",
            "precio venta": "price",
            "coste": "cost_price",
            "costo": "cost_price",
            "cost": "cost_price",
            "precio coste": "cost_price",
            "iva": "tax_percentage",
            "tax": "tax_percentage",
            "impuesto": "tax_percentage",
            "stock": "stock_quantity",
            "existencias": "stock_quantity",
            "cantidad": "stock_quantity",
            "categoria": "category",
            "categoría": "category",
            "category": "category",
            "ubicacion": "location",
            "ubicación": "location",
            "location": "location",
            "unidad": "unit",
            "unit": "unit",
        },
        "required": ["name"],
        "numeric": {"price", "cost_price", "tax_percentage"},
        "integer": {"stock_quantity"},
    },
    "clientes": {
        "label": "Clientes / Proveedores",
        "model": Client,
        "fields": {
            "nombre": "name",
            "name": "name",
            "cliente": "name",
            "empresa": "name",
            "razon social": "name",
            "razón social": "name",
            "nif": "nif",
            "cif": "nif",
            "dni": "nif",
            "email": "email",
            "correo": "email",
            "e-mail": "email",
            "telefono": "phone",
            "teléfono": "phone",
            "phone": "phone",
            "tel": "phone",
            "movil": "phone",
            "móvil": "phone",
            "direccion": "address",
            "dirección": "address",
            "address": "address",
            "ciudad": "city",
            "city": "city",
            "poblacion": "city",
            "población": "city",
            "cp": "postal_code",
            "codigo postal": "postal_code",
            "código postal": "postal_code",
            "postal_code": "postal_code",
        },
        "required": ["name"],
        "numeric": set(),
        "integer": set(),
    },
    "empleados": {
        "label": "Empleados",
        "model": Employee,
        "fields": {
            "nombre": "name",
            "name": "name",
            "empleado": "name",
            "nif": "nif",
            "dni": "nif",
            "email": "email",
            "correo": "email",
            "telefono": "phone",
            "teléfono": "phone",
            "phone": "phone",
            "cargo": "role",
            "puesto": "role",
            "role": "role",
            "departamento": "department",
            "department": "department",
            "salario": "base_salary",
            "salario base": "base_salary",
            "salario_base": "base_salary",
            "base_salary": "base_salary",
            "sueldo": "base_salary",
        },
        "required": ["name"],
        "numeric": {"base_salary"},
        "integer": set(),
    },
}


def _to_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("€", "").replace("%", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")  # 1.234,56 → 1234.56
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _coerce(field: str, value: Any, config: dict) -> Any:
    if field in config["integer"]:
        n = _to_number(value)
        return int(round(n)) if n is not None else None
    if field in config["numeric"]:
        return _to_number(value)
    s = str(value).strip()
    return s[:200] if field == "name" else (s or None)


def _norm_headers(columns: list[str]) -> dict[str, str]:
    """{header_original: header_normalizado_minúsculas}."""
    return {c: str(c).strip().lower() for c in columns}


def _detect_target(columns: list[str]) -> str | None:
    """Elige el target con más columnas reconocidas (mín. 1 + el requerido)."""
    norm = list(_norm_headers(columns).values())
    best, best_score = None, 0
    for key, cfg in IMPORT_TARGETS.items():
        matched = {cfg["fields"][h] for h in norm if h in cfg["fields"]}
        if not all(r in matched for r in cfg["required"]):
            continue
        if len(matched) > best_score:
            best, best_score = key, len(matched)
    return best


def _map_record(row: dict, header_norm: dict[str, str], config: dict) -> dict:
    record: dict = {}
    for orig, norm in header_norm.items():
        field = config["fields"].get(norm)
        if not field or field in record:
            continue
        coerced = _coerce(field, row.get(orig), config)
        if coerced is not None:
            record[field] = coerced
    return record


async def _load_doc(db, tenant_id, document_id: uuid.UUID) -> TenantDocument:
    res = await db.execute(
        select(TenantDocument).where(TenantDocument.tenant_id == tenant_id, TenantDocument.id == document_id)
    )
    doc = res.scalar_one_or_none()
    if doc is None:
        raise LookupError("Documento no encontrado")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise FileNotFoundError("El archivo ya no está disponible en disco")
    return doc


def _resolve_target(target: str | None, columns: list[str]) -> tuple[str, dict]:
    key = (target or "").strip().lower() or _detect_target(columns) or ""
    if key not in IMPORT_TARGETS:
        raise ValueError("No se pudo determinar el tipo de datos. Indica un target: " + ", ".join(IMPORT_TARGETS))
    return key, IMPORT_TARGETS[key]


async def preview_import(db, tenant_id, document_id: uuid.UUID, target: str | None) -> dict:
    """Mapea columnas y devuelve muestra + recuento. No escribe nada."""
    doc = await _load_doc(db, tenant_id, document_id)
    columns, rows, _ = parse_tabular_file(doc.file_path, doc.file_name)
    if not columns:
        raise ValueError("El archivo no tiene columnas legibles")

    key, config = _resolve_target(target, columns)
    header_norm = _norm_headers(columns)

    mapped_fields = sorted({config["fields"][n] for n in header_norm.values() if n in config["fields"]})
    unmapped = [c for c in columns if header_norm[c] not in config["fields"]]

    sample, importable = [], 0
    for row in rows:
        rec = _map_record(row, header_norm, config)
        ok = all(rec.get(r) for r in config["required"])
        if ok:
            importable += 1
        if len(sample) < 8:
            sample.append({"record": rec, "ok": ok})

    return {
        "target": key,
        "target_label": config["label"],
        "available_targets": [{"key": k, "label": v["label"]} for k, v in IMPORT_TARGETS.items()],
        "columns": columns,
        "mapped_fields": mapped_fields,
        "unmapped_columns": unmapped,
        "total_rows": len(rows),
        "importable": importable,
        "skipped": len(rows) - importable,
        "sample": sample,
    }


async def apply_import(db, tenant_id, document_id: uuid.UUID, target: str | None) -> dict:
    """Crea los registros del target en una sola transacción."""
    doc = await _load_doc(db, tenant_id, document_id)
    columns, rows, _ = parse_tabular_file(doc.file_path, doc.file_name)
    key, config = _resolve_target(target, columns)
    header_norm = _norm_headers(columns)
    model_cls = config["model"]

    created, skipped, errors = 0, 0, []
    for idx, row in enumerate(rows, start=2):  # fila 1 = cabecera
        rec = _map_record(row, header_norm, config)
        if any(not rec.get(r) for r in config["required"]):
            skipped += 1
            continue
        try:
            db.add(model_cls(tenant_id=tenant_id, **rec))
            created += 1
        except Exception as e:  # noqa: BLE001
            errors.append(f"Fila {idx}: {e}")
            skipped += 1

    if created:
        try:
            await db.commit()
        except Exception as e:  # noqa: BLE001
            await db.rollback()
            logger.exception("[ERP-IMPORT] commit falló")
            return {"target": key, "created": 0, "skipped": len(rows), "errors": [str(e)]}

    return {
        "target": key,
        "target_label": config["label"],
        "created": created,
        "skipped": skipped,
        "errors": errors[:10],
    }
