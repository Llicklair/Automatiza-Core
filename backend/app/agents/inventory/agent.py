"""Inventory (stock) agent — LangGraph graph for stock queries and batch edits."""

from datetime import date, datetime

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import INVENTORY_SYSTEM_PROMPT
from .tools import tools


async def inventory_agent_node(state: AgentState):
    """Nodo principal: el LLM razona y elige herramientas de stock."""
    today = date.today().isoformat()

    if "messages" not in state or not state["messages"]:
        sys_msg = make_cached_system_message(
            INVENTORY_SYSTEM_PROMPT.format(
                tenant_id=state.get("tenant_id", ""),
                today=today,
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    # temperature=0: las operaciones de stock deben ser deterministas.
    llm_with_tools = get_llm(temperature=0).bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"inventory_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de stock...",
        status="completed",
        action_taken=(
            "Invocando herramientas de inventario"
            if response.tool_calls
            else "Asistencia de stock completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def inventory_finalize_node(state: AgentState):
    """Cierra el flujo del agente de stock."""
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="inventory_final",
        description="Agente de Stock ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Operación de inventario completada."
        ),
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


workflow = StateGraph(AgentState)
workflow.add_node("inventory_agent", inventory_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", inventory_finalize_node)

workflow.set_entry_point("inventory_agent")
workflow.add_conditional_edges(
    "inventory_agent", tools_condition, {"tools": "tools", "__end__": "finalize"}
)
workflow.add_edge("tools", "inventory_agent")
workflow.add_edge("finalize", END)

graph = workflow.compile()
