"""
Dispatcher de compliance fiscal.
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary
from app.agents.orchestrator.helpers import _save_ai_result_as_document

logger = logging.getLogger(__name__)


async def _dispatch_compliance(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de compliance fiscal."""
    from app.agents.compliance_agent import run_compliance_agent

    agent_result = await run_compliance_agent(
        user_intent=state.get("current_intent", state["user_intent"]),
        tenant_id=state["tenant_id"],
    )

    # Guardar resultado como documento si fue exitoso
    if agent_result.success:
        content_parts = []
        if agent_result.respuesta_consulta:
            content_parts.append(f"Respuesta: {agent_result.respuesta_consulta}")
        if agent_result.alertas_redactadas:
            content_parts.append("Alertas:\n" + "\n".join(f"- {a}" for a in agent_result.alertas_redactadas))
        if agent_result.vencimientos_proximos:
            content_parts.append("Vencimientos:\n" + "\n".join(f"- {v}" for v in agent_result.vencimientos_proximos))
        if agent_result.resumen_boe:
            content_parts.append(f"Novedades BOE: {agent_result.resumen_boe}")
        await _save_ai_result_as_document(
            tenant_id=state["tenant_id"],
            task_id=state["task_id"],
            category="fiscal",
            title=f"Informe Fiscal IA — {state['user_intent'][:60]}",
            content="\n\n".join(content_parts) if content_parts else "Análisis completado sin contenido exportable.",
        )

    _compliance_output = {
        "action":               agent_result.action,
        "vencimientos":         agent_result.vencimientos_proximos,
        "alertas":              agent_result.alertas_redactadas,
        "boe_novedades":        agent_result.boe_novedades,
        "resumen_boe":          agent_result.resumen_boe,
        "respuesta_consulta":   agent_result.respuesta_consulta,
    }
    return {
        "subtask_id": subtask["id"],
        "agent": "compliance",
        "success": agent_result.success,
        "output": _compliance_output,
        "summary": _format_summary("compliance", _compliance_output, agent_result.success, agent_result.error),
        "error": agent_result.error,
    }
