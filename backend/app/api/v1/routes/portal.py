"""Employee self-service portal — data scoped to the logged-in user's employee record."""
import uuid

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    EmployeeResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
    PayrollResponse,
)
from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.db.models.hr import Attendance, Employee, LeaveRequest, Payroll
from app.services.hr.commands import (
    clock_in as svc_clock_in,
)
from app.services.hr.commands import (
    clock_out_attendance as svc_clock_out,
)
from app.services.hr.commands import (
    create_leave_request,
)
from app.services.hr.queries import get_employee_schedule as svc_get_schedule

router = APIRouter(prefix="/portal", tags=["portal"])


async def _get_my_employee(db: AsyncSession, current_user) -> Employee | None:
    result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == current_user.tenant_id,
            Employee.email == current_user.email,
        )
    )
    return result.scalar_one_or_none()


async def _get_active_attendance(
    db: AsyncSession, tenant_id, employee_id
) -> Attendance | None:
    result = await db.execute(
        select(Attendance).where(
            Attendance.tenant_id == tenant_id,
            Attendance.employee_id == employee_id,
            Attendance.clock_out.is_(None),
        )
    )
    return result.scalar_one_or_none()


def _attendance_dict(record: Attendance) -> dict:
    return {
        "id": str(record.id),
        "employee_id": str(record.employee_id),
        "clock_in": record.clock_in.isoformat() if record.clock_in else None,
        "clock_out": record.clock_out.isoformat() if record.clock_out else None,
        "date": record.date.isoformat() if record.date else None,
        "notes": record.notes,
    }


async def _build_portal_payload(
    db: AsyncSession,
    employee: Employee,
    tenant_id,
    *,
    read_only: bool = False,
) -> dict:
    payrolls_res = await db.execute(
        select(Payroll)
        .where(Payroll.employee_id == employee.id, Payroll.tenant_id == tenant_id)
        .order_by(Payroll.issue_date.desc())
        .limit(60)
    )
    payrolls = payrolls_res.scalars().all()

    leaves_res = await db.execute(
        select(LeaveRequest)
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.tenant_id == tenant_id,
        )
        .order_by(LeaveRequest.created_at.desc())
        .limit(100)
    )
    leaves = leaves_res.scalars().all()

    schedule = await svc_get_schedule(db, tenant_id, employee.id)
    active = await _get_active_attendance(db, tenant_id, employee.id)

    return {
        "employee": EmployeeResponse.model_validate(employee),
        "payrolls": [PayrollResponse.model_validate(p) for p in payrolls],
        "leave_requests": [LeaveRequestResponse.model_validate(lr) for lr in leaves],
        "schedule": schedule,
        "active_attendance": _attendance_dict(active) if active else None,
        "read_only": read_only,
    }


@router.get("/me")
async def get_portal_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    employee = await _get_my_employee(db, current_user)
    if not employee:
        return {"employee": None, "payrolls": [], "leave_requests": [], "read_only": False}
    return await _build_portal_payload(db, employee, current_user.tenant_id)


@router.get("/as/{employee_id}")
async def get_portal_as_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Vista admin: previsualiza Mi portal de cualquier empleado del tenant en modo lectura."""
    try:
        emp_uuid = uuid.UUID(employee_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="ID de empleado inválido")

    result = await db.execute(
        select(Employee).where(
            Employee.id == emp_uuid,
            Employee.tenant_id == current_user.tenant_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    return await _build_portal_payload(db, employee, current_user.tenant_id, read_only=True)


@router.post("/leave-requests", response_model=LeaveRequestResponse)
async def submit_my_leave_request(
    body: LeaveRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    employee = await _get_my_employee(db, current_user)
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
    employee = await _get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha de empleado")
    notes = body.get("notes") if isinstance(body, dict) else None
    try:
        record = await svc_clock_in(db, current_user.tenant_id, employee.id, notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _attendance_dict(record)


@router.post("/clock-out")
async def my_clock_out(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Cierra el fichaje activo del empleado vinculado al usuario actual."""
    employee = await _get_my_employee(db, current_user)
    if not employee:
        raise HTTPException(status_code=404, detail="No se encontró tu ficha de empleado")
    active = await _get_active_attendance(db, current_user.tenant_id, employee.id)
    if not active:
        raise HTTPException(status_code=400, detail="No tienes ningún fichaje abierto")
    try:
        record = await svc_clock_out(db, current_user.tenant_id, active.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _attendance_dict(record)
