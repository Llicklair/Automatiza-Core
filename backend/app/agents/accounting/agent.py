"""Accounting agent — LangGraph graph for accounting and journal entries."""

from datetime import date, datetime

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.agents.base import AgentState
from app.agents.types import StepResult
from app.core.llm_factory import get_llm, make_cached_system_message

from .prompts import ACCOUNTING_SYSTEM_PROMPT
from .tools import (
    create_journal_entry,
    get_account_balance,
    get_profit_loss_summary,
    list_fixed_assets,
    list_journal_entries,
)

tools = [
    create_journal_entry,
    list_journal_entries,
    get_account_balance,
    get_profit_loss_summary,
    list_fixed_assets,
    create_pdf_report,
    create_pdf_text_report,
]

# Defensa multi-tenant (SEC): ignorar el tenant_id que pase el LLM y usar
# SIEMPRE el del ContextVar activo, igual que el resto de agentes. Sin esto, el
# agente de contabilidad confiaba en el tenant_id del LLM (protegido solo por la
# RLS ambiente). enforce_tenant es no-op si no hay contexto activo (tests).
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)


async def accounting_agent_node(state: AgentState):
    """Nodo principal: el LLM razona y elige herramientas contables."""
    today = date.today().isoformat()

    if "messages" not in state or not state["messages"]:
        sys_msg = make_cached_system_message(
            ACCOUNTING_SYSTEM_PROMPT.format(
                tenant_id=state.get("tenant_id", ""),
                today=today,
            )
        )
        user_msg = HumanMessage(content=state["user_intent"])
        extra_init_messages = [sys_msg, user_msg]
        state["messages"] = extra_init_messages
    else:
        extra_init_messages = []

    llm_with_tools = get_llm(temperature=0).bind_tools(tools)
    response = await llm_with_tools.ainvoke(state["messages"])

    result_log = StepResult(
        step_id=f"accounting_step_{datetime.now().timestamp()}",
        description="Procesando solicitud de contabilidad...",
        status="completed",
        action_taken=(
            "Invocando herramientas de contabilidad"
            if response.tool_calls
            else "Asistencia contable completada."
        ),
    )

    if "agent_results" not in state:
        state["agent_results"] = []

    state["agent_results"].append(result_log.model_dump())
    return {"messages": extra_init_messages + [response], "agent_results": state["agent_results"]}


def accounting_finalize_node(state: AgentState):
    """Cierra el flujo del agente de contabilidad."""
    last_msg = state["messages"][-1]
    final_result = StepResult(
        step_id="accounting_final",
        description="Agente de Contabilidad ha finalizado.",
        status="completed",
        action_taken=(
            last_msg.content
            if isinstance(last_msg.content, str)
            else "Operación contable completada."
        ),
    )
    return {"status": "done", "agent_results": [final_result.model_dump()]}


workflow = StateGraph(AgentState)
workflow.add_node("accounting_agent", accounting_agent_node)
workflow.add_node("tools", ToolNode(tools))
workflow.add_node("finalize", accounting_finalize_node)

workflow.set_entry_point("accounting_agent")
workflow.add_conditional_edges(
    "accounting_agent", tools_condition, {"tools": "tools", "__end__": "finalize"}
)
workflow.add_edge("tools", "accounting_agent")
workflow.add_edge("finalize", END)

graph = workflow.compile()
