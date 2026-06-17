"""Bulk CSV import endpoints for employees, clients and products.

Capa de transporte: parsea el body, delega al servicio
`services.migration.bulk_import` y serializa el `BulkImportResult`.
Cero lógica de negocio aquí.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_role
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

# SEC.RBAC — importación masiva = operación de administración (puede crear/mutar
# en bloque empleados, clientes, facturas, movimientos bancarios). Todo el router
# exige rol admin; un usuario normal autenticado no debe poder importar en masa.
router = APIRouter(
    prefix="/import",
    tags=["import"],
    dependencies=[Depends(require_role("admin"))],
)


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


# ── Bank statement Norma 43 (AEB) ─────────────────────────────────────────────


class N43ImportResult(MigrationImportResult):
    """Resultado del import N43: además del import idempotente, informa
    cuántos movimientos quedaron conciliados automáticamente."""

    reconciled: int


@router.post("/bank-statement-n43", response_model=N43ImportResult)
async def import_bank_statement_n43(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Importa un extracto bancario en formato Norma 43 (Cuaderno 43 AEB).

    Valida los registros de control (33), importa idempotente por
    (fecha, importe, concepto, saldo) y lanza la auto-conciliación.
    """
    from app.services.banking.parsers.norma43 import (
        Norma43Error,
        norma43_to_rows,
        parse_norma43,
    )
    from app.services.banking.service import auto_reconcile

    content = await file.read()
    try:
        accounts = parse_norma43(content)
    except Norma43Error as e:
        raise HTTPException(status_code=422, detail=f"Fichero N43 inválido: {e}") from e

    rows = norma43_to_rows(accounts)
    result = await import_bank_transactions_rows(rows, current_user.tenant_id, db)

    reconciled = 0
    unmatched = 0
    if result.created:
        recon = await auto_reconcile(db, current_user.tenant_id, current_user.id)
        reconciled = recon.get("matched", 0)
        unmatched = max(recon.get("total", 0) - reconciled, 0)

    if result.created:
        from app.services import events_catalog as ev
        from app.services.event_bus import emit_event

        await emit_event(
            db, current_user.tenant_id, current_user.id, ev.N43_IMPORTED,
            {
                "imported": result.created,
                "skipped": result.skipped,
                "reconciled": reconciled,
                "unmatched": unmatched,
            },
        )
        if unmatched:
            await emit_event(
                db, current_user.tenant_id, current_user.id,
                ev.RECONCILIATION_EXCEPTIONS,
                {"unmatched": unmatched, "total": unmatched + reconciled, "source": "n43"},
            )

    return N43ImportResult(
        imported=result.created,
        skipped=result.skipped,
        reconciled=reconciled,
        errors=result.errors,
    )
