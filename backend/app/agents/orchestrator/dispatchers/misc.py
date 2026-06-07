"""
Dispatchers misceláneos: RAG, Excel, Email, Workflow, Skill.
Todos invocan agentes autónomos via LangGraph graph.ainvoke.
"""

import inspect
import logging

from app.agents.orchestrator.helpers import (
    _messages_already_generated_pdf,
    _save_ai_result_as_document,
)
from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.skills.registry import SkillRegistry

logger = logging.getLogger(__name__)


def _extract_final_text(result_state: dict) -> str:
    """Extrae el texto final del último mensaje del agente."""
    messages = result_state.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return ""


async def _run_graph_agent(
    graph, state: OrchestratorState, subtask: dict, agent_name: str, category: str
) -> AgentResult:
    """Patrón genérico para ejecutar un agente LangGraph y devolver AgentResult."""
    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get(
        "intent", state.get("current_intent", state["user_intent"])
    )

    try:
        result_state = await graph.ainvoke(
            {
                "tenant_id": tenant_id,
                "task_id": state.get("task_id"),
                "user_id": state.get("user_id"),
                "user_intent": intent,
                "current_intent": intent,
                "messages": [],
                "agent_results": [],
                "status": "running",
            }
        )

        final_text = _extract_final_text(result_state)
        is_error = final_text.lower().startswith("error")
        success = not is_error

        output = {"action": "completed" if success else "failed", "response": final_text}

        # No duplicar si el agente ya creó un PDF profesional por su cuenta.
        messages = result_state.get("messages", [])
        if success and final_text and not _messages_already_generated_pdf(messages):
            await _save_ai_result_as_document(
                tenant_id=tenant_id,
                task_id=state["task_id"],
                category=category,
                title=f"{agent_name.capitalize()} — {state['user_intent'][:60]}",
                content=final_text,
            )

        return {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": success,
            "output": output,
            "summary": _format_summary(
                agent_name, output, success, None if success else final_text
            ),
            "error": None if success else final_text,
        }

    except Exception as e:
        logger.exception("Error en %s agent graph", agent_name)
        return {
            "subtask_id": subtask["id"],
            "agent": agent_name,
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente {agent_name}: {e}",
            "error": str(e),
        }


async def _dispatch_rag(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente RAG autónomo."""
    from app.agents.rag import graph

    return await _run_graph_agent(graph, state, subtask, "rag", "informes")


async def _dispatch_excel(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de Excel autónomo."""
    from app.agents.excel import graph

    return await _run_graph_agent(graph, state, subtask, "excel", "informes")


async def _dispatch_email(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de email autónomo."""
    try:
        from app.agents.email import run_email_agent

        agent_result = await run_email_agent(
            user_intent=subtask.get("params", {}).get(
                "intent", state.get("current_intent", state["user_intent"])
            ),
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
        )

        # El agente email devuelve en `agent_result.action` el texto multilínea
        # del LLM (no un slug). Separamos: action queda como slug corto
        # (email_sent/failed) y la respuesta completa va a output.response,
        # que es lo que _format_summary y la UI esperan leer.
        final_text = agent_result.action or "Operación de email completada."

        try:
            await _save_ai_result_as_document(
                tenant_id=state["tenant_id"],
                task_id=state["task_id"],
                category="correos",
                title=f"Email: {state['user_intent'][:50]}...",
                content=final_text,
            )
        except Exception as e:
            logger.warning("Error al archivar log de email: %s", e)

        _email_output = {
            "action": "email_sent" if agent_result.success else "failed",
            "response": final_text,
        }
        return {
            "subtask_id": subtask["id"],
            "agent": "email",
            "success": agent_result.success,
            "output": _email_output,
            "summary": _format_summary(
                "email", _email_output, agent_result.success, agent_result.error
            ),
            "error": agent_result.error,
        }
    except Exception as e:
        logger.exception("Error en email agent")
        return {
            "subtask_id": subtask["id"],
            "agent": "email",
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente de email: {e}",
            "error": str(e),
        }


async def _dispatch_workflow(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de gestión de Workflows / Automatizaciones."""
    try:
        from app.agents.workflow import run_workflow_agent

        agent_result = await run_workflow_agent(
            user_intent=state.get("current_intent", state["user_intent"]),
            tenant_id=state["tenant_id"],
            user_id=state.get("user_id"),
            task_id=state.get("task_id"),
        )

        if agent_result.success:
            await _save_ai_result_as_document(
                tenant_id=state["tenant_id"],
                task_id=state["task_id"],
                category="automatizaciones",
                title=f"Nueva Regla: {agent_result.workflow_name}",
                content=f"Acción: {agent_result.action}\nID: {agent_result.workflow_id}\n\nDetalle del plan:\n{agent_result.data}",
            )

        return {
            "subtask_id": subtask["id"],
            "agent": "workflow",
            "success": agent_result.success,
            "output": {
                "action": agent_result.action,
                "workflow_id": agent_result.workflow_id,
                "workflow_name": agent_result.workflow_name,
                "plan": agent_result.data,
            },
            "error": agent_result.error,
        }
    except Exception as e:
        logger.exception("Error en workflow agent")
        return {
            "subtask_id": subtask["id"],
            "agent": "workflow",
            "success": False,
            "output": {"action": "failed", "error": str(e)},
            "summary": f"Error en agente de workflow: {e}",
            "error": str(e),
        }


async def _dispatch_skill(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca una Habilidad Modular (Skill) del registro dinámico."""
    agent_name = subtask["agent"]
    skill_name = agent_name
    if skill_name.startswith("skill:"):
        skill_name = skill_name[6:]

    if skill_name == "skill":
        skill_name = subtask.get("params", {}).get("skill_name")

    if not skill_name:
        return {
            "subtask_id": subtask["id"],
            "agent": "skill",
            "success": False,
            "output": {},
            "error": "No se especificó el nombre de la Skill a ejecutar.",
        }

    skill = SkillRegistry.get_skill(skill_name)
    if not skill:
        SkillRegistry.load_builtins()
        skill = SkillRegistry.get_skill(skill_name)

    if not skill:
        return {
            "subtask_id": subtask["id"],
            "agent": "skill",
            "success": False,
            "output": {},
            "error": f"La Skill '{skill_name}' no está registrada en el sistema.",
        }

    try:
        payload = subtask.get("params", {})
        tenant_id = state.get("tenant_id")

        if inspect.iscoroutinefunction(skill.run):
            result_data = await skill.run(payload, tenant_id=tenant_id)
        else:
            result_data = skill.run(payload, tenant_id=tenant_id)

        return {
            "subtask_id": subtask["id"],
            "agent": f"skill:{skill_name}",
            "success": True,
            "output": result_data,
            "error": None,
        }
    except Exception as e:
        return {
            "subtask_id": subtask["id"],
            "agent": f"skill:{skill_name}",
            "success": False,
            "output": {},
            "error": f"Error ejecutando Skill '{skill_name}': {str(e)}",
        }
