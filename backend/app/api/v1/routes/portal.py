"""Employee self-service portal — data scoped to the logged-in user's employee record."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.api.v1.schemas.hr import (
    EmployeeResponse,
    LeaveRequestCreate,
    LeaveRequestResponse,
    PayrollResponse,
)
from app.db.models.hr import Employee, LeaveRequest, Payroll
from app.services.hr.commands import create_leave_request

router = APIRouter(prefix="/portal", tags=["portal"])


async def _get_my_employee(db: AsyncSession, current_user) -> Employee | None:
    result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == current_user.tenant_id,
            Employee.email == current_user.email,
        )
    )
    return result.scalar_one_or_none()


@router.get("/me")
async def get_portal_me(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    employee = await _get_my_employee(db, current_user)
    if not employee:
        return {"employee": None, "payrolls": [], "leave_requests": []}

    payrolls_res = await db.execute(
        select(Payroll)
        .where(Payroll.employee_id == employee.id, Payroll.tenant_id == current_user.tenant_id)
        .order_by(Payroll.issue_date.desc())
    )
    payrolls = payrolls_res.scalars().all()

    leaves_res = await db.execute(
        select(LeaveRequest)
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.tenant_id == current_user.tenant_id,
        )
        .order_by(LeaveRequest.created_at.desc())
    )
    leaves = leaves_res.scalars().all()

    return {
        "employee": EmployeeResponse.model_validate(employee),
        "payrolls": [PayrollResponse.model_validate(p) for p in payrolls],
        "leave_requests": [LeaveRequestResponse.model_validate(lr) for lr in leaves],
    }


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
