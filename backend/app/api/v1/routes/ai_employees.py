"""Rutas para el sistema de Empleados IA.

Endpoints:
  GET    /ai-employees                    — Lista empleados del tenant
  POST   /ai-employees                    — Crea empleado personalizado (con skills)
  PATCH  /ai-employees/{id}/status        — Pausa/activa un empleado
  POST   /ai-employees/{id}/instruct      — Envía instrucción directa a un agente
  GET    /ai-employees/available-skills   — Lista tool_modules disponibles
  POST   /ai-employees/seed               — Siembra empleados built-in si no existen
  GET    /activity-feed                   — Timeline de actividad del tenant
  POST   /activity-feed                   — Registra entrada manual (uso interno/tests)
"""
import uuid
import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.ai_employees import AIEmployee, AgentSkill, ActivityEntry
from app.db.models.auth import User
from app.db.models.tasks import Task

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-employees"])


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AIEmployeeOut(BaseModel):
    id: str
    name: str
    role: str
    domain: str
    status: str
    is_builtin: bool
    budget_limit_usd: float | None

    model_config = ConfigDict(from_attributes=True)


class AIEmployeeCreate(BaseModel):
    name: str
    role: str
    domain: str
    system_prompt: str
    budget_limit_usd: float = 10.0
    skills: list[str] = []  # lista de tool_module a autorizar


class InstructPayload(BaseModel):
    message: str


class ActivityEntryOut(BaseModel):
    id: str
    employee_id: str | None
    category: str
    icon: str
    message: str
    metadata: dict | None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ActivityEntryCreate(BaseModel):
    category: str
    message: str
    icon: str = "📋"
    employee_id: str | None = None
    task_id: str | None = None
    metadata: dict | None = None


# ─── Empleados ────────────────────────────────────────────────────────────────

@router.get("/ai-employees", response_model=list[AIEmployeeOut])
async def list_ai_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIEmployee)
        .where(AIEmployee.tenant_id == current_user.tenant_id)
        .order_by(AIEmployee.created_at)
    )
    employees = result.scalars().all()
    return [
        AIEmployeeOut(
            id=str(e.id),
            name=e.name,
            role=e.role,
            domain=e.domain,
            status=e.status,
            is_builtin=e.is_builtin,
            budget_limit_usd=float(e.budget_limit_usd) if e.budget_limit_usd else None,
        )
        for e in employees
    ]


@router.post("/ai-employees", response_model=AIEmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_ai_employee(
    payload: AIEmployeeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = AIEmployee(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=payload.name,
        role=payload.role,
        domain=payload.domain,
        system_prompt=payload.system_prompt,
        budget_limit_usd=payload.budget_limit_usd,
        status="idle",
        is_builtin=False,
    )
    db.add(employee)
    await db.flush()  # obtener ID antes de crear skills

    for tool_module in payload.skills:
        db.add(AgentSkill(employee_id=employee.id, tool_module=tool_module))

    await db.commit()
    await db.refresh(employee)
    return AIEmployeeOut(
        id=str(employee.id),
        name=employee.name,
        role=employee.role,
        domain=employee.domain,
        status=employee.status,
        is_builtin=employee.is_builtin,
        budget_limit_usd=float(employee.budget_limit_usd) if employee.budget_limit_usd else None,
    )


@router.get("/ai-employees/available-skills")
async def list_available_skills(
    current_user: User = Depends(get_current_user),
):
    """Devuelve los tool_modules disponibles para asignar a empleados IA."""
    skills = [
        {"module": "billing.create_invoice", "label": "Crear facturas"},
        {"module": "billing.list_invoices", "label": "Ver facturas"},
        {"module": "billing.send_reminder", "label": "Enviar recordatorios de cobro"},
        {"module": "hr.list_employees", "label": "Ver empleados"},
        {"module": "hr.generate_payroll", "label": "Generar nóminas"},
        {"module": "hr.generate_document", "label": "Generar documentos laborales"},
        {"module": "crm.list_clients", "label": "Ver clientes"},
        {"module": "crm.create_activity", "label": "Registrar actividad CRM"},
        {"module": "email.send", "label": "Enviar emails"},
        {"module": "email.read_inbox", "label": "Leer bandeja de entrada"},
        {"module": "documents.search_rag", "label": "Buscar en documentos (RAG)"},
        {"module": "documents.upload", "label": "Subir documentos"},
        {"module": "banking.list_transactions", "label": "Ver transacciones bancarias"},
        {"module": "compliance.check", "label": "Verificar compliance"},
        {"module": "excel.export", "label": "Exportar a Excel"},
    ]
    return skills


@router.post("/ai-employees/{employee_id}/instruct")
async def instruct_employee(
    employee_id: str,
    payload: InstructPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Envía una instrucción directa a un agente IA, creando una tarea en su dominio."""
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == current_user.tenant_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if employee.status == "paused":
        raise HTTPException(status_code=409, detail="El empleado está pausado")

    # Las instrucciones siempre pasan por el coordinador.
    # El hint employee_id orienta el routing, pero el coordinador decide.
    task = Task(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        created_by=current_user.id,
        domain="coordinator",
        user_intent=payload.message,
        status="pending",
        additional_metadata={
            "source": "direct_instruction",
            "addressed_employee_id": str(employee.id),
            "addressed_employee_domain": employee.domain,
        },
    )
    db.add(task)
    await db.flush()

    from app.services.activity_service import log_activity
    await log_activity(
        db=db,
        tenant_id=str(current_user.tenant_id),
        category="system",
        message=f"Instrucción enviada a {employee.name}: {payload.message[:80]}{'…' if len(payload.message) > 80 else ''}",
        employee_id=str(employee.id),
        task_id=str(task.id),
        icon="💬",
    )

    await db.commit()
    return {"task_id": str(task.id), "status": "queued", "employee": employee.name}


@router.patch("/ai-employees/{employee_id}/status", response_model=AIEmployeeOut)
async def update_employee_status(
    employee_id: str,
    new_status: Literal["idle", "paused"],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == current_user.tenant_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    employee.status = new_status
    await db.commit()
    await db.refresh(employee)

    # Registrar o cancelar heartbeat según el nuevo estado
    try:
        from app.services.heartbeat_service import (
            register_employee_heartbeat,
            unregister_employee_heartbeat,
        )
        if new_status == "idle":
            register_employee_heartbeat(str(employee.id), str(employee.tenant_id))
        else:
            unregister_employee_heartbeat(str(employee.id))
    except Exception:
        pass  # El heartbeat es opcional — no bloquea la respuesta
    return AIEmployeeOut(
        id=str(employee.id),
        name=employee.name,
        role=employee.role,
        domain=employee.domain,
        status=employee.status,
        is_builtin=employee.is_builtin,
        budget_limit_usd=float(employee.budget_limit_usd) if employee.budget_limit_usd else None,
    )


# ─── Seed de empleados built-in ───────────────────────────────────────────────

_BUILTIN_EMPLOYEES = [
    {
        "name": "Ana Valdés",
        "role": "Directora Financiera",
        "domain": "billing",
        "system_prompt": (
            "Eres Ana Valdés, Directora Financiera de la empresa. "
            "Tu responsabilidad es gestionar facturas, cobros, albaranes y la salud financiera del negocio. "
            "Actúas de forma proactiva: detectas facturas vencidas, envías recordatorios y mantienes el flujo de caja. "
            "Comunicas siempre en español, con tono profesional y directo."
        ),
    },
    {
        "name": "Carlos Herrero",
        "role": "Responsable de RRHH",
        "domain": "hr",
        "system_prompt": (
            "Eres Carlos Herrero, Responsable de Recursos Humanos. "
            "Gestionas empleados, nóminas, contratos y el bienestar del equipo. "
            "Procesas nóminas con precisión, alertas de vacaciones y revisas cumplimiento laboral. "
            "Comunicas siempre en español, con tono cercano y profesional."
        ),
    },
    {
        "name": "Sofía Martín",
        "role": "Asistente de Comunicación",
        "domain": "email",
        "system_prompt": (
            "Eres Sofía Martín, Asistente de Comunicación. "
            "Gestionas el correo electrónico de la empresa: revisas el buzón, redactas respuestas "
            "y envías comunicaciones a clientes y proveedores. "
            "Siempre revisas antes de enviar y mantienes un tono profesional en español."
        ),
    },
]


@router.post("/ai-employees/seed", status_code=status.HTTP_200_OK)
async def seed_builtin_employees(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea los empleados built-in para el tenant si aún no existen.
    Idempotente: si ya existen (por nombre+domain), no los duplica.
    """
    created = []
    for emp_data in _BUILTIN_EMPLOYEES:
        existing = await db.execute(
            select(AIEmployee).where(
                AIEmployee.tenant_id == current_user.tenant_id,
                AIEmployee.domain == emp_data["domain"],
                AIEmployee.is_builtin == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            continue

        employee = AIEmployee(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            is_builtin=True,
            status="idle",
            **emp_data,
        )
        db.add(employee)
        created.append(emp_data["name"])

    await db.commit()
    return {"created": created, "message": f"{len(created)} empleados creados"}


# ─── Activity Feed ─────────────────────────────────────────────────────────────

@router.get("/activity-feed", response_model=list[ActivityEntryOut])
async def get_activity_feed(
    employee_id: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        select(ActivityEntry)
        .where(ActivityEntry.tenant_id == current_user.tenant_id)
        .order_by(desc(ActivityEntry.created_at))
        .limit(limit)
        .offset(offset)
    )
    if employee_id:
        query = query.where(ActivityEntry.employee_id == employee_id)
    if category:
        query = query.where(ActivityEntry.category == category)

    result = await db.execute(query)
    entries = result.scalars().all()
    return [
        ActivityEntryOut(
            id=str(e.id),
            employee_id=str(e.employee_id) if e.employee_id else None,
            category=e.category,
            icon=e.icon,
            message=e.message,
            metadata=e.metadata_json,
            created_at=e.created_at.isoformat(),
        )
        for e in entries
    ]


@router.post("/activity-feed", status_code=status.HTTP_201_CREATED)
async def create_activity_entry(
    payload: ActivityEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Endpoint para registrar entradas manualmente (tests o sistema interno)."""
    from app.services.activity_service import log_activity
    entry = await log_activity(
        db=db,
        tenant_id=str(current_user.tenant_id),
        category=payload.category,
        message=payload.message,
        employee_id=payload.employee_id,
        task_id=payload.task_id,
        icon=payload.icon,
        metadata=payload.metadata,
    )
    await db.commit()
    await db.refresh(entry)
    return {"id": str(entry.id), "created_at": entry.created_at.isoformat()}
