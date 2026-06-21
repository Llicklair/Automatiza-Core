"""employee_crud â€” CRUD, skills catalog, activity feed and direct instruction for AIEmployee."""

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

# â”€â”€ Skills catalog â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

# Única fuente de verdad del catálogo de skills visible/asignable. CADA clave
# DEBE resolver en el tool_registry: `get_tool_for_employee` usa el último
# segmento tras el punto ("hr.calculate_and_create_payroll" → "calculate_and_create_payroll").
# Antes coexistían dos catálogos divergentes y 12 de 17 skills de UI apuntaban a
# tools inexistentes ("hr.generate_payroll", "email.send", "excel.export"…), que
# el compiler descartaba en silencio → el empleado no podía ejecutarlas.
# El invariante lo protege backend/tests/test_skill_catalog_valid.py.
_SKILL_LABELS = {
    # Facturación
    "billing.create_invoice": "Crear facturas",
    "billing.list_invoices": "Consultar facturas",
    "billing.send_invoice_by_email": "Enviar facturas por email",
    "billing.update_invoice_status": "Actualizar estado de facturas",
    # RRHH / Nóminas
    "hr.list_employees": "Ver empleados",
    "hr.calculate_and_create_payroll": "Generar nómina de un empleado",
    "hr.generate_all_payrolls": "Generar todas las nóminas del mes",
    "hr.approve_payroll": "Aprobar nóminas",
    # CRM
    "crm.list_opportunities": "Ver oportunidades CRM",
    "crm.create_opportunity": "Crear oportunidades",
    "crm.qualify_leads": "Cualificar leads con IA",
    # Banca
    "banking.list_transactions": "Ver transacciones bancarias",
    "banking.financial_summary": "Resumen financiero",
    "banking.reconcile_transactions": "Conciliar movimientos bancarios",
    # Email
    "email.send_email": "Enviar emails",
    "email.check_inbox": "Leer bandeja de entrada",
    "email.check_unread": "Ver correos sin leer",
    # Documentos / RAG
    "documents.classify_document": "Clasificar documentos",
    "documents.search_documents_semantic": "Buscar en documentos (semántico)",
    "documents.answer_from_documents": "Responder con base en documentos",
    "documents.create_document": "Crear documentos",
    # Compliance fiscal
    "compliance.check_fiscal_deadlines": "Verificar plazos fiscales (AEAT)",
    "compliance.fiscal_query": "Consultas fiscales (RAG)",
    "compliance.check_boe_news": "Vigilar novedades del BOE",
    # Excel
    "excel.export_erp_data": "Exportar datos a Excel",
    "excel.import_excel": "Importar/volcar datos desde Excel",
    # Reclutamiento
    "recruitment.process_cv": "Procesar CVs",
    "recruitment.list_candidates": "Ver candidatos",
    # Informes (universal)
    "reports.create_pdf_report": "Generar informes PDF (estructurado)",
    "reports.create_pdf_text_report": "Generar informes PDF (markdown)",
}

# Derivado de _SKILL_LABELS (antes era una lista duplicada y desincronizada).
# employee_provisioning lo usa para filtrar lo que sugiere el LLM e indexa
# _SKILL_LABELS[s], por lo que ambos DEBEN compartir exactamente las claves.
_KNOWN_SKILLS = list(_SKILL_LABELS)

AVAILABLE_SKILLS = [{"module": k, "label": v} for k, v in _SKILL_LABELS.items()]


# â”€â”€ Helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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
        "scope": e.scope,
        "memory_enabled": bool(e.memory_enabled),
        "knowledge_enabled": bool(e.knowledge_enabled),
        "workflows": e.workflows,
    }


async def _get_employee(employee_id: str, tenant_id, db: AsyncSession) -> AIEmployee | None:
    result = await db.execute(
        select(AIEmployee).where(
            AIEmployee.id == uuid.UUID(str(employee_id)),
            AIEmployee.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


# â”€â”€ CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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
    *,
    scope: dict | None = None,
    memory_enabled: bool = False,
    knowledge_enabled: bool = False,
    workflows: list | None = None,
) -> tuple[dict, str]:
    """Crea un empleado custom (nombre + rol/persona).

    Las 4 capacidades (scope/memory/knowledge/workflows) son opcionales y por
    defecto van vacías: un custom "fino" es válido — su valor está en el
    `system_prompt`. El conteo de capacidades NO bloquea el alta; solo se usa,
    de forma defensiva, en el classifier para que un custom sin capacidades no
    intercepte el routing por mención incidental (ver
    `agents/orchestrator/classifier.py`, `_meets_employee_contract`).

    Retorna (out_dict, employee_id) para que la ruta lance el BG task.
    """
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
        scope=scope,
        memory_enabled=memory_enabled,
        knowledge_enabled=knowledge_enabled,
        workflows=workflows,
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


async def update_budget(
    employee_id: str,
    tenant_id,
    budget_limit_usd: float | None,
    db: AsyncSession,
) -> dict | None:
    """Actualiza el límite de gasto mensual (USD) del empleado.

    `None` desactiva el límite (sin tope). El hard-stop y el aviso al 80% lo
    aplica el heartbeat vía `get_budget_status`.
    """
    employee = await _get_employee(employee_id, tenant_id, db)
    if not employee:
        return None
    employee.budget_limit_usd = budget_limit_usd
    await db.commit()
    await db.refresh(employee)
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
        # Ventana MENSUAL, coherente con el guard que pausa por paso
        # (agent_budget.get_budget_status). Antes este gate usaba gasto
        # acumulado de siempre → un empleado podía bloquearse para siempre
        # aquí pese a tener presupuesto del mes, o pasar el guard mensual
        # indefinidamente mientras este lo bloqueaba.
        from app.services.agent_budget import get_budget_status

        status = await get_budget_status(str(employee.id), db)
        if status and status["state"] == "exhausted":
            raise ValueError(
                f"budget_exceeded:{status['spend_usd']:.4f}/{float(status['limit_usd']):.2f}"
            )

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
        message=f"Instrucción enviada a {employee.name}: {message[:80]}{'â€¦' if len(message) > 80 else ''}",
        employee_id=str(employee.id),
        task_id=str(task.id),
        icon="ðŸ’¬",
    )

    await db.commit()

    # Sin esto la task queda pending eterno: el TaskRunner solo procesa lo que
    # se le despacha explícitamente (mismo patrón que el resto de creators de
    # tasks coordinator: workflow/_execution, event_bus, messaging, etc.).
    # Fase 3 (RLS): propagamos tenant_id al worker para fijar el ContextVar
    # antes de la SELECT de bootstrap de la Task.
    from app.services.workflow.task_dispatch import dispatch_orchestrator
    await dispatch_orchestrator(str(task.id), tenant_id=str(tenant_id))

    return {"task_id": str(task.id), "status": "queued", "employee": employee.name}


# â”€â”€ Activity Feed â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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


# â”€â”€ Single-employee lookup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def get_employee(employee_id: str, tenant_id, db: AsyncSession) -> dict | None:
    employee = await _get_employee(employee_id, tenant_id, db)
    return to_out(employee) if employee else None


# â”€â”€ TokenLedger â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


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
