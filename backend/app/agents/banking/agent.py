"""
Banking agent node + LangGraph graph builder.
"""

import logging
from datetime import UTC
from datetime import datetime as dt

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import BANKING_SYSTEM_PROMPT
from .tools import tools

logger = logging.getLogger(__name__)


async def banking_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = make_cached_system_message(
            BANKING_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = get_llm(temperature=0).bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"banking_step_{dt.now(UTC).timestamp()}",
        description="Procesando solicitud bancaria...",
        status="completed",
        action_taken="Invocando herramientas bancarias"
        if response.tool_calls
        else "Asistencia bancaria completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def banking_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="banking_final",
        description="Agente Bancario ha finalizado.",
        status="completed",
        action_taken=last_msg.content
        if isinstance(last_msg.content, str)
        else "Operación bancaria completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("banking_agent", banking_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", banking_finalize_node)

workflow.set_entry_point("banking_agent")
workflow.add_conditional_edges(
    "banking_agent", tools_condition, {"tools": "tools", "__end__": "finalize"}
)
workflow.add_edge("tools", "banking_agent")
workflow.add_edge("finalize", END)

graph = workflow.compile()
