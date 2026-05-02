"""HR agent — agent definition, graph nodes, and LLM orchestration."""

import logging
from datetime import datetime

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.agent_tools.documents import (
    create_document,
    get_document_content,
    list_tenant_documents,
    update_existing_document,
)
from app.agents.agent_tools.knowledge import get_tenant_knowledge, upsert_tenant_knowledge
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import build_system_prompt
from .tools import (
    approve_payroll,
    calculate_and_create_payroll,
    create_employee,
    generate_all_payrolls,
    list_employees,
    list_payrolls,
    update_payroll,
)

logger = logging.getLogger(__name__)


def _get_llm():
    return get_llm(temperature=0)


tools = [
    create_employee,
    calculate_and_create_payroll,
    generate_all_payrolls,
    list_employees,
    list_payrolls,
    update_payroll,
    approve_payroll,
    create_document,
    list_tenant_documents,
    update_existing_document,
    get_document_content,
    get_tenant_knowledge,
    upsert_tenant_knowledge,
]


# ─── Nodos del grafo ──────────────────────────────────────────────────────────


async def hr_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = make_cached_system_message(build_system_prompt(state.get("tenant_id")))
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"hr_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de RRHH...",
        status="completed",
        action_taken=(
            "Invocando herramientas de RRHH"
            if response.tool_calls
            else "Asistencia RRHH completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def hr_finalize_node(state: AgentState):
    """Cierra el flujo del agente de RRHH."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="hr_final",
        description="Agente RRHH ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Borradores generados localmente."
        ),
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("hr_agent", hr_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", hr_finalize_node)

workflow.set_entry_point("hr_agent")
workflow.add_conditional_edges("hr_agent", tools_condition)
workflow.add_edge("tools", "hr_agent")

graph = workflow.compile()
