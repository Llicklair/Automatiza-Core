"""
Recruitment agent — LangGraph graph definition and node logic.
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import RECRUITMENT_SYSTEM_PROMPT
from .tools import tools


async def recruitment_agent_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0).bind_tools(tools)
    if not state.get("messages"):
        tenant_id = str(state.get("tenant_id") or "")
        prompt_text = RECRUITMENT_SYSTEM_PROMPT.replace("{tenant_id}", tenant_id)
        state["messages"] = [
            make_cached_system_message(prompt_text),
            HumanMessage(content=state.get("user_intent", "Lista los puestos abiertos")),
        ]
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def recruitment_finalize_node(state: AgentState) -> dict:
    last = state["messages"][-1] if state.get("messages") else None
    content = last.content if last and isinstance(last.content, str) else "Operación completada."
    return {
        "status": "done",
        "agent_results": [{"agent": "recruitment", "result": content, "status": "completed"}],
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", recruitment_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", recruitment_finalize_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "finalize"})
workflow.add_edge("tools", "agent")
workflow.add_edge("finalize", END)

graph = workflow.compile()
