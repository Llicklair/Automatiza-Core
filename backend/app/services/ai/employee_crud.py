"""employee_crud — CRUD, skills catalog, activity feed and direct instruction for AIEmployee."""

from __future__ import annotations

import logging
import uuid

import uuid as _uuid
from decimal import Decimal

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import ActivityEntry, AgentSkill, AIEmployee, TokenLedger
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

AVAILABLE_SKILLS = [{"module": k, "label": v} for k, v in _SKILL_LABELS.items()]


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
            AIEmployee.id == uuid.UUID(str(employee_id)),
            AIEmployee.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


# ── CRUD ────────────────────────────────────────────────────────────────────


async def list_employees(tenant_id, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(AIEmployee).where(AIEmployee.tenant_id == tenant_id).order_by(AIEmployee.created_at)
    )
    return [to_out(e) for e in result.scalars().all()]


async def create_employee(
    name: str,
    role_description: str,
    budget_limit_usd: float,
    tenant_id,
    db: AsyncSession,
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
    employee_id: str,
    tenant_id,
    domain: str | None,
    role: str | None,
    system_prompt: str | None,
    doc_folder: str | None,
    skills: list[str],
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
    employee_id: str,
    tenant_id,
    icon: str | None,
    avatar_color: str | None,
    db: AsyncSession,
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
    employee_id: str,
    tenant_id,
    new_status: str,
    db: AsyncSession,
) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None

    employee.status = new_status
    await db.commit()
    await db.refresh(employee)

    try:
        from app.services.integration.heartbeat import (
            register_employee_heartbeat,
            unregister_employee_heartbeat,
        )

        if new_status == "idle":
            register_employee_heartbeat(str(employee.id), str(employee.tenant_id))
        else:
            unregister_employee_heartbeat(str(employee.id))
    except Exception as e:
        logger.debug("Error updating employee heartbeat for %s: %s", employee.id, e)

    return to_out(employee)


async def delete_employee(employee_id: str, tenant_id, db: AsyncSession) -> bool:
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return False
    await db.delete(employee)
    await db.commit()
    return True


async def instruct_employee(
    employee_id: str,
    message: str,
    tenant_id,
    user_id,
    db: AsyncSession,
) -> dict:
    """Envía instrucción directa. Lanza ValueError si no existe o está pausado."""
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        raise ValueError("Empleado no encontrado")
    if employee.status == "paused":
        raise ValueError("paused")
    if employee.budget_limit_usd is not None:
        spent = await get_employee_spend(employee_id, tenant_id, db)
        if spent >= float(employee.budget_limit_usd):
            raise ValueError(f"budget_exceeded:{spent:.4f}/{float(employee.budget_limit_usd):.2f}")

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

    from app.services.workflow.activity import log_activity

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


# ── Activity Feed ───────────────────────────────────────────────────────────


async def list_activity(
    tenant_id,
    db: AsyncSession,
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
    tenant_id,
    category: str,
    message: str,
    icon: str,
    employee_id: str | None,
    task_id: str | None,
    metadata: dict | None,
    db: AsyncSession,
) -> dict:
    from app.services.workflow.activity import log_activity

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


# ── Single-employee lookup ───────────────────────────────────────────────────


async def get_employee(employee_id: str, tenant_id, db: AsyncSession) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    return to_out(employee) if employee else None


# ── TokenLedger ──────────────────────────────────────────────────────────────


async def record_token_usage(
    employee_id: str,
    tenant_id: str,
    task_id: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    provider: str,
    db: AsyncSession,
) -> None:
    """Append an immutable cost record to the TokenLedger for an AI employee."""
    db.add(TokenLedger(
        tenant_id=_uuid.UUID(tenant_id),
        employee_id=_uuid.UUID(employee_id),
        task_id=_uuid.UUID(task_id),
        prompt_tokens=tokens_in,
        completion_tokens=tokens_out,
        cost_usd=Decimal(str(round(cost_usd, 6))),
        llm_provider=provider,
    ))


def _to_uuid(val) -> _uuid.UUID:
    return val if isinstance(val, _uuid.UUID) else _uuid.UUID(str(val))


async def get_employee_spend(employee_id: str, tenant_id, db: AsyncSession) -> float:
    """Return cumulative cost_usd spent by an employee across all tasks.

    Filters by both employee_id AND tenant_id as defense-in-depth: even if an
    attacker guessed an employee UUID, the tenant filter prevents cross-tenant
    cost data leaks.
    """
    result = await db.execute(
        select(func.sum(TokenLedger.cost_usd)).where(
            TokenLedger.employee_id == _to_uuid(employee_id),
            TokenLedger.tenant_id == _to_uuid(tenant_id),
        )
    )
    total = result.scalar_one_or_none()
    return float(total or 0)


async def get_employee_ledger(
    employee_id: str,
    tenant_id,
    db: AsyncSession,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Return per-call ledger rows plus aggregate spend for one employee.

    Always filters by tenant_id to prevent cross-tenant data leaks.
    """
    emp_uuid = _to_uuid(employee_id)
    tnt_uuid = _to_uuid(tenant_id)

    rows_result = await db.execute(
        select(TokenLedger)
        .where(TokenLedger.employee_id == emp_uuid, TokenLedger.tenant_id == tnt_uuid)
        .order_by(desc(TokenLedger.created_at))
        .limit(min(limit, 200))
        .offset(offset)
    )
    rows = rows_result.scalars().all()

    agg_result = await db.execute(
        select(
            func.sum(TokenLedger.prompt_tokens).label("total_in"),
            func.sum(TokenLedger.completion_tokens).label("total_out"),
            func.sum(TokenLedger.cost_usd).label("total_cost"),
            func.count(TokenLedger.id).label("total_calls"),
        ).where(TokenLedger.employee_id == emp_uuid, TokenLedger.tenant_id == tnt_uuid)
    )
    agg = agg_result.one()

    return {
        "employee_id": employee_id,
        "total_calls": int(agg.total_calls or 0),
        "total_tokens_in": int(agg.total_in or 0),
        "total_tokens_out": int(agg.total_out or 0),
        "total_cost_usd": float(agg.total_cost or 0),
        "entries": [
            {
                "id": str(r.id),
                "task_id": str(r.task_id) if r.task_id else None,
                "provider": r.llm_provider,
                "tokens_in": r.prompt_tokens,
                "tokens_out": r.completion_tokens,
                "cost_usd": float(r.cost_usd),
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ],
    }
