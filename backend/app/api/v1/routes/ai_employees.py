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
import json
import uuid
import logging
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
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


def _out(e: "AIEmployee") -> "AIEmployeeOut":
    return AIEmployeeOut(
        id=str(e.id),
        name=e.name,
        role=e.role,
        domain=e.domain,
        status=e.status,
        is_builtin=e.is_builtin,
        budget_limit_usd=float(e.budget_limit_usd) if e.budget_limit_usd else None,
        doc_folder=e.doc_folder,
        icon=e.icon,
        avatar_color=e.avatar_color,
    )


# ─── Schemas ─────────────────────────────────────────────────────────────────

class AIEmployeeOut(BaseModel):
    id: str
    name: str
    role: str
    domain: str
    status: str
    is_builtin: bool
    budget_limit_usd: float | None
    doc_folder: str | None = None
    icon: str | None = None
    avatar_color: str | None = None

    model_config = ConfigDict(from_attributes=True)


class AIEmployeeIconUpdate(BaseModel):
    icon: str


class AIEmployeeAppearanceUpdate(BaseModel):
    icon: str | None = None
    avatar_color: str | None = None


class AIEmployeeCreate(BaseModel):
    name: str
    role_description: str  # lenguaje natural: "marketing", "CTO", "diseñador web"…
    budget_limit_usd: float = 10.0


class AIEmployeeProvision(BaseModel):
    """Usado por el coordinador para completar la configuración del agente."""
    domain: str | None = None
    role: str | None = None
    system_prompt: str | None = None
    doc_folder: str | None = None
    skills: list[str] = []


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
        _out(e) for e in employees
    ]


@router.post("/ai-employees", response_model=AIEmployeeOut, status_code=status.HTTP_201_CREATED)
async def create_ai_employee(
    payload: AIEmployeeCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Crea el registro del agente y lanza la configuración LLM en background."""
    name_slug = payload.name.lower().replace(" ", "-")
    employee = AIEmployee(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        name=payload.name,
        role=payload.role_description,
        domain="custom",
        system_prompt=(
            f"Eres {payload.name}, agente IA con rol: {payload.role_description}. "
            f"Ejecutas las tareas asignadas de forma proactiva y profesional. "
            f"Comunicas siempre en español, con tono profesional y directo."
        ),
        budget_limit_usd=payload.budget_limit_usd,
        doc_folder=f"agentes/{name_slug}-{str(uuid.uuid4())[:8]}",
        status="pending_setup",
        is_builtin=False,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)

    background_tasks.add_task(
        _provision_employee_bg,
        employee_id=str(employee.id),
        tenant_id=str(current_user.tenant_id),
        name=payload.name,
        role_description=payload.role_description,
    )
    return _out(employee)


_KNOWN_SKILLS = [
    "billing.create_invoice", "billing.list_invoices", "billing.send_reminder",
    "hr.list_employees", "hr.generate_payroll", "hr.generate_document",
    "crm.list_clients", "crm.create_activity",
    "email.send", "email.read_inbox",
    "documents.search_rag", "documents.upload",
    "banking.list_transactions", "compliance.check", "excel.export",
]

_SKILL_LABELS = {
    "billing.create_invoice": "Crear facturas",
    "billing.list_invoices": "Consultar facturas",
    "billing.send_reminder": "Enviar recordatorios de cobro",
    "hr.list_employees": "Ver empleados",
    "hr.generate_payroll": "Generar nóminas",
    "hr.generate_document": "Generar documentos laborales",
    "crm.list_clients": "Ver clientes",
    "crm.create_activity": "Registrar actividad CRM",
    "email.send": "Enviar emails",
    "email.read_inbox": "Leer bandeja de entrada",
    "documents.search_rag": "Buscar en documentos",
    "documents.upload": "Subir documentos",
    "banking.list_transactions": "Ver transacciones bancarias",
    "compliance.check": "Verificar compliance fiscal",
    "excel.export": "Exportar a Excel",
}


async def _provision_employee_bg(employee_id: str, tenant_id: str, name: str, role_description: str) -> None:
    """Llama al LLM para configurar el agente y genera un resumen de capacidades visible en el panel de tareas."""
    from app.db.base import AsyncSessionLocal
    from app.core.llm_factory import get_llm
    from langchain_core.messages import HumanMessage

    all_skill_labels = ", ".join(f"{k} ({v})" for k, v in _SKILL_LABELS.items())

    prompt = (
        f"Eres un asistente de configuración de agentes IA empresariales.\n"
        f"Se ha creado un nuevo agente: nombre='{name}', rol solicitado='{role_description}'.\n"
        f"Skills disponibles: {all_skill_labels}.\n\n"
        f"Devuelve SOLO un JSON válido con esta estructura (sin texto extra):\n"
        f"{{\n"
        f'  "domain": "<billing|hr|email|crm|banking|compliance|excel|documents|custom>",\n'
        f'  "role": "<título profesional conciso en español>",\n'
        f'  "system_prompt": "<prompt detallado en español, primera persona, 3-5 frases profesionales>",\n'
        f'  "skills": ["<tool_module>", ...],\n'
        f'  "can_do": ["<capacidad concreta 1>", "<capacidad 2>", ...],\n'
        f'  "cannot_do": ["<limitación concreta 1>", ...],\n'
        f'  "vs_others": "<1-2 frases comparando este agente con otros del equipo: en qué se diferencia y cuándo usarlo>"\n'
        f"}}\n"
        f"Asigna solo las skills realmente relevantes para el rol. can_do debe reflejar las skills asignadas. "
        f"cannot_do son acciones fuera de su dominio. vs_others compara con agentes típicos del equipo (facturación, RRHH, CRM, etc.)."
    )

    try:
        llm = get_llm(temperature=0)
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)

        assigned_skills = [s for s in data.get("skills", []) if s in _KNOWN_SKILLS]
        unassigned_skills = [s for s in _KNOWN_SKILLS if s not in assigned_skills]

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
            emp = result.scalar_one_or_none()
            if not emp:
                return

            emp.domain = data.get("domain", "custom")
            emp.role = data.get("role", role_description)
            emp.system_prompt = data.get("system_prompt", emp.system_prompt)
            emp.status = "idle"

            for tool_module in assigned_skills:
                session.add(AgentSkill(employee_id=emp.id, tool_module=tool_module))

            # Crear tarea completada con resumen de capacidades
            can_do = data.get("can_do", [_SKILL_LABELS[s] for s in assigned_skills])
            cannot_do = data.get("cannot_do", [_SKILL_LABELS[s] for s in unassigned_skills[:3]])
            vs_others = data.get("vs_others", "")

            summary_lines = [
                f"✅ Agente **{emp.name}** configurado como *{emp.role}* (dominio: {emp.domain}).",
                "",
                f"**Puede hacer:**",
                *[f"  • {item}" for item in can_do],
                "",
                f"**No puede hacer:**",
                *[f"  • {item}" for item in cannot_do],
            ]
            if vs_others:
                summary_lines += ["", f"**Respecto a otros agentes:**", f"  {vs_others}"]

            summary = "\n".join(summary_lines)

            provision_task = Task(
                id=uuid.uuid4(),
                tenant_id=emp.tenant_id,
                created_by=None,
                domain="coordinator",
                user_intent=f"Configuración automática de {emp.name} ({role_description})",
                status="done",
                agent_results=[{
                    "agent": "coordinator",
                    "success": True,
                    "summary": summary,
                    "output": {
                        "action": "chat_response",
                        "response": summary,
                    },
                }],
            )
            session.add(provision_task)
            await session.commit()
            logger.info("Agente '%s' provisionado (domain=%s, skills=%d)", name, emp.domain, len(assigned_skills))

    except Exception as exc:
        logger.error("Error provisionando agente '%s': %s", name, exc)
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
                emp = result.scalar_one_or_none()
                if emp and emp.status == "pending_setup":
                    emp.status = "idle"
                    await session.commit()
        except Exception:
            pass


@router.post("/ai-employees/{employee_id}/provision", response_model=AIEmployeeOut)
async def provision_ai_employee(
    employee_id: str,
    payload: AIEmployeeProvision,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """El coordinador llama a este endpoint para completar la configuración
    del agente: asigna dominio, system_prompt, skills y carpeta de docs."""
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == current_user.tenant_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    if payload.domain:
        employee.domain = payload.domain
    if payload.role:
        employee.role = payload.role
    if payload.system_prompt:
        employee.system_prompt = payload.system_prompt
    if payload.doc_folder:
        employee.doc_folder = payload.doc_folder
    if employee.status == "pending_setup":
        employee.status = "idle"

    # Reemplazar skills existentes
    if payload.skills:
        from sqlalchemy import delete as sa_delete
        await db.execute(
            sa_delete(AgentSkill).where(AgentSkill.employee_id == employee.id)
        )
        for tool_module in payload.skills:
            db.add(AgentSkill(employee_id=employee.id, tool_module=tool_module))

    await db.commit()
    await db.refresh(employee)
    return _out(employee)


@router.patch("/ai-employees/{employee_id}/icon", response_model=AIEmployeeOut)
async def update_employee_icon(
    employee_id: str,
    payload: AIEmployeeIconUpdate,
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
    employee.icon = payload.icon
    await db.commit()
    await db.refresh(employee)
    return _out(employee)


@router.patch("/ai-employees/{employee_id}/appearance", response_model=AIEmployeeOut)
async def update_employee_appearance(
    employee_id: str,
    payload: AIEmployeeAppearanceUpdate,
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
    if payload.icon is not None:
        employee.icon = payload.icon
    if payload.avatar_color is not None:
        employee.avatar_color = payload.avatar_color
    await db.commit()
    await db.refresh(employee)
    return _out(employee)


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


@router.delete("/ai-employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_employee(
    employee_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina un empleado IA del tenant. Los built-in también pueden eliminarse."""
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == current_user.tenant_id,
        )
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    await db.delete(employee)
    await db.commit()


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
    return _out(employee)


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
    {
        "name": "Javier Romero",
        "role": "Responsable Comercial",
        "domain": "crm",
        "system_prompt": (
            "Eres Javier Romero, Responsable Comercial de la empresa. "
            "Gestionas el CRM: registras oportunidades, haces seguimiento de clientes, "
            "creas actividades comerciales y mantienes el pipeline actualizado. "
            "Eres proactivo en detectar oportunidades de venta y en mantener relaciones con clientes. "
            "Comunicas siempre en español, con tono comercial y profesional."
        ),
    },
    {
        "name": "Miguel Torres",
        "role": "Responsable de Banca",
        "domain": "banking",
        "system_prompt": (
            "Eres Miguel Torres, Responsable de Banca de la empresa. "
            "Controlas los movimientos bancarios, reconcilias extractos, supervisas transferencias "
            "y mantienes el control de tesorería. "
            "Alertas sobre descubiertos, pagos pendientes y anomalías en cuenta. "
            "Comunicas siempre en español, con tono riguroso y profesional."
        ),
    },
    {
        "name": "Laura Jiménez",
        "role": "Asesora Fiscal y Compliance",
        "domain": "compliance",
        "system_prompt": (
            "Eres Laura Jiménez, Asesora Fiscal y de Compliance de la empresa. "
            "Gestionas las obligaciones tributarias: modelos 303, 130, retenciones, plazos del BOE "
            "y alertas de vencimientos fiscales. "
            "Asesoras sobre normativa aplicable y mantienes al día el calendario fiscal. "
            "Comunicas siempre en español, con tono técnico, preciso y profesional."
        ),
    },
    {
        "name": "Elena Ruiz",
        "role": "Gestora de Documentación",
        "domain": "documents",
        "system_prompt": (
            "Eres Elena Ruiz, Gestora de Documentación de la empresa. "
            "Procesas, clasificas y analizas documentos: contratos, facturas recibidas, albaranes y archivos. "
            "Extraes información clave mediante OCR, buscas en el repositorio documental "
            "y garantizas que la documentación esté ordenada y accesible. "
            "Comunicas siempre en español, con tono metódico y profesional."
        ),
    },
    {
        "name": "David Sánchez",
        "role": "Analista de Datos",
        "domain": "excel",
        "system_prompt": (
            "Eres David Sánchez, Analista de Datos de la empresa. "
            "Creas y gestionas hojas de cálculo, cruzas tablas de datos, generas informes en Excel "
            "y elaboras resúmenes ejecutivos a partir de los datos del negocio. "
            "Trabajas con precisión y entregas resultados listos para tomar decisiones. "
            "Comunicas siempre en español, con tono analítico y profesional."
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
