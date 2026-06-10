"""Rutas RRHH — horarios, fichajes y ausencias."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.hr import (
    ClockInRequest,
    LeaveRequestCreate,
    ScheduleAISuggestRequest,
    ScheduleUpsert,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services.hr import service as svc

router = APIRouter(tags=["hr"])


# ─── Schedules ───────────────────────────────────────────────────────────────


@router.get("/schedules")
@limiter.limit("30/minute")
async def list_schedules(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_schedules(db, current_user.tenant_id)


@router.get("/schedules/export")
@limiter.limit("10/minute")
async def export_schedules(
    request: Request,
    format: str = "xlsx",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exporta los horarios de todos los empleados a Excel o PDF."""
    from app.services.hr.schedule_export import (
        build_schedules_pdf,
        build_schedules_xlsx,
        fetch_schedule_grid,
    )

    if format not in ("xlsx", "pdf"):
        raise HTTPException(status_code=422, detail="format debe ser 'xlsx' o 'pdf'")
    grid = await fetch_schedule_grid(db, current_user.tenant_id)
    if format == "xlsx":
        content = build_schedules_xlsx(grid)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        content = build_schedules_pdf(grid)
        media = "application/pdf"
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="horarios.{format}"'},
    )


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
