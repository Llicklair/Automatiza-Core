"""Rutas para el sistema de Empleados IA — thin controller."""

import logging
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.ai_employees import (
    ActivityEntryCreate,
    ActivityEntryOut,
    AIEmployeeAppearanceUpdate,
    AIEmployeeBudgetUpdate,
    AIEmployeeCreate,
    AIEmployeeIconUpdate,
    AIEmployeeOut,
    AIEmployeeProvision,
    InstructPayload,
)
from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import User
from app.services.ai import employee as svc

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-employees"])


# ─── Empleados ──────────────────────────────────────────────────────────────


@router.get("/ai-employees", response_model=list[AIEmployeeOut])
async def list_ai_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_employees(current_user.tenant_id, db)


@router.post("/ai-employees", response_model=AIEmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_ai_employee(
    payload: AIEmployeeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    out, employee_id = await svc.create_employee(
        payload.name,
        payload.role_description,
        payload.budget_limit_usd,
        current_user.tenant_id,
        db,
        scope=payload.scope,
        memory_enabled=payload.memory_enabled,
        knowledge_enabled=payload.knowledge_enabled,
        workflows=payload.workflows,
    )
    background_tasks.add_task(
        svc.provision_employee_bg,
        employee_id=employee_id,
        tenant_id=str(current_user.tenant_id),
        name=payload.name,
        role_description=payload.role_description,
    )
    return out


@router.get("/ai-employees/available-skills")
async def list_available_skills(
    current_user: User = Depends(get_current_user),
):
    return svc.AVAILABLE_SKILLS


@router.get("/ai-employees/{employee_id}", response_model=AIEmployeeOut)
async def get_ai_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.get_employee(employee_id, current_user.tenant_id, db)
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.get("/ai-employees/{employee_id}/usage")
async def get_employee_usage(
    employee_id: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    emp = await svc.get_employee(employee_id, current_user.tenant_id, db)
    if not emp:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return await svc.get_employee_ledger(employee_id, current_user.tenant_id, db, limit, offset)


@router.post("/ai-employees/{employee_id}/provision", response_model=AIEmployeeOut)
async def provision_ai_employee(
    employee_id: str,
    payload: AIEmployeeProvision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    result = await svc.provision_employee(
        employee_id,
        current_user.tenant_id,
        payload.domain,
        payload.role,
        payload.system_prompt,
        payload.doc_folder,
        payload.skills,
        db,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.patch("/ai-employees/{employee_id}/icon", response_model=AIEmployeeOut)
async def update_employee_icon(
    employee_id: str,
    payload: AIEmployeeIconUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.update_icon(employee_id, current_user.tenant_id, payload.icon, db)
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.patch("/ai-employees/{employee_id}/appearance", response_model=AIEmployeeOut)
async def update_employee_appearance(
    employee_id: str,
    payload: AIEmployeeAppearanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.update_appearance(
        employee_id,
        current_user.tenant_id,
        payload.icon,
        payload.avatar_color,
        db,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.patch("/ai-employees/{employee_id}/budget", response_model=AIEmployeeOut)
async def update_employee_budget(
    employee_id: str,
    payload: AIEmployeeBudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.update_budget(
        employee_id, current_user.tenant_id, payload.budget_limit_usd, db
    )
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.patch("/ai-employees/{employee_id}/status", response_model=AIEmployeeOut)
async def update_employee_status(
    employee_id: str,
    new_status: Literal["idle", "paused"],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await svc.update_status(employee_id, current_user.tenant_id, new_status, db)
    if not result:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    return result


@router.post("/ai-employees/{employee_id}/instruct")
async def instruct_employee(
    employee_id: str,
    payload: InstructPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.instruct_employee(
            employee_id,
            payload.message,
            current_user.tenant_id,
            current_user.id,
            db,
        )
    except ValueError as e:
        msg = str(e)
        if "pausado" in msg or "paused" in msg:
            raise HTTPException(status_code=409, detail="El empleado está pausado")
        if "budget_exceeded" in msg:
            raise HTTPException(status_code=402, detail="Presupuesto agotado para este empleado")
        raise HTTPException(status_code=404, detail=msg)


@router.delete("/ai-employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not await svc.delete_employee(employee_id, current_user.tenant_id, db):
        raise HTTPException(status_code=404, detail="Empleado no encontrado")


@router.post("/ai-employees/seed", status_code=status.HTTP_200_OK)
async def seed_builtin_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    created = await svc.seed_builtin(current_user.tenant_id, db)
    return {"created": created, "message": f"{len(created)} empleados creados"}


# ─── Activity Feed ──────────────────────────────────────────────────────────


@router.get("/activity-feed", response_model=list[ActivityEntryOut])
async def get_activity_feed(
    employee_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.list_activity(
        current_user.tenant_id,
        db,
        employee_id,
        category,
        limit,
        offset,
    )


@router.post("/activity-feed", status_code=status.HTTP_201_CREATED)
async def create_activity_entry(
    payload: ActivityEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_activity(
        current_user.tenant_id,
        payload.category,
        payload.message,
        payload.icon,
        payload.employee_id,
        payload.task_id,
        payload.metadata,
        db,
    )
