"""
Dispatchers misceláneos: RAG, Excel, Email, Workflow, Skill.
Agrupados por ser relativamente pequeños.
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import _save_ai_result_as_document

logger = logging.getLogger(__name__)


async def _dispatch_rag(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de RAG para consulta de documentos."""
    from app.agents.rag_agent import run_rag_agent

    tenant_id = state["tenant_id"]

    agent_result = await run_rag_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=tenant_id,
        top_k=5
    )

    # Guardar respuesta RAG como documento en el Escáner
    if agent_result.success:
        sources = agent_result.sources_used
        if isinstance(sources, (list, tuple, set)):
            sources_str = ', '.join(str(s) for s in sources)
        else:
            sources_str = str(sources) if sources else 'N/A'

        await _save_ai_result_as_document(
            tenant_id=tenant_id,
            task_id=state["task_id"],
            category="informes",
            title=f"Consulta Documental — {state['user_intent'][:60]}",
            content=f"Pregunta: {subtask.get('params', {}).get('intent')}\n\nRespuesta:\n{agent_result.answer}\n\nFuentes: {sources_str}"
        )

    _rag_output = {
        "answer": agent_result.answer,
        "sources_used": agent_result.sources_used,
    }
    return {
        "subtask_id": subtask["id"],
        "agent": "rag",
        "success": agent_result.success,
        "output": _rag_output,
        "summary": _format_summary("rag", _rag_output, agent_result.success, agent_result.error),
        "error": agent_result.error,
    }


async def _dispatch_excel(state: OrchestratorState, subtask: dict) -> AgentResult:
    from app.agents.excel_agent import run_excel_agent

    agent_result = await run_excel_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=state["tenant_id"],
        task_id=state["task_id"]
    )

    return {
        "subtask_id": subtask["id"],
        "agent": "excel",
        "success": agent_result.success,
        "output": {"message": agent_result.output_message},
        "error": agent_result.error,
    }


async def _dispatch_email(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de email y guarda su resultado como documento."""
    from app.agents.email_agent import run_email_agent

    agent_result = await run_email_agent(
        user_intent=subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"])),
        tenant_id=state["tenant_id"],
        task_id=state["task_id"]
    )

    action = agent_result.action or "Operación de email completada."

    # Guardar siempre el resultado en el Scanner bajo la categoría correos
    try:
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="correos",
            title=f"Email: {state['user_intent'][:50]}...",
            content=action
        )
    except Exception as e:
        logger.warning(f"Error al archivar log de email: {e}")

    _email_output = {"action": action}
    return {
        "subtask_id": subtask["id"],
        "agent": "email",
        "success": agent_result.success,
        "output": _email_output,
        "summary": _format_summary("email", _email_output, agent_result.success, agent_result.error),
        "error": agent_result.error,
    }


async def _dispatch_workflow(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de gestión de Workflows / Automatizaciones."""
    from app.agents.workflow_agent import run_workflow_agent

    agent_result = await run_workflow_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=state["tenant_id"],
        user_id=state.get("user_id"),
        task_id=state.get("task_id"),
    )

    # Guardar configuración de automatización como documento
    if agent_result.success:
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="automatizaciones",
            title=f"Nueva Regla: {agent_result.workflow_name}",
            content=f"Acción: {agent_result.action}\nID: {agent_result.workflow_id}\n\nDetalle del plan:\n{agent_result.data}"
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


async def _dispatch_skill(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca una Habilidad Modular (Skill) del registro dinámico."""
    from app.skills.registry import SkillRegistry

    agent_name = subtask["agent"]
    skill_name = agent_name
    if skill_name.startswith("skill:"):
        skill_name = skill_name[6:]

    # Intentar obtener de params si el agente es genérico 'skill'
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
        # Fallback: intentar cargar builtins si por algún motivo no están
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
        # Ejecutar la skill
        payload = subtask.get("params", {})
        tenant_id = state.get("tenant_id")

        # Si la skill es asíncrona
        import inspect
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
