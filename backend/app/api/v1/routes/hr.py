"""Rutas RRHH — thin controller para empleados, nóminas y documentos HR."""

import logging
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    ClockInRequest,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    ExpenseCreate,
    FiniquitoRequest,
    LeaveRequestCreate,
    LiquidacionRequest,
    PayrollCalculateResponse,
    PayrollCreate,
    PayrollResponse,
    PayrollSimpleCreate,
    PayrollUpdate,
    RegistroJornadaRequest,
    ScheduleAISuggestRequest,
    ScheduleUpsert,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.hr import service as svc
from app.services.state_machine import InvalidTransitionError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hr", tags=["hr"])


# ─── Employees ───────────────────────────────────────────────────────────────


@router.get("/employees", response_model=list[EmployeeResponse])
@limiter.limit("30/minute")
async def list_employees(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_employees(current_user.tenant_id, db)


@router.post("/employees", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_employee(
    request: Request,
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.create_employee(payload.model_dump(), current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error("Error guardando empleado: %s", e)
        raise HTTPException(status_code=500, detail="Error al guardar el empleado")


@router.patch("/employees/{employee_id}", response_model=EmployeeResponse)
@limiter.limit("30/minute")
async def update_employee(
    request: Request,
    employee_id: UUID,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = await svc.update_employee(employee_id, payload, current_user.tenant_id, db)
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return emp


@router.delete("/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_employee(
    request: Request,
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_employee(employee_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")


# ─── Payrolls ────────────────────────────────────────────────────────────────


@router.get("/employees/{employee_id}/payroll/preview", response_model=PayrollCalculateResponse)
@limiter.limit("30/minute")
async def preview_payroll(
    request: Request,
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await svc.preview_payroll(employee_id, current_user.tenant_id, db)
        return PayrollCalculateResponse(**result)
    except ValueError as e:
        code = 404 if "no encontrado" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))


@router.post("/payrolls/auto", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def generate_payroll_auto(
    request: Request,
    payload: PayrollSimpleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.create_payroll_auto(payload, current_user.tenant_id, db)
    except ValueError as e:
        code = 404 if "no encontrado" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))


@router.get("/payrolls", response_model=list[PayrollResponse])
@limiter.limit("30/minute")
async def list_payrolls(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_payrolls(current_user.tenant_id, db)


@router.post("/payrolls", response_model=PayrollResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def generate_payroll(
    request: Request,
    payload: PayrollCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_payroll(payload, current_user.tenant_id, db)


@router.post("/payrolls/{payroll_id}/approve", response_model=PayrollResponse)
@limiter.limit("30/minute")
async def approve_payroll(
    request: Request,
    payroll_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payroll = await svc.approve_payroll(payroll_id, current_user.tenant_id, current_user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    background_tasks.add_task(
        svc.generate_and_save_payroll_pdf,
        payroll_id=str(payroll_id),
        tenant_id=str(current_user.tenant_id),
        user_id=str(current_user.id),
    )
    return payroll


@router.patch("/payrolls/{payroll_id}", response_model=PayrollResponse)
@limiter.limit("30/minute")
async def update_payroll(
    request: Request,
    payroll_id: UUID,
    payload: PayrollUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        payroll = await svc.update_payroll(payroll_id, payload, current_user.tenant_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not payroll:
        raise HTTPException(status_code=404, detail="Nómina no encontrada")
    return payroll


@router.delete("/payrolls/{payroll_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_payroll(
    request: Request,
    payroll_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        if not await svc.delete_payroll(payroll_id, current_user.tenant_id, db):
            raise HTTPException(status_code=404, detail="Nómina no encontrada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payrolls/{payroll_id}/pdf")
@limiter.limit("30/minute")
async def download_payroll_pdf(
    request: Request,
    payroll_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        pdf_bytes, filename = await svc.download_payroll_pdf(
            payroll_id,
            current_user.tenant_id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Employee documents ──────────────────────────────────────────────────────


@router.get("/employees/{employee_id}/documents")
async def list_employee_documents(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_employee_documents(employee_id, current_user.tenant_id, db)


@router.post("/employees/{employee_id}/documents/upload", status_code=status.HTTP_201_CREATED)
async def upload_employee_document_file(
    employee_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        return await svc.upload_employee_document(
            employee_id,
            file.filename,
            content,
            file.content_type,
            current_user.tenant_id,
            current_user.id,
            db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/employees/{employee_id}/documents/{doc_id}/download")
async def download_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = await svc.get_employee_document(employee_id, doc_id, current_user.tenant_id, db)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    try:
        content, media_type, filename = svc.read_document_file(doc)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Documento no encontrado en disco")
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/employees/{employee_id}/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_employee_document(
    employee_id: UUID,
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_employee_document(employee_id, doc_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Documento no encontrado")


# ─── HR PDF documents ────────────────────────────────────────────────────────


@router.post("/documents/finiquito/pdf")
@limiter.limit("10/minute")
async def generate_finiquito_pdf_endpoint(
    request: Request,
    payload: FiniquitoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        emp, tenant = await svc.load_employee_and_tenant(
            payload.employee_id, current_user.tenant_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    pdf_bytes, filename, calc = svc.generate_finiquito_pdf(emp, tenant, payload)

    # Modo auto-cálculo: registrar el finiquito como Settlement (draft).
    if calc is not None:
        from app.services.hr.finiquito import create_settlement

        await create_settlement(db, current_user.tenant_id, payload.employee_id, calc)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/liquidacion-finiquito/pdf")
@limiter.limit("10/minute")
async def generate_liquidacion_finiquito_pdf_endpoint(
    request: Request,
    payload: LiquidacionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        emp, tenant = await svc.load_employee_and_tenant(
            payload.employee_id, current_user.tenant_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    pdf_bytes, filename = svc.generate_liquidacion_pdf(emp, tenant, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/documents/registro-jornada/pdf")
@limiter.limit("10/minute")
async def generate_registro_jornada_pdf_endpoint(
    request: Request,
    payload: RegistroJornadaRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        emp, tenant = await svc.load_employee_and_tenant(
            payload.employee_id, current_user.tenant_id, db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    pdf_bytes, filename = svc.generate_registro_jornada(emp, tenant, payload)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Schedules ───────────────────────────────────────────────────────────────


@router.get("/schedules")
@limiter.limit("30/minute")
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_schedules(db, current_user.tenant_id)


@router.get("/schedules/{employee_id}")
@limiter.limit("30/minute")
async def get_employee_schedule(
    request: Request,
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_employee_schedule(db, current_user.tenant_id, employee_id)


@router.post("/schedules/{employee_id}")
@limiter.limit("30/minute")
async def upsert_employee_schedule(
    request: Request,
    employee_id: UUID,
    payload: ScheduleUpsert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = await svc.upsert_schedule(
        db, current_user.tenant_id, employee_id,
        [s.model_dump() for s in payload.schedules],
    )
    return [{"id": str(r.id), "employee_id": str(r.employee_id), "day_of_week": r.day_of_week, "start_time": r.start_time, "end_time": r.end_time, "active": r.active} for r in rows]


@router.post("/schedules/ai-suggest")
@limiter.limit("10/minute")
async def ai_suggest_schedules(
    request: Request,
    payload: ScheduleAISuggestRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Genera una propuesta de horarios para los empleados (todos o un subconjunto)
    a partir de una instrucción en lenguaje natural. NO persiste — devuelve la
    sugerencia para que el usuario la revise y la guarde manualmente.
    """
    from app.services.ai.schedule_planner import suggest_schedules

    employees = await svc.list_employees(current_user.tenant_id, db)
    active = [e for e in employees if e.status != "inactive"]
    if payload.employee_ids:
        wanted = {str(eid) for eid in payload.employee_ids}
        active = [e for e in active if str(e.id) in wanted]

    emp_dicts = [
        {
            "id": str(e.id),
            "name": e.name,
            "role": e.role,
            "department": e.department,
        }
        for e in active
    ]

    return await suggest_schedules(emp_dicts, payload.instruction)


# ─── Attendance ───────────────────────────────────────────────────────────────


@router.get("/attendance")
@limiter.limit("30/minute")
async def list_attendance(
    request: Request,
    date: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date as date_type
    parsed = date_type.fromisoformat(date) if date else None
    return await svc.list_attendance(db, current_user.tenant_id, parsed)


@router.get("/attendance/now")
@limiter.limit("30/minute")
async def get_currently_working(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_currently_working(db, current_user.tenant_id)


@router.post("/attendance/clock-in", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def clock_in(
    request: Request,
    payload: ClockInRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        record = await svc.clock_in(db, current_user.tenant_id, payload.employee_id, payload.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": str(record.id), "employee_id": str(record.employee_id), "clock_in": record.clock_in.isoformat(), "clock_out": None, "date": record.date.isoformat(), "notes": record.notes}


@router.post("/attendance/{attendance_id}/clock-out")
@limiter.limit("30/minute")
async def clock_out(
    request: Request,
    attendance_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        record = await svc.clock_out_attendance(db, current_user.tenant_id, attendance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": str(record.id), "employee_id": str(record.employee_id), "clock_in": record.clock_in.isoformat(), "clock_out": record.clock_out.isoformat() if record.clock_out else None, "date": record.date.isoformat(), "notes": record.notes}


# ─── Leave Requests ───────────────────────────────────────────────────────────


@router.get("/leave-requests")
@limiter.limit("30/minute")
async def list_leave_requests(
    request: Request,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_leave_requests(db, current_user.tenant_id, status_filter)


@router.post("/leave-requests", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_leave_request(
    request: Request,
    payload: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    req = await svc.create_leave_request(
        db, current_user.tenant_id, payload.employee_id,
        payload.leave_type, payload.start_date, payload.end_date, payload.notes,
    )
    return _leave_row(req)


@router.post("/leave-requests/{request_id}/approve")
@limiter.limit("30/minute")
async def approve_leave_request(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = await svc.approve_leave_request(db, current_user.tenant_id, request_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _leave_row(req)


@router.post("/leave-requests/{request_id}/reject")
@limiter.limit("30/minute")
async def reject_leave_request(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        req = await svc.reject_leave_request(db, current_user.tenant_id, request_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _leave_row(req)


@router.delete("/leave-requests/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_leave_request(
    request: Request,
    request_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await svc.delete_leave_request(db, current_user.tenant_id, request_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


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

    content = await file.read()
    mime = file.content_type or "image/jpeg"
    try:
        data = await extract_receipt_data(content, mime)
    except ReceiptExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logging.getLogger(__name__).exception("Fallo procesando ticket")
        raise HTTPException(status_code=500, detail=f"Error procesando ticket: {e}")
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
        raise HTTPException(status_code=404, detail=str(e))
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
        raise HTTPException(status_code=404, detail=str(e))
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
        raise HTTPException(status_code=404, detail=str(e))
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
        raise HTTPException(status_code=404, detail=str(e))
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
    with open(path, "rb") as f:
        content = f.read()
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
        raise HTTPException(status_code=404, detail=str(e))


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


def _leave_row(req) -> dict:
    return {
        "id": str(req.id),
        "employee_id": str(req.employee_id),
        "leave_type": req.leave_type,
        "start_date": req.start_date.isoformat(),
        "end_date": req.end_date.isoformat(),
        "status": req.status,
        "notes": req.notes,
        "created_at": req.created_at.isoformat(),
    }
