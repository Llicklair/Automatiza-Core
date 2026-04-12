"""Servicio de dominio para empleados IA.

Encapsula: CRUD, provisioning LLM, instrucciones directas, seed built-in,
activity feed, skills y apariencia.
"""

import json
import logging
import uuid

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import ActivityEntry, AgentSkill, AIEmployee
from app.db.models.tasks import Task

logger = logging.getLogger(__name__)

# ── Skills catalog ──────────────────────────────────────────────────────────

_KNOWN_SKILLS = [
    "billing.create_invoice",
    "billing.list_invoices",
    "billing.send_reminder",
    "hr.list_employees",
    "hr.generate_payroll",
    "hr.generate_document",
    "crm.list_clients",
    "crm.create_activity",
    "email.send",
    "email.read_inbox",
    "documents.search_rag",
    "documents.upload",
    "banking.list_transactions",
    "compliance.check",
    "excel.export",
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

AVAILABLE_SKILLS = [
    {"module": k, "label": v} for k, v in _SKILL_LABELS.items()
]

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


# ── Helpers ─────────────────────────────────────────────────────────────────


def to_out(e: AIEmployee) -> dict:
    """Convierte un AIEmployee a dict compatible con AIEmployeeOut."""
    return {
        "id": str(e.id),
        "name": e.name,
        "role": e.role,
        "domain": e.domain,
        "status": e.status,
        "is_builtin": e.is_builtin,
        "budget_limit_usd": float(e.budget_limit_usd) if e.budget_limit_usd else None,
        "doc_folder": e.doc_folder,
        "icon": e.icon,
        "avatar_color": e.avatar_color,
    }


async def _get_employee(employee_id: str, tenant_id, db: AsyncSession) -> AIEmployee | None:
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == employee_id,
            AIEmployee.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


# ── CRUD ────────────────────────────────────────────────────────────────────


async def list_employees(tenant_id, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(AIEmployee)
        .where(AIEmployee.tenant_id == tenant_id)
        .order_by(AIEmployee.created_at)
    )
    return [to_out(e) for e in result.scalars().all()]


async def create_employee(
    name: str, role_description: str, budget_limit_usd: float, tenant_id, db: AsyncSession,
) -> tuple[dict, str]:
    """Crea empleado. Retorna (out_dict, employee_id) para que la ruta lance el BG task."""
    name_slug = name.lower().replace(" ", "-")
    employee = AIEmployee(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name,
        role=role_description,
        domain="custom",
        system_prompt=(
            f"Eres {name}, agente IA con rol: {role_description}. "
            f"Ejecutas las tareas asignadas de forma proactiva y profesional. "
            f"Comunicas siempre en español, con tono profesional y directo."
        ),
        budget_limit_usd=budget_limit_usd,
        doc_folder=f"agentes/{name_slug}-{str(uuid.uuid4())[:8]}",
        status="pending_setup",
        is_builtin=False,
    )
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return to_out(employee), str(employee.id)


async def provision_employee(
    employee_id: str, tenant_id, domain: str | None, role: str | None,
    system_prompt: str | None, doc_folder: str | None, skills: list[str],
    db: AsyncSession,
) -> dict | None:
    """Provisiona un empleado (llamado por coordinador). Retorna None si no existe."""
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None

    if domain:
        employee.domain = domain
    if role:
        employee.role = role
    if system_prompt:
        employee.system_prompt = system_prompt
    if doc_folder:
        employee.doc_folder = doc_folder
    if employee.status == "pending_setup":
        employee.status = "idle"

    if skills:
        from sqlalchemy import delete as sa_delete
        await db.execute(sa_delete(AgentSkill).where(AgentSkill.employee_id == employee.id))
        for tool_module in skills:
            db.add(AgentSkill(employee_id=employee.id, tool_module=tool_module))

    await db.commit()
    await db.refresh(employee)
    return to_out(employee)


async def update_icon(employee_id: str, tenant_id, icon: str, db: AsyncSession) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None
    employee.icon = icon
    await db.commit()
    await db.refresh(employee)
    return to_out(employee)


async def update_appearance(
    employee_id: str, tenant_id, icon: str | None, avatar_color: str | None, db: AsyncSession,
) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None
    if icon is not None:
        employee.icon = icon
    if avatar_color is not None:
        employee.avatar_color = avatar_color
    await db.commit()
    await db.refresh(employee)
    return to_out(employee)


async def update_status(
    employee_id: str, tenant_id, new_status: str, db: AsyncSession,
) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None

    employee.status = new_status
    await db.commit()
    await db.refresh(employee)

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
        pass

    return to_out(employee)


async def delete_employee(employee_id: str, tenant_id, db: AsyncSession) -> bool:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return False
    await db.delete(employee)
    await db.commit()
    return True


async def instruct_employee(
    employee_id: str, message: str, tenant_id, user_id, db: AsyncSession,
) -> dict:
    """Envía instrucción directa. Lanza ValueError si no existe o está pausado."""
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        raise ValueError("Empleado no encontrado")
    if employee.status == "paused":
        raise ValueError("paused")

    task = Task(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        created_by=user_id,
        domain="coordinator",
        user_intent=message,
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
        tenant_id=str(tenant_id),
        category="system",
        message=f"Instrucción enviada a {employee.name}: {message[:80]}{'…' if len(message) > 80 else ''}",
        employee_id=str(employee.id),
        task_id=str(task.id),
        icon="💬",
    )

    await db.commit()
    return {"task_id": str(task.id), "status": "queued", "employee": employee.name}


# ── Seed ────────────────────────────────────────────────────────────────────


async def seed_builtin(tenant_id, db: AsyncSession) -> list[str]:
    """Crea empleados built-in. Retorna lista de nombres creados."""
    created = []
    for emp_data in _BUILTIN_EMPLOYEES:
        existing = await db.execute(
            select(AIEmployee).where(
                AIEmployee.tenant_id == tenant_id,
                AIEmployee.domain == emp_data["domain"],
                AIEmployee.is_builtin == True,  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            continue
        employee = AIEmployee(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            is_builtin=True,
            status="idle",
            **emp_data,
        )
        db.add(employee)
        created.append(emp_data["name"])
    await db.commit()
    return created


# ── Background provisioning ────────────────────────────────────────────────


async def provision_employee_bg(
    employee_id: str, tenant_id: str, name: str, role_description: str,
) -> None:
    """Llama al LLM para configurar el agente (ejecutar en background task)."""
    from langchain_core.messages import HumanMessage

    from app.core.llm_factory import get_llm
    from app.db.base import AsyncSessionLocal

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

            can_do = data.get("can_do", [_SKILL_LABELS[s] for s in assigned_skills])
            cannot_do = data.get("cannot_do", [_SKILL_LABELS[s] for s in unassigned_skills[:3]])
            vs_others = data.get("vs_others", "")

            summary_lines = [
                f"✅ Agente **{emp.name}** configurado como *{emp.role}* (dominio: {emp.domain}).",
                "",
                "**Puede hacer:**",
                *[f"  • {item}" for item in can_do],
                "",
                "**No puede hacer:**",
                *[f"  • {item}" for item in cannot_do],
            ]
            if vs_others:
                summary_lines += ["", "**Respecto a otros agentes:**", f"  {vs_others}"]

            summary = "\n".join(summary_lines)

            provision_task = Task(
                id=uuid.uuid4(),
                tenant_id=emp.tenant_id,
                created_by=None,
                domain="coordinator",
                user_intent=f"Configuración automática de {emp.name} ({role_description})",
                status="done",
                agent_results=[
                    {
                        "agent": "coordinator",
                        "success": True,
                        "summary": summary,
                        "output": {
                            "action": "chat_response",
                            "response": summary,
                        },
                    }
                ],
            )
            session.add(provision_task)
            await session.commit()
            logger.info(
                "Agente '%s' provisionado (domain=%s, skills=%d)",
                name, emp.domain, len(assigned_skills),
            )

    except Exception as exc:
        logger.error("Error provisionando agente '%s': %s", name, exc)
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(AIEmployee).where(AIEmployee.id == employee_id)
                )
                emp = result.scalar_one_or_none()
                if emp and emp.status == "pending_setup":
                    emp.status = "idle"
                    await session.commit()
        except Exception:
            pass


# ── Activity Feed ───────────────────────────────────────────────────────────


async def list_activity(
    tenant_id, db: AsyncSession,
    employee_id: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = (
        select(ActivityEntry)
        .where(ActivityEntry.tenant_id == tenant_id)
        .order_by(desc(ActivityEntry.created_at))
        .limit(limit)
        .offset(offset)
    )
    if employee_id:
        query = query.where(ActivityEntry.employee_id == employee_id)
    if category:
        query = query.where(ActivityEntry.category == category)

    result = await db.execute(query)
    return [
        {
            "id": str(e.id),
            "employee_id": str(e.employee_id) if e.employee_id else None,
            "category": e.category,
            "icon": e.icon,
            "message": e.message,
            "metadata": e.metadata_json,
            "created_at": e.created_at.isoformat(),
        }
        for e in result.scalars().all()
    ]


async def create_activity(
    tenant_id, category: str, message: str, icon: str,
    employee_id: str | None, task_id: str | None, metadata: dict | None,
    db: AsyncSession,
) -> dict:
    from app.services.activity_service import log_activity

    entry = await log_activity(
        db=db,
        tenant_id=str(tenant_id),
        category=category,
        message=message,
        employee_id=employee_id,
        task_id=task_id,
        icon=icon,
        metadata=metadata,
    )
    await db.commit()
    await db.refresh(entry)
    return {"id": str(entry.id), "created_at": entry.created_at.isoformat()}
