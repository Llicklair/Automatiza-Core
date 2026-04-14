"""
CRM agent — LangGraph graph definition and node logic.
"""

from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm

from .tools import tools


def _get_llm():
    return get_llm(temperature=0)


async def crm_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=(
                "Eres el Agente Comercial (CRM) de la empresa automatizada.\n"
                "Gestionas las etapas de los leads y cualificas oportunidades.\n"
                "Tus herramientas:\n"
                "1. list_opportunities: para ver embudos y prospectos.\n"
                "2. qualify_leads: para analizar leads nuevos y rankear a quién contactar.\n"
                "3. update_opportunity_stage: para avanzar deals (won/lost/qualified).\n"
                "4. create_opportunity: si descubres una nueva vía de negocio en un cliente.\n"
                "5. create_document: para generar informes en texto o csv y guardarlos en el Gestor Documental.\n"
                "6. Herramientas documentales (list_tenant_documents, get_document_content) "
                "por si necesitas leer emails escaneados, contratos, que contengan información clave.\n"
                f"Tú respondes y decides a partir del ID de Tenant actual: {state.get('tenant_id')}."
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"crm_step_{datetime.now().timestamp()}",
        description="Analizando intención comercial y operando sobre ventas...",
        status="completed",
        action_taken="Invocando herramientas CRM"
        if response.tool_calls
        else "Asistencia CRM completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def crm_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="crm_final",
        description="Agente CRM ha finalizado sus operaciones.",
        status="completed",
        action_taken=last_msg.content
        if isinstance(last_msg.content, str)
        else "Operaciones en BD completadas.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


workflow = StateGraph(AgentState)
workflow.add_node("crm_agent", crm_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", crm_finalize_node)

workflow.set_entry_point("crm_agent")
workflow.add_conditional_edges("crm_agent", tools_condition)
workflow.add_edge("tools", "crm_agent")

graph = workflow.compile()
