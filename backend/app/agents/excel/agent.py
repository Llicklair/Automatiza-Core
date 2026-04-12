"""
Agente de Excel — Autónomo con LangGraph.

El LLM decide qué herramientas usar según la intención del usuario:
  - Exportar datos del ERP a Excel -> export_erp_data
  - Transformar archivos subidos -> transform_uploaded_files
  - Listar datos disponibles -> list_available_datasets

Cada herramienta ejecuta lógica determinista (BD, openpyxl, pandas).
"""

from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm

from .prompts import EXCEL_SYSTEM_PROMPT
from .tools import tools


def _get_llm():
    return get_llm(temperature=0)


async def excel_agent_node(state: AgentState):
    if "messages" not in state or not state["messages"]:
        sys_msg = SystemMessage(
            content=EXCEL_SYSTEM_PROMPT.format(tenant_id=state.get("tenant_id", ""))
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = _get_llm().bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"excel_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de Excel...",
        status="completed",
        action_taken="Invocando herramientas de Excel"
        if response.tool_calls
        else "Asistencia Excel completada.",
    )

    if "agent_results" not in state:
        state["agent_results"] = []
    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def excel_finalize_node(state: AgentState):
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="excel_final",
        description="Agente de Excel ha finalizado.",
        status="completed",
        action_taken=last_msg.content
        if isinstance(last_msg.content, str)
        else "Operación Excel completada.",
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


# ─── Compilar grafo ───────────────────────────────────────────────────────────

workflow = StateGraph(AgentState)
workflow.add_node("excel_agent", excel_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", excel_finalize_node)

workflow.set_entry_point("excel_agent")
workflow.add_conditional_edges("excel_agent", tools_condition)
workflow.add_edge("tools", "excel_agent")

graph = workflow.compile()
