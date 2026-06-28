"""
RAG agent — LangGraph graph definition and node logic.
"""

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import RAG_SYSTEM_PROMPT
from .tools import tools


async def rag_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = make_cached_system_message(
            RAG_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = get_llm(temperature=0).bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"rag_step_{datetime.now(UTC).timestamp()}",
        description="Procesando consulta documental...",
        status="completed",
        action_taken="Buscando en documentos"
        if response.tool_calls
        else "Consulta documental completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def rag_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="rag_final",
        description="Agente RAG ha finalizado.",
        status="completed",
        action_taken=last_msg.content
        if isinstance(last_msg.content, str)
        else "Consulta documental completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


workflow = StateGraph(AgentState)
workflow.add_node("rag_agent", rag_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", rag_finalize_node)

workflow.set_entry_point("rag_agent")
workflow.add_conditional_edges("rag_agent", tools_condition)
workflow.add_edge("tools", "rag_agent")

graph = workflow.compile()
