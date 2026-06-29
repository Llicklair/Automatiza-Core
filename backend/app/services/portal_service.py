"""Employee self-service portal — business logic extracted from the portal route."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    EmployeeResponse,
    LeaveRequestResponse,
    PayrollResponse,
)
from app.db.models.hr import Attendance, Employee, LeaveRequest, Payroll
from app.services.hr.queries import get_employee_schedule as svc_get_schedule


async def get_my_employee(db: AsyncSession, current_user) -> Employee | None:
    result = await db.execute(
        select(Employee).where(
            Employee.tenant_id == current_user.tenant_id,
            Employee.email == current_user.email,
        )
    )
    return result.scalar_one_or_none()


async def get_active_attendance(
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


def attendance_dict(record: Attendance) -> dict:
    return {
        "id": str(record.id),
        "employee_id": str(record.employee_id),
        "clock_in": record.clock_in.isoformat() if record.clock_in else None,
        "clock_out": record.clock_out.isoformat() if record.clock_out else None,
        "date": record.date.isoformat() if record.date else None,
        "notes": record.notes,
    }


async def build_portal_payload(
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
    active = await get_active_attendance(db, tenant_id, employee.id)

    return {
        "employee": EmployeeResponse.model_validate(employee),
        "payrolls": [PayrollResponse.model_validate(p) for p in payrolls],
        "leave_requests": [LeaveRequestResponse.model_validate(lr) for lr in leaves],
        "schedule": schedule,
        "active_attendance": attendance_dict(active) if active else None,
        "read_only": read_only,
    }


async def get_employee_by_uuid(
    db: AsyncSession, employee_id: uuid.UUID, tenant_id
) -> Employee | None:
    result = await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()
