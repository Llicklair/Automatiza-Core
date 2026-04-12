"""
Billing agent — LangGraph graph definition and node logic.
"""

from datetime import date, datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm

from .prompts import BILLING_SYSTEM_PROMPT
from .tools import tools


def _get_llm():
    return get_llm(temperature=0)


async def billing_agent_node(state: AgentState):
    """Nodo principal: el LLM razona y elige herramientas."""
    today = date.today().isoformat()

    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=BILLING_SYSTEM_PROMPT.format(
                tenant_id=state.get("tenant_id", ""),
                today=today,
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
        step_id=f"billing_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de facturación...",
        status="completed",
        action_taken=(
            "Invocando herramientas de facturación"
            if response.tool_calls
            else "Asistencia de facturación completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def billing_finalize_node(state: AgentState):
    """Cierra el flujo del agente de facturación."""
    last_msg = state["messages"][-1]

    final_result = StepResult(
        step_id="billing_final",
        description="Agente de Facturación ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Operación de facturación completada."
        ),
    )

    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("billing_agent", billing_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", billing_finalize_node)

workflow.set_entry_point("billing_agent")
workflow.add_conditional_edges("billing_agent", tools_condition)
workflow.add_edge("tools", "billing_agent")

graph = workflow.compile()
