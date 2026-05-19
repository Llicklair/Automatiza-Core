"""Bulk CSV import for employees / clients / products.

Capa de servicio para los endpoints `POST /import/{employees,clients,products}`.
La ruta solo recibe filas, valida transporte y delega aquí. Toda la lógica
(coerción de tipos, instanciación de modelos ORM, persistencia, agregación
de errores) vive en este módulo para que pueda reutilizarse desde un wizard
de onboarding, un workflow batch o tests sin pasar por HTTP.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.crm import Client
from app.db.models.hr import Employee
from app.db.models.inventory import Product


@dataclass
class BulkImportResult:
    """Resultado de un import bulk fila a fila.

    - `created`: filas insertadas con éxito.
    - `errors`: lista de errores estructurados con `row` (1-based, +1 por
      la cabecera) y `reason`.
    - `skipped`: filas saltadas por validación previa (e.g. campo
      obligatorio vacío). NOTA: cada skip también queda registrado en
      `errors` para compatibilidad con la API histórica.
    """

    created: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    skipped: int = 0


def _coerce(value: str | None, typ: type):
    """Convierte `value` al tipo `typ`; devuelve `None` ante error o vacío."""
    if value == "" or value is None:
        return None
    try:
        return typ(value)
    except (ValueError, TypeError):
        return None


async def import_employees_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de empleados. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            emp = Employee(
                tenant_id=tenant_id,
                name=name.strip(),
                nif=row.get("nif") or None,
                email=row.get("email") or None,
                department=row.get("departamento") or row.get("department") or None,
                role=row.get("rol") or row.get("role") or None,
                base_salary=_coerce(row.get("salario_base") or row.get("base_salary") or "", float),
                irpf_rate=_coerce(row.get("irpf") or row.get("irpf_rate") or "", float),
                status=row.get("estado") or row.get("status") or "active",
            )
            db.add(emp)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001 — agregamos al reporte por fila
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def import_clients_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de clientes. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            client = Client(
                tenant_id=tenant_id,
                name=name.strip(),
                nif=row.get("nif") or None,
                email=row.get("email") or None,
                phone=row.get("telefono") or row.get("phone") or None,
                address=row.get("direccion") or row.get("address") or None,
                city=row.get("ciudad") or row.get("city") or None,
                postal_code=row.get("codigo_postal") or row.get("postal_code") or None,
                client_type=row.get("tipo") or row.get("client_type") or "customer",
            )
            db.add(client)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result


async def import_products_rows(
    rows: list[dict[str, str]],
    tenant_id: UUID,
    db: AsyncSession,
) -> BulkImportResult:
    """Persiste filas de productos. Hace `commit` al final."""
    result = BulkImportResult()
    for i, row in enumerate(rows):
        name = row.get("nombre") or row.get("name") or ""
        if not name.strip():
            result.errors.append({"row": i + 2, "reason": "El campo 'nombre' es obligatorio"})
            result.skipped += 1
            continue
        try:
            product = Product(
                tenant_id=tenant_id,
                name=name.strip(),
                sku=row.get("sku") or None,
                description=row.get("descripcion") or row.get("description") or None,
                price=_coerce(row.get("precio") or row.get("price") or "0", float) or 0,
                tax_percentage=_coerce(row.get("iva") or row.get("tax_percentage") or "21", float) or 21.0,
                stock_quantity=_coerce(row.get("stock") or row.get("stock_quantity") or "0", int) or 0,
            )
            db.add(product)
            await db.flush()
            result.created += 1
        except Exception as e:  # noqa: BLE001
            result.errors.append({"row": i + 2, "reason": str(e)[:120]})

    await db.commit()
    return result
