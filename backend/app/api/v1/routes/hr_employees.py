"""Rutas RRHH — empleados, documentos de empleado y documentos PDF HR."""

import logging
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

from app.api.v1.schemas.hr import (
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    FiniquitoRequest,
    LiquidacionRequest,
    RegistroJornadaRequest,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.hr import service as svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["hr"])


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
