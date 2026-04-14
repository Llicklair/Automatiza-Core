"""
Compliance agent — LangGraph graph definition and node logic.
"""

from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm
from app.prompts import load_prompt

from .tools import tools

COMPLIANCE_SYSTEM_PROMPT = load_prompt("compliance_agent")


def _get_llm():
    return get_llm(temperature=0.1)


async def compliance_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=COMPLIANCE_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"compliance_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de compliance...",
        status="completed",
        action_taken="Invocando herramientas de compliance"
        if response.tool_calls
        else "Asistencia compliance completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def compliance_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="compliance_final",
        description="Agente de Compliance ha finalizado.",
        status="completed",
        action_taken=last_msg.content
        if isinstance(last_msg.content, str)
        else "Operación compliance completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


workflow = StateGraph(AgentState)
workflow.add_node("compliance_agent", compliance_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", compliance_finalize_node)

workflow.set_entry_point("compliance_agent")
workflow.add_conditional_edges("compliance_agent", tools_condition)
workflow.add_edge("tools", "compliance_agent")

graph = workflow.compile()
