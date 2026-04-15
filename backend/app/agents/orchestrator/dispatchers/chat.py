"""
Dispatcher de chat — responde preguntas generales y consultas de estado
sin invocar agentes especializados. Usa el LLM directamente con contexto del tenant.
"""

import asyncio
import logging
from datetime import datetime
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import desc, func, select

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.core.llm_factory import get_llm_for_tenant
from app.db.base import AsyncSessionLocal
from app.db.models.accounting import BankTransaction
from app.db.models.billing import Invoice
from app.db.models.crm import Client, Opportunity
from app.db.models.hr import Employee, Payroll
from app.db.models.models import Task, Workflow, WorkflowExecution

logger = logging.getLogger(__name__)

_CHAT_SYSTEM = """\
Eres el asistente de AutomatizaPyme, un ERP inteligente para PYMEs españolas.
Respondes preguntas generales, dudas conceptuales y consultas de estado de forma clara y concisa.
Hoy es {date}. Responde siempre en español.

CONTEXTO DEL TENANT:
{tenant_context}

{extra_context}

REGLAS:
- Sé directo y útil. No uses jerga técnica innecesaria.
- Si te preguntan por el estado de una tarea, usa el contexto proporcionado.
- Si no tienes información suficiente para responder, dilo honestamente.
- No inventes datos. Si no sabes algo, sugiere qué acción podría hacer el usuario para obtenerlo.
- Respuestas cortas y al grano. Usa listas cuando mejore la legibilidad.
- NUNCA sugieras al usuario crear tareas desde la sección de automatizaciones ni automatizaciones desde la sección de tareas. Son módulos independientes: las tareas se crean en /tareas y las automatizaciones en /automatizaciones. No mezcles funcionalidades entre módulos.
- Tú solo respondes preguntas y consultas. No ejecutas acciones ni creas nada.
- PROHIBIDO: nunca digas "tu solicitud está en proceso", "te avisaré", "en breve tendrás la información" ni similares. Responde con los datos que tienes en el CONTEXTO DEL TENANT o di claramente que no tienes ese dato disponible en este modo."""


async def _dispatch_chat(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Responde directamente al usuario usando el LLM con contexto del tenant."""
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )
    tenant_id = state["tenant_id"]

    try:
        # Construir contexto del tenant
        tenant_context = _build_tenant_context(state)

        # Contexto extra según metadata (ej: workflows desde /automatizaciones)
        extra_context = await _build_extra_context(state)

        system_prompt = _CHAT_SYSTEM.format(
            date=datetime.now().strftime("%d/%m/%Y"),
            tenant_context=tenant_context,
            extra_context=extra_context,
        )

        # Construir mensajes con historial de conversación si existe
        messages = [SystemMessage(content=system_prompt)]
        metadata = state.get("additional_metadata") or {}
        conversation_history = metadata.get("conversation_history", [])
        for msg in conversation_history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=intent))

        # Usar LLM del tenant (respeta config de API Keys del dashboard)
        async with AsyncSessionLocal() as db:
            llm = await get_llm_for_tenant(tenant_id, db, temperature=0)
        response = await llm.ainvoke(messages)

        response_text = (
            response.content.strip() if response.content else "No he podido generar una respuesta."
        )

        return {
            "subtask_id": subtask["id"],
            "agent": "chat",
            "success": True,
            "output": {"action": "chat_response", "response": response_text},
            "summary": response_text[:200],
            "error": None,
        }

    except Exception as e:
        logger.exception("Error en dispatcher chat")
        return {
            "subtask_id": subtask["id"],
            "agent": "chat",
            "success": False,
            "output": {"action": "failed", "response": f"Error al procesar tu pregunta: {e}"},
            "summary": f"Error en chat: {e}",
            "error": str(e),
        }


def _build_tenant_context(state: OrchestratorState) -> str:
    """Construye contexto a partir del tenant_knowledge cargado."""
    knowledge = state.get("tenant_knowledge", [])
    if not knowledge:
        return "No hay información adicional del tenant disponible."

    lines = []
    for fact in knowledge:
        lines.append(f"- {fact.get('key', '')}: {fact.get('value', '')}")
    return "\n".join(lines)


_BILLING_KW = {
    "factura",
    "cobro",
    "pago",
    "presupuesto",
    "albarán",
    "iva",
    "emisión",
    "invoice",
    "facturación",
    "importe",
    "cobrada",
    "pendiente de cobro",
}
_HR_KW = {
    "nómina",
    "empleado",
    "empleados",
    "salario",
    "trabajador",
    "vacaciones",
    "baja",
    "contrato laboral",
    "rrhh",
    "payroll",
}
_CRM_KW = {"cliente", "clientes", "oportunidad", "lead", "venta", "embudo", "trato", "crm"}
_BANKING_KW = {
    "saldo",
    "banco",
    "cuenta",
    "transacción",
    "movimiento",
    "transferencia",
    "balance bancario",
    "extracto",
}


def _detect_topics(intent: str) -> set[str]:
    """Detecta qué módulos son relevantes para la pregunta."""
    t = intent.lower()
    topics: set[str] = set()
    if any(kw in t for kw in _BILLING_KW):
        topics.add("billing")
    if any(kw in t for kw in _HR_KW):
        topics.add("hr")
    if any(kw in t for kw in _CRM_KW):
        topics.add("crm")
    if any(kw in t for kw in _BANKING_KW):
        topics.add("banking")
    return topics


async def _build_extra_context(state: OrchestratorState) -> str:
    """Carga solo el contexto relevante para la pregunta del usuario."""
    tenant_id = state.get("tenant_id")
    if not tenant_id:
        return ""

    intent = state.get("current_intent") or state.get("user_intent", "")
    metadata = state.get("additional_metadata") or {}
    topics = _detect_topics(intent)

    loaders: list = [_load_recent_tasks_context(tenant_id)]

    # Si no se detecta ningún módulo específico, cargar todos (pregunta genérica)
    if not topics:
        loaders += [
            _load_billing_context(tenant_id),
            _load_hr_context(tenant_id),
            _load_crm_context(tenant_id),
            _load_banking_context(tenant_id),
        ]
    else:
        if "billing" in topics:
            loaders.append(_load_billing_context(tenant_id))
        if "hr" in topics:
            loaders.append(_load_hr_context(tenant_id))
        if "crm" in topics:
            loaders.append(_load_crm_context(tenant_id))
        if "banking" in topics:
            loaders.append(_load_banking_context(tenant_id))

    if metadata.get("context") == "workflows":
        loaders.append(_load_workflow_context(tenant_id))

    results = await asyncio.gather(*loaders, return_exceptions=True)
    return "\n\n".join(r for r in results if isinstance(r, str) and r)


async def _load_workflow_context(tenant_id: str) -> str:
    """Carga resumen de workflows y últimas ejecuciones."""
    try:
        async with AsyncSessionLocal() as db:
            wf_result = await db.execute(
                select(Workflow)
                .where(Workflow.tenant_id == UUID(tenant_id))
                .order_by(desc(Workflow.created_at))
                .limit(20)
            )
            workflows = wf_result.scalars().all()

            if not workflows:
                return "AUTOMATIZACIONES: No hay automatizaciones configuradas."

            lines = ["AUTOMATIZACIONES CONFIGURADAS:"]
            for wf in workflows:
                status = "activa" if wf.is_active else "pausada"
                lines.append(
                    f"- '{wf.name}' ({status}) — trigger: {wf.trigger_type}, modo: {wf.execution_mode}"
                )

            # Últimas 10 ejecuciones
            wf_ids = [wf.id for wf in workflows]
            exec_result = await db.execute(
                select(WorkflowExecution)
                .where(WorkflowExecution.workflow_id.in_(wf_ids))
                .order_by(desc(WorkflowExecution.started_at))
                .limit(10)
            )
            execs = exec_result.scalars().all()

            if execs:
                lines.append("\nULTIMAS EJECUCIONES:")
                for ex in execs:
                    wf_name = next((w.name for w in workflows if w.id == ex.workflow_id), "?")
                    lines.append(
                        f"- '{wf_name}' — {ex.status} ({ex.started_at.strftime('%d/%m %H:%M') if ex.started_at else '?'})"
                    )

            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de workflows: %s", e)
        return ""


async def _load_billing_context(tenant_id: str) -> str:
    """Carga resumen y detalle de facturas."""
    try:
        async with AsyncSessionLocal() as db:
            # Agregados
            stats = await db.execute(
                select(
                    func.count(Invoice.id).label("total"),
                    func.count(Invoice.id).filter(Invoice.status == "draft").label("draft"),
                    func.count(Invoice.id).filter(Invoice.status == "sent").label("sent"),
                    func.count(Invoice.id).filter(Invoice.status == "paid").label("paid"),
                    func.coalesce(func.sum(Invoice.amount_total), 0).label("amount_total"),
                ).where(Invoice.tenant_id == UUID(tenant_id))
            )
            s = stats.one()

            # Detalle individual (hasta 50 facturas recientes)
            rows = await db.execute(
                select(Invoice, Client.name.label("client_name"))
                .join(Client, Invoice.client_id == Client.id, isouter=True)
                .where(Invoice.tenant_id == UUID(tenant_id))
                .order_by(desc(Invoice.date))
                .limit(20)
            )
            invoices = rows.all()

            lines = [
                f"FACTURACIÓN (total: {s.total} | borradores: {s.draft} | enviadas: {s.sent} | cobradas: {s.paid} | importe total: {float(s.amount_total):.2f} €):",
            ]
            for inv, client_name in invoices:
                fecha = inv.date.strftime("%d/%m/%Y") if inv.date else "?"
                lines.append(
                    f"  · {inv.invoice_number or inv.id} | {client_name or 'Sin cliente'} | "
                    f"{float(inv.amount_total):.2f} € | {inv.status} | {fecha}"
                )
            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de facturación: %s", e)
        return ""


async def _load_hr_context(tenant_id: str) -> str:
    """Carga resumen y detalle de empleados y nóminas."""
    try:
        async with AsyncSessionLocal() as db:
            emp_stats = await db.execute(
                select(
                    func.count(Employee.id).label("total"),
                    func.count(Employee.id).filter(Employee.status == "active").label("active"),
                ).where(Employee.tenant_id == UUID(tenant_id))
            )
            er = emp_stats.one()

            employees = await db.execute(
                select(Employee)
                .where(Employee.tenant_id == UUID(tenant_id))
                .order_by(Employee.name)
                .limit(20)
            )
            emp_list = employees.scalars().all()

            pay_stats = await db.execute(
                select(
                    func.count(Payroll.id).label("total"),
                    func.coalesce(func.sum(Payroll.net_salary), 0).label("net_total"),
                ).where(Payroll.tenant_id == UUID(tenant_id))
            )
            pr = pay_stats.one()

            recent_payrolls = await db.execute(
                select(Payroll)
                .where(Payroll.tenant_id == UUID(tenant_id))
                .order_by(desc(Payroll.issue_date))
                .limit(10)
            )
            pay_list = recent_payrolls.scalars().all()

            lines = [
                f"RRHH (empleados activos: {er.active}/{er.total} | nóminas: {pr.total} | masa salarial neta: {float(pr.net_total):.2f} €):"
            ]
            lines.append("  Empleados:")
            for e in emp_list:
                lines.append(
                    f"    · {e.name} | {e.role or '-'} | {e.department or '-'} | salario base: {float(e.base_salary or 0):.2f} € | {e.status}"
                )
            if pay_list:
                lines.append("  Últimas nóminas:")
                for p in pay_list:
                    fecha = p.issue_date.strftime("%d/%m/%Y") if p.issue_date else "?"
                    # Buscar nombre empleado
                    emp_name = next(
                        (e.name for e in emp_list if e.id == p.employee_id), str(p.employee_id)
                    )
                    lines.append(
                        f"    · {emp_name} | neto: {float(p.net_salary or 0):.2f} € | {p.status} | {fecha}"
                    )
            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de RRHH: %s", e)
        return ""


async def _load_crm_context(tenant_id: str) -> str:
    """Carga detalle de clientes y oportunidades CRM."""
    try:

        async with AsyncSessionLocal() as db:
            clients = await db.execute(
                select(Client)
                .where(Client.tenant_id == UUID(tenant_id))
                .order_by(Client.name)
                .limit(20)
            )
            client_list = clients.scalars().all()

            opps = await db.execute(
                select(Opportunity)
                .where(Opportunity.tenant_id == UUID(tenant_id))
                .order_by(desc(Opportunity.expected_value))
                .limit(15)
            )
            opp_list = opps.scalars().all()

            lines = [f"CRM (clientes: {len(client_list)} | oportunidades: {len(opp_list)}):"]
            lines.append("  Clientes:")
            for c in client_list:
                lines.append(
                    f"    · {c.name} | {c.nif or '-'} | {c.email or '-'} | {c.client_type}"
                )
            if opp_list:
                lines.append("  Oportunidades:")
                for o in opp_list:
                    client_name = next(
                        (c.name for c in client_list if c.id == o.client_id), str(o.client_id)
                    )
                    lines.append(
                        f"    · {o.title} | {client_name} | {float(o.expected_value or 0):.0f} € | etapa: {o.stage}"
                    )
            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de CRM: %s", e)
        return ""


async def _load_banking_context(tenant_id: str) -> str:
    """Carga movimientos bancarios recientes con detalle."""
    try:
        async with AsyncSessionLocal() as db:
            stats = await db.execute(
                select(
                    func.count(BankTransaction.id).label("total"),
                    func.count(BankTransaction.id)
                    .filter(BankTransaction.status == "unreconciled")
                    .label("unreconciled"),
                ).where(BankTransaction.tenant_id == UUID(tenant_id))
            )
            sr = stats.one()

            txs = await db.execute(
                select(BankTransaction)
                .where(BankTransaction.tenant_id == UUID(tenant_id))
                .order_by(desc(BankTransaction.date))
                .limit(15)
            )
            tx_list = txs.scalars().all()

            last_balance = next((float(t.balance) for t in tx_list if t.balance is not None), None)
            lines = [
                f"BANCA (movimientos: {sr.total} | sin conciliar: {sr.unreconciled}{f' | último saldo: {last_balance:.2f} €' if last_balance is not None else ''}):"
            ]
            for t in tx_list:
                fecha = t.date.strftime("%d/%m/%Y") if t.date else "?"
                signo = "+" if (t.amount or 0) >= 0 else ""
                lines.append(
                    f"  · {fecha} | {t.description or '-'} | {signo}{float(t.amount or 0):.2f} € | {t.status}"
                )
            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando contexto de banca: %s", e)
        return ""


async def _load_recent_tasks_context(tenant_id: str) -> str:
    """Carga las últimas tareas para consultas de estado."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Task)
                .where(Task.tenant_id == UUID(tenant_id))
                .order_by(desc(Task.created_at))
                .limit(10)
            )
            tasks = result.scalars().all()

            if not tasks:
                return "TAREAS RECIENTES: No hay tareas registradas."

            lines = ["TAREAS RECIENTES:"]
            for t in tasks:
                fecha = t.created_at.strftime("%d/%m %H:%M") if t.created_at else "?"
                lines.append(f"- [{t.status}] {t.user_intent[:80]} ({t.domain}, {fecha})")

            return "\n".join(lines)
    except Exception as e:
        logger.debug("Error cargando tareas recientes: %s", e)
        return ""
