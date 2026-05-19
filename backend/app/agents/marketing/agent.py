"""
Marketing agent — LangGraph graph definition and node logic.
"""

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import MARKETING_SYSTEM_PROMPT
from .tools import tools


async def marketing_agent_node(state: AgentState) -> dict:
    llm = get_llm(temperature=0.4).bind_tools(tools)
    if not state.get("messages"):
        # Sustituir el placeholder {tenant_id} con el real antes de cachear.
        # Sin esto el LLM ve el literal "{tenant_id}" y pide al usuario que
        # lo proporcione.
        tenant_id = str(state.get("tenant_id") or "")
        prompt_text = MARKETING_SYSTEM_PROMPT.replace("{tenant_id}", tenant_id)
        state["messages"] = [
            make_cached_system_message(prompt_text),
            HumanMessage(
                content=state.get("user_intent", "Genera un plan de contenidos para este mes")
            ),
        ]
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def marketing_finalize_node(state: AgentState) -> dict:
    last = state["messages"][-1] if state.get("messages") else None
    content = last.content if last and isinstance(last.content, str) else "Plan generado."
    return {
        "status": "done",
        "agent_results": [{"agent": "marketing", "result": content, "status": "completed"}],
    }


workflow = StateGraph(AgentState)
workflow.add_node("agent", marketing_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", marketing_finalize_node)
workflow.set_entry_point("agent")
workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "finalize"})
workflow.add_edge("tools", "agent")
workflow.add_edge("finalize", END)

graph = workflow.compile()
