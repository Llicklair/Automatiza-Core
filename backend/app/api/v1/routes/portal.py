"""Employee self-service portal — data scoped to the logged-in user's employee record."""

import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    LeaveRequestCreate,
    LeaveRequestResponse,
)
from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services import portal_service
from app.services.hr.commands import (
    clock_in as svc_clock_in,
)
from app.services.hr.commands import (
    clock_out_attendance as svc_clock_out,
)
from app.services.hr.commands import (
    create_leave_request,
)

router = APIRouter(prefix="/portal", tags=["portal"])


@router.get("/me")
async def get_portal_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    employee = await portal_service.get_my_employee(db, current_user)
    if not employee:
        return {"employee": None, "payrolls": [], "leave_requests": [], "read_only": False}
    return await portal_service.build_portal_payload(db, employee, current_user.tenant_id)


@router.get("/my-schedule/export")
async def export_my_schedule(
    format: str = "pdf",
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Descarga el horario del propio empleado en Excel o PDF."""
    from fastapi import Response

    from app.services.hr.schedule_export import (
        build_schedules_pdf,
        build_schedules_xlsx,
        fetch_schedule_grid,
    )

    if format not in ("xlsx", "pdf"):
        raise HTTPException(status_code=422, detail="format debe ser 'xlsx' o 'pdf'")
    employee = await portal_service.get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No tienes ficha de empleado")
    grid = await fetch_schedule_grid(db, current_user.tenant_id, employee_id=employee.id)
    if format == "xlsx":
        content = build_schedules_xlsx(grid)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = build_schedules_pdf(grid)
        media = "application/pdf"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="mi-horario.{format}"'},
    )


@router.get("/as/{employee_id}")
async def get_portal_as_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Vista admin: previsualiza Mi portal de cualquier empleado del tenant en modo lectura."""
    try:
        emp_uuid = uuid.UUID(employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="ID de empleado inválido") from exc

    employee = await portal_service.get_employee_by_uuid(db, emp_uuid, current_user.tenant_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    return await portal_service.build_portal_payload(db, employee, current_user.tenant_id, read_only=True)


@router.post("/leave-requests", response_model=LeaveRequestResponse)
async def submit_my_leave_request(
    body: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    employee = await portal_service.get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha de empleado")
    # Always use own employee_id regardless of what was sent
    req = await create_leave_request(
        db,
        tenant_id=current_user.tenant_id,
        employee_id=employee.id,
        leave_type=body.leave_type,
        start_date=body.start_date,
        end_date=body.end_date,
        notes=body.notes,
    )
    return LeaveRequestResponse.model_validate(req)


@router.post("/clock-in")
async def my_clock_in(
    body: dict = Body(default={}),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Crea un fichaje de entrada para el empleado vinculado al usuario actual."""
    employee = await portal_service.get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha de empleado")
    notes = body.get("notes") if isinstance(body, dict) else None
    try:
        record = await svc_clock_in(db, current_user.tenant_id, employee.id, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return portal_service.attendance_dict(record)


@router.post("/clock-out")
async def my_clock_out(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cierra el fichaje activo del empleado vinculado al usuario actual."""
    employee = await portal_service.get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha de empleado")
    active = await portal_service.get_active_attendance(db, current_user.tenant_id, employee.id)
    if not active:
        raise HTTPException(status_code=400, detail="No tienes ningún fichaje abierto")
    try:
        record = await svc_clock_out(db, current_user.tenant_id, active.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return portal_service.attendance_dict(record)
