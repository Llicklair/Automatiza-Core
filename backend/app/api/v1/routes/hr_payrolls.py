"""Rutas RRHH — nóminas."""

from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    PayrollCalculateResponse,
    PayrollCreate,
    PayrollResponse,
    PayrollSimpleCreate,
    PayrollUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.hr import service as svc
from app.services.state_machine import InvalidTransitionError

router = APIRouter(tags=["hr"])


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
        raise HTTPException(status_code=code, detail=str(e)) from e


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
        raise HTTPException(status_code=code, detail=str(e)) from e


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
        raise HTTPException(status_code=404, detail=str(e)) from e
    except InvalidTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

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
        raise HTTPException(status_code=400, detail=str(e)) from e
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
        raise HTTPException(status_code=400, detail=str(e)) from e


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
        raise HTTPException(status_code=404, detail=str(e)) from e

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
