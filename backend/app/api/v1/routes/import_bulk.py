"""Bulk CSV import endpoints for employees, clients and products.

Capa de transporte: parsea el body, delega al servicio
`services.migration.bulk_import` y serializa el `BulkImportResult`.
Cero lógica de negocio aquí.
"""
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.services.migration.bulk_import import (
    BulkImportResult,
    import_clients_rows,
    import_employees_rows,
    import_products_rows,
)

router = APIRouter(prefix="/import", tags=["import"])


class ImportResult(BaseModel):
    """Respuesta HTTP del bulk import. Mantiene el contrato histórico
    (`imported`, `errors`) que ya consumen el frontend y los tests.
    """

    imported: int
    errors: list[dict[str, Any]]


def _to_response(result: BulkImportResult) -> ImportResult:
    return ImportResult(imported=result.created, errors=result.errors)


# ── Employees ─────────────────────────────────────────────────────────────────

@router.post("/employees", response_model=ImportResult)
async def import_employees(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = body.get("rows", [])
    result = await import_employees_rows(rows, current_user.tenant_id, db)
    return _to_response(result)


# ── Clients ───────────────────────────────────────────────────────────────────

@router.post("/clients", response_model=ImportResult)
async def import_clients(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = body.get("rows", [])
    result = await import_clients_rows(rows, current_user.tenant_id, db)
    return _to_response(result)


# ── Products ──────────────────────────────────────────────────────────────────

@router.post("/products", response_model=ImportResult)
async def import_products(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    rows = body.get("rows", [])
    result = await import_products_rows(rows, current_user.tenant_id, db)
    return _to_response(result)
