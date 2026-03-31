"""
Agente CRM — gestiona el embudo de ventas, leads y oportunidades.
Puede crear, mover y analizar oportunidades de negocio de forma autónoma.
"""
from datetime import UTC, datetime
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy import select

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.db.base import AsyncSessionLocal
from app.db.models.models import Client, Opportunity
from app.core.config import settings
from app.core.llm_factory import get_llm

def _get_llm():
    return get_llm(temperature=0)


# ─── Herramientas ────────────────────────────────────────────────────────────

@tool
async def list_opportunities(tenant_id: str, stage: str = "all") -> str:
    """
    Lista las oportunidades de venta del CRM, opcionalmente filtradas por fase.
    Args:
        tenant_id: ID del tenant
        stage: Fase a filtrar ('new', 'qualified', 'proposal', 'won', 'lost', 'all')
    """
    return await _list_opportunities_async(tenant_id, stage)

async def _list_opportunities_async(tenant_id: str, stage: str) -> str:
    try:
        from sqlalchemy.orm import selectinload
        async with AsyncSessionLocal() as db:
            query = select(Opportunity).filter(Opportunity.tenant_id == UUID(tenant_id)).options(selectinload(Opportunity.client))
            if stage != "all":
                query = query.filter(Opportunity.stage == stage)
            query = query.order_by(Opportunity.created_at.desc())
            result = await db.execute(query)
            opps = result.scalars().all()

            if not opps:
                return f"No hay oportunidades{' en la fase ' + stage if stage != 'all' else ''}."

            lines = []
            for opp in opps:
                client_name = opp.client.name if opp.client else "Cliente desconocido"
                lines.append(
                    f"- [{opp.stage.upper()}] {opp.title} | "
                    f"Cliente: {client_name} | "
                    f"Valor: {float(opp.expected_value or 0):.2f}EUR | "
                    f"ID: {opp.id}"
                )
            return f"Oportunidades ({len(opps)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error listando oportunidades: {str(e)}"


@tool
async def create_opportunity(tenant_id: str, client_nif: str, title: str, expected_value: float = 0, stage: str = "new") -> str:
    """
    Crea una nueva Oportunidad de Venta (Lead) en el CRM para un cliente existente.
    Args:
        tenant_id: ID del tenant
        client_nif: NIF del cliente/lead
        title: Nombre de la oportunidad
        expected_value: Valor esperado en euros
        stage: Fase ('new', 'qualified', 'proposal', 'won', 'lost')
    """
    # Validate inputs
    try:
        _val = float(expected_value) if isinstance(expected_value, str) else expected_value
        if _val < 0:
            return f"Error: el valor esperado no puede ser negativo (recibido: {expected_value})."
        expected_value = _val
    except (ValueError, TypeError):
        return f"Error: valor esperado inválido '{expected_value}'. Debe ser un número."

    VALID_STAGES = {"new", "qualified", "proposal", "negotiation", "won", "lost"}
    if stage not in VALID_STAGES:
        return f"Error: etapa inválida '{stage}'. Opciones válidas: {', '.join(sorted(VALID_STAGES))}."

    return await _create_opportunity_async(tenant_id, client_nif, title, expected_value, stage)

async def _create_opportunity_async(tenant_id: str, client_nif: str, title: str, expected_value: float, stage: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Client).filter(
                Client.tenant_id == UUID(tenant_id),
                Client.nif == client_nif
            ))
            client = result.scalars().first()

            if not client:
                return f"Error: No se encontro ningun cliente con NIF {client_nif}. Verifica el NIF o usa list_clients."

            opp = Opportunity(
                tenant_id=UUID(tenant_id),
                client_id=client.id,
                title=title,
                expected_value=expected_value,
                stage=stage
            )
            db.add(opp)
            await db.commit()
            await db.refresh(opp)
            return f"Oportunidad '{title}' creada para {client.name} en fase '{stage}'. Valor: {expected_value}EUR. ID: {opp.id}"
    except Exception as e:
        return f"Error creando oportunidad: {str(e)}"


@tool
async def update_opportunity_stage(tenant_id: str, opportunity_id: str, new_stage: str, notes: str = "") -> str:
    """
    Mueve una Oportunidad de Venta de una fase a otra en el Embudo.
    Args:
        tenant_id: ID del tenant
        opportunity_id: ID de la oportunidad a mover
        new_stage: Nueva fase ('new', 'qualified', 'proposal', 'won', 'lost')
        notes: Nota opcional sobre el cambio de etapa
    """
    valid_stages = ['new', 'qualified', 'proposal', 'won', 'lost']
    if new_stage not in valid_stages:
        return f"Error: Fase '{new_stage}' invalida. Usa una de: {valid_stages}."

    return await _update_opportunity_stage_async(tenant_id, opportunity_id, new_stage, notes)

async def _update_opportunity_stage_async(tenant_id: str, opportunity_id: str, new_stage: str, notes: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Opportunity).filter(
                Opportunity.tenant_id == UUID(tenant_id),
                Opportunity.id == UUID(opportunity_id)
            ))
            opp = result.scalars().first()

            if not opp:
                return f"Error: Oportunidad con ID {opportunity_id} no encontrada."

            old_stage = opp.stage
            opp.stage = new_stage
            
            await db.commit()

            msg = f"Oportunidad '{opp.title}' movida de '{old_stage}' a '{new_stage}'."
            if notes:
                msg += f" Nota: {notes}"
            return msg
    except Exception as e:
        return f"Error actualizando oportunidad: {str(e)}"


@tool
async def qualify_leads(tenant_id: str) -> str:
    """
    Analiza todas las oportunidades en fase 'new' y sugiere cuáles cualificar
    basándose en el valor esperado y el tiempo en pipeline.
    Args:
        tenant_id: ID del tenant
    """
    return await _qualify_leads_async(tenant_id)

async def _qualify_leads_async(tenant_id: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Opportunity).filter(
                Opportunity.tenant_id == UUID(tenant_id),
                Opportunity.stage == "new"
            ))
            new_opps = result.scalars().all()

            if not new_opps:
                return "No hay leads en fase 'new' para analizar."

            suggestions = []
            for opp in new_opps:
                # Usa fromtimestamp o convierte de naive a aware de forma robusta
                from datetime import datetime
                if opp.created_at:
                    now = datetime.now(UTC)
                    op_date = opp.created_at
                    if op_date.tzinfo is None:
                        op_date = op_date.replace(tzinfo=UTC)
                    days_in_pipeline = (now - op_date).days
                else:
                    days_in_pipeline = 0
                    
                value = float(opp.expected_value or 0)

                if value > 5000 or days_in_pipeline < 7:
                    priority = "ALTA"
                    action = "Cualificar ahora — llamar al cliente esta semana"
                elif value > 1000:
                    priority = "MEDIA"
                    action = "Enviar propuesta inicial"
                else:
                    priority = "BAJA"
                    action = "Mantener en seguimiento pasivo"

                suggestions.append(
                    f"- [{priority}] {opp.title} | {days_in_pipeline} dias en pipeline | "
                    f"Valor: {value:.2f}EUR → Accion: {action}"
                )

            return (
                f"Analisis de {len(new_opps)} leads en fase 'new':\n" +
                "\n".join(suggestions) +
                "\n\nPuedo mover automaticamente los leads de alta prioridad a 'qualified' si me lo indicas."
            )
    except Exception as e:
        return f"Error analizando leads: {str(e)}"


@tool
async def create_client(
    tenant_id: str,
    name: str,
    nif: str = "",
    email: str = "",
    phone: str = "",
    address: str = "",
    city: str = "",
    postal_code: str = "",
    client_type: str = "customer",
) -> str:
    """
    Crea un nuevo cliente en el sistema.
    Args:
        tenant_id: ID del tenant
        name: Nombre o razón social del cliente (obligatorio)
        nif: NIF/CIF del cliente
        email: Email de contacto
        phone: Teléfono
        address: Dirección
        city: Ciudad
        postal_code: Código postal
        client_type: Tipo de cliente ('customer' o 'supplier')
    """
    from sqlalchemy.exc import IntegrityError
    try:
        async with AsyncSessionLocal() as db:
            from app.db.models.models import Client as ClientModel
            new_client = ClientModel(
                tenant_id=UUID(tenant_id),
                name=name,
                nif=nif or None,
                email=email or None,
                phone=phone or None,
                address=address or None,
                city=city or None,
                postal_code=postal_code or None,
                client_type=client_type,
            )
            db.add(new_client)
            try:
                await db.commit()
                await db.refresh(new_client)
            except IntegrityError:
                await db.rollback()
                return f"Error: Ya existe un cliente con NIF '{nif}' o email '{email}'."
            return f"Cliente '{name}' creado correctamente. ID: {new_client.id}. NIF: {nif or 'no especificado'}."
    except Exception as e:
        return f"Error creando cliente: {str(e)}"


tools = [
    list_opportunities,
    create_opportunity,
    update_opportunity_stage,
    qualify_leads,
    create_client,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
]
def _get_llm_with_tools():
    return _get_llm().bind_tools(tools)


# ─── Nodos del grafo ─────────────────────────────────────────────────────────

async def crm_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=(
                "Eres el Agente Comercial (CRM) de la empresa automatizada.\n"
                "Gestualizas las etapas de los leads y cualificas oportunidades.\n"
                "Tus herramientas:\n"
                "1. list_opportunities: para ver embudos y prospectos.\n"
                "2. qualify_leads: para analizar leads nuevos y rankear a quién contactar.\n"
                "3. update_opportunity_stage: para avanzar deals (won/lost/qualified).\n"
                "4. create_client: para dar de alta un nuevo cliente en el sistema (nombre obligatorio, NIF/email opcionales).\n"
                "5. create_opportunity: si descubres una nueva vía de negocio en un cliente existente.\n"
                "6. create_document: para generar informes en texto o csv y guardarlos en el Gestor Documental.\n"
                "7. Herramientas documentales (list_tenant_documents, get_document_content) "
                "por si necesitas leer emails escaneados, contratos, que contengan información clave.\n"
                f"Tú respondes y decides a partir del ID de Tenant actual: {state.get('tenant_id')}."
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    response = await _get_llm_with_tools().ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"crm_step_{datetime.now().timestamp()}",
        description="Analizando intentención comercial y operando sobre ventas...",
        status="completed",
        action_taken=f"{'Invocando herramientas CRM' if response.tool_calls else 'Asistencia CRM completada.'}"
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def crm_finalize_node(state: AgentState):
    """Cierra el flujo del agente CRM."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="crm_final",
        description="Agente CRM ha finalizado sus operaciones.",
        status="completed",
        action_taken=last_msg.content if isinstance(last_msg.content, str) else "Operaciones en BD completadas."
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ──────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("crm_agent", crm_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", crm_finalize_node)

workflow.set_entry_point("crm_agent")
workflow.add_conditional_edges("crm_agent", tools_condition)
workflow.add_edge("tools", "crm_agent")

graph = workflow.compile()
