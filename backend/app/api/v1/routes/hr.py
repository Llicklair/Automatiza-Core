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
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    FiniquitoRequest,
    LiquidacionRequest,
    PayrollCalculateResponse,
    PayrollCreate,
    PayrollResponse,
    PayrollSimpleCreate,
    PayrollUpdate,
    RegistroJornadaRequest,
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
        return await svc.create_employee(payload, current_user.tenant_id, db)
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

    pdf_bytes, filename = svc.generate_finiquito_pdf(emp, tenant, payload)
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
