"""Rutas RRHH — gastos de empleados."""

import asyncio
import logging
from pathlib import Path
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import ExpenseCreate
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.hr import service as svc

router = APIRouter(tags=["hr"])


# ─── Expenses ─────────────────────────────────────────────────────────────────


@router.get("/expenses")
@limiter.limit("30/minute")
async def list_expenses(
    request: Request,
    status_filter: str | None = None,
    employee_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    eid = UUID(employee_id) if employee_id else None
    return await svc.list_expenses(db, current_user.tenant_id, status_filter, eid)


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_expense(
    request: Request,
    payload: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = await svc.create_expense(
        db, current_user.tenant_id, payload.employee_id,
        payload.amount, payload.category, payload.description, payload.date, payload.notes,
    )
    return _expense_row(exp)


@router.post("/expenses/scan", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def scan_expense_receipt(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """OCR + IA: extrae datos de un ticket y devuelve un borrador de gasto.

    No crea nada en BD. El frontend muestra el borrador para que el usuario
    revise/edite antes de llamar a POST /expenses para confirmar.
    """
    from app.services.ocr import ReceiptExtractionError, extract_receipt_data
    from app.services.ocr._upload_validation import (
        RECEIPT_EXTENSIONS,
        validate_ocr_upload,
    )

    validate_ocr_upload(file, RECEIPT_EXTENSIONS)
    content = await file.read()
    mime = file.content_type or "image/jpeg"
    try:
        data = await extract_receipt_data(content, mime)
    except ReceiptExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as exc:
        logging.getLogger(__name__).exception("Fallo procesando ticket")
        raise HTTPException(status_code=500, detail="Error al procesar el ticket") from exc
    return data.to_dict()


@router.post("/expenses/{expense_id}/approve")
@limiter.limit("30/minute")
async def approve_expense(
    request: Request,
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        exp = await svc.approve_expense(db, current_user.tenant_id, expense_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _expense_row(exp)


@router.post("/expenses/{expense_id}/reject")
@limiter.limit("30/minute")
async def reject_expense(
    request: Request,
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        exp = await svc.reject_expense(db, current_user.tenant_id, expense_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _expense_row(exp)


@router.post("/expenses/{expense_id}/reimburse")
@limiter.limit("30/minute")
async def reimburse_expense(
    request: Request,
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        exp = await svc.reimburse_expense(db, current_user.tenant_id, expense_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _expense_row(exp)


@router.post("/expenses/{expense_id}/receipt", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def upload_expense_receipt(
    request: Request,
    expense_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        exp = await svc.upload_expense_receipt(
            db, current_user.tenant_id, expense_id, content, file.filename or "recibo"
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return _expense_row(exp)


@router.get("/expenses/{expense_id}/receipt")
@limiter.limit("30/minute")
async def download_expense_receipt(
    request: Request,
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.get_expense_receipt_path(db, current_user.tenant_id, expense_id)
    if not result:
        raise HTTPException(status_code=404, detail="Recibo no encontrado")
    path, filename = result
    if not __import__("os").path.exists(path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    import mimetypes
    mime, _ = mimetypes.guess_type(filename)
    content = await asyncio.to_thread(Path(path).read_bytes)
    return Response(
        content=content,
        media_type=mime or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/expenses/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_expense(
    request: Request,
    expense_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_expense(db, current_user.tenant_id, expense_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


def _expense_row(exp) -> dict:
    return {
        "id": str(exp.id),
        "employee_id": str(exp.employee_id),
        "employee_name": exp.employee.name if exp.employee else None,
        "amount": float(exp.amount),
        "category": exp.category,
        "description": exp.description,
        "date": exp.date.isoformat() if exp.date else None,
        "status": exp.status,
        "receipt_filename": exp.receipt_filename,
        "notes": exp.notes,
        "created_at": exp.created_at.isoformat() if exp.created_at else None,
    }
