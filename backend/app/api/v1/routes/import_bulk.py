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
    import_bank_transactions_rows,
    import_clients_rows,
    import_employees_rows,
    import_invoices_rows,
    import_payrolls_rows,
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


# ── Payrolls (migración de histórico) ─────────────────────────────────────────


class MigrationImportResult(BaseModel):
    """Import de histórico en migración (nóminas, facturas…). Expone `skipped`
    (ya migradas, idempotencia) además de `imported`/`errors`, porque al migrar
    interesa saber cuántas se omitieron por ya existir."""

    imported: int
    skipped: int
    errors: list[dict[str, Any]]


@router.post("/payrolls", response_model=MigrationImportResult)
async def import_payrolls(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Migra nóminas históricas desde otro programa (preserva importes, no
    recalcula). El empleado debe existir previamente. Idempotente por período."""
    rows = body.get("rows", [])
    result = await import_payrolls_rows(rows, current_user.tenant_id, db)
    return MigrationImportResult(
        imported=result.created, skipped=result.skipped, errors=result.errors
    )


# ── Invoices (migración de histórico) ─────────────────────────────────────────


@router.post("/invoices", response_model=MigrationImportResult)
async def import_invoices(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Migra facturas históricas (emitidas y recibidas) desde otro programa:
    preserva número e importes, no encadena Verifactu ni genera asientos.
    Idempotente. El cliente/proveedor debe existir previamente."""
    rows = body.get("rows", [])
    result = await import_invoices_rows(rows, current_user.tenant_id, db)
    return MigrationImportResult(
        imported=result.created, skipped=result.skipped, errors=result.errors
    )


# ── Bank transactions (migración de extracto) ─────────────────────────────────


@router.post("/bank-transactions", response_model=MigrationImportResult)
async def import_bank_transactions(
    body: dict[str, list[dict[str, str]]],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Carga un extracto bancario histórico (CSV). Importe con signo, movimientos
    sin conciliar. Idempotente por (fecha, importe, concepto[, saldo])."""
    rows = body.get("rows", [])
    result = await import_bank_transactions_rows(rows, current_user.tenant_id, db)
    return MigrationImportResult(
        imported=result.created, skipped=result.skipped, errors=result.errors
    )
