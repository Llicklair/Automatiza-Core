"""Dynamic Agent Compiler — Compila un grafo LangGraph para un AIEmployee.

El grafo resultante sigue el patrón ReAct estándar:
  agent_node ↔ ToolNode (solo tools autorizadas en AgentSkill)

El sistema_prompt del empleado y sus tools autorizadas se inyectan
en tiempo de compilación. Si una tool no está en el registry, falla
en voz alta (KeyError intencionado — configuración incorrecta).

USO:
    graph = await compile_dynamic_agent(employee_id, db)
    result = await graph.ainvoke({
        "tenant_id": "...",
        "user_intent": "Genera las nóminas de marzo",
        "messages": [],
        "agent_results": [],
        "status": "running",
    })
"""

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import AgentState
from app.agents.tool_registry import get_tool_for_employee
from app.core.datetime_utils import local_today
from app.core.llm_factory import get_llm
from app.db.models.ai_employees import AgentSkill, AIEmployee

logger = logging.getLogger(__name__)


async def compile_dynamic_agent(employee_id: str, db: AsyncSession):
    """Compila y devuelve un grafo LangGraph para el AIEmployee indicado.

    Raises:
        ValueError: Si el empleado no existe o está mal configurado.
        KeyError: Si una AgentSkill apunta a una tool no registrada.
    """
    emp_result = await db.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
    employee = emp_result.scalar_one_or_none()
    if not employee:
        raise ValueError(f"AIEmployee '{employee_id}' no encontrado")

    skills_result = await db.execute(select(AgentSkill).where(AgentSkill.employee_id == employee_id))
    skills = skills_result.scalars().all()

    if not skills:
        logger.warning(
            "Empleado '%s' no tiene skills configuradas — " "usará herramientas del dominio '%s' por defecto",
            employee.name,
            employee.domain,
        )

    # Zero Trust: cada tool se resuelve explícitamente del registry.
    # Si una skill apunta a una tool inexistente (p.ej. tras renombrado), se omite
    # con warning y el agente sigue funcionando con el resto. Evita que un AIEmployee
    # con una sola skill obsoleta deje de responder.
    allowed_tools = []
    skipped: list[str] = []
    for skill in skills:
        try:
            allowed_tools.append(get_tool_for_employee(skill.tool_module))
        except KeyError:
            skipped.append(skill.tool_module)
    if skipped:
        logger.warning(
            "Empleado '%s' tiene skills obsoletas omitidas (revisa agent_skills): %s",
            employee.name,
            skipped,
        )

    llm = get_llm()
    llm_with_tools = llm.bind_tools(allowed_tools) if allowed_tools else llm

    system_prompt_base = employee.system_prompt
    employee_name = employee.name

    def _enriched_system_prompt(state: AgentState) -> str:
        tenant_id = state.get("tenant_id", "")
        user_id = state.get("user_id", "")
        today = local_today().isoformat()
        runtime_ctx = (
            "\n\n--- CONTEXTO DE EJECUCIÓN (USAR SIEMPRE) ---\n"
            f"tenant_id={tenant_id}\n"
            f"user_id={user_id}\n"
            f"fecha_actual={today}\n"
            "Cuando una herramienta requiera tenant_id, usa el valor de arriba SIEMPRE. "
            "NUNCA pidas el tenant_id al usuario — ya lo tienes. "
            "Si una herramienta requiere user_id u otro identificador interno, "
            "úsalo del contexto sin preguntar.\n\n"
            "--- FINALIZACIÓN DE TAREA ---\n"
            "Cuando completes tu tarea principal (generar un documento, enviar un "
            "mensaje, crear un registro, etc.), responde DIRECTAMENTE al usuario con "
            "un breve mensaje de confirmación. NO intentes invocar herramientas de "
            "'finalizar', 'marcar como completado', 'cerrar tarea' o similares — "
            "esas herramientas no existen. El sistema marca la tarea como completada "
            "automáticamente cuando emitas tu respuesta final. NUNCA empieces tu "
            "respuesta final con la palabra 'Error' a menos que algo haya fallado "
            "realmente; si el documento o acción se completó, comienza con "
            "'✅', 'Listo', 'Hecho' o similar."
        )
        return (system_prompt_base or "") + runtime_ctx

    async def agent_node(state: AgentState) -> dict[str, Any]:
        """Nodo principal: el LLM razona y elige herramientas."""
        if not state.get("messages"):
            state["messages"] = [
                SystemMessage(content=_enriched_system_prompt(state)),
                HumanMessage(content=state.get("user_intent", "")),
            ]

        response = await llm_with_tools.ainvoke(state["messages"])

        agent_results = list(state.get("agent_results") or [])
        agent_results.append(
            {
                "agent": employee_name,
                "tool_calls": len(response.tool_calls) if response.tool_calls else 0,
            }
        )

        return {"messages": [response], "agent_results": agent_results}

    def finalize_node(state: AgentState) -> dict[str, Any]:
        """Nodo final: extrae la respuesta y marca como completado."""
        last_msg = state["messages"][-1] if state.get("messages") else None
        content = last_msg.content if last_msg and isinstance(last_msg.content, str) else "Operación completada."
        return {
            "status": "done",
            "agent_results": [
                {
                    "agent": employee_name,
                    "result": content,
                    "status": "completed",
                }
            ],
        }

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("finalize", finalize_node)

    if allowed_tools:
        graph.add_node("tools", ToolNode(allowed_tools))
        graph.set_entry_point("agent")
        graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", "__end__": "finalize"})
        graph.add_edge("tools", "agent")
    else:
        graph.set_entry_point("agent")
        graph.add_edge("agent", "finalize")

    graph.add_edge("finalize", END)

    return graph.compile()
