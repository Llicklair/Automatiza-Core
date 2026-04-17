"""Node handlers: summarize_node."""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.orchestrator.state import AgentResult, OrchestratorState, TaskStatus
from app.core.llm_factory import get_llm

logger = logging.getLogger(__name__)


async def summarize_node(state: OrchestratorState) -> dict:
    """
    Genera un resumen en lenguaje natural de los resultados de los agentes.
    Se salta si el dominio es 'chat' (ya devuelve texto conversacional).
    """
    if state.get("classified_domain") == "chat":
        return state
    if state.get("status") != TaskStatus.DONE:
        return state

    results = state.get("agent_results", [])
    if not results:
        return state

    try:
        results_text = []
        for r in results:
            agent = r.get("agent", "?")
            output = r.get("output", {})
            response = output.get("response", "") or output.get("message", "")
            summary = r.get("summary", "")
            text = response if response else summary
            if text:
                results_text.append(f"[{agent}]: {text[:500]}")

        if not results_text:
            return state

        prompt = (
            "Eres el asistente de AutomatizaPyme. El usuario pidió lo siguiente:\n"
            f'"{state["user_intent"]}"\n\n'
            "Los agentes han devuelto estos resultados:\n" + "\n".join(results_text) + "\n\n"
            "Genera un RESUMEN EJECUTIVO breve y claro en español para el usuario. "
            "Usa lenguaje natural, no técnico. Si hay acciones urgentes, destácalas. "
            "Formato: texto directo, usa listas si mejora la legibilidad."
        )

        llm = get_llm(temperature=0.3)
        response = await asyncio.wait_for(
            llm.ainvoke(
                [
                    SystemMessage(
                        content="Resumes resultados de agentes ERP para PYMEs españolas. Sé conciso y directo."
                    ),
                    HumanMessage(content=prompt),
                ]
            ),
            timeout=30,
        )

        summary_text = response.content.strip() if response.content else ""
        if summary_text:
            summary_result: AgentResult = {
                "subtask_id": "summary",
                "agent": "summary",
                "success": True,
                "output": {"action": "chat_response", "response": summary_text},
                "summary": summary_text[:200],
                "error": None,
            }
            return {
                **state,
                "agent_results": list(results) + [summary_result],
            }
    except Exception as e:
        logger.warning("Error generando resumen conversacional: %s", e)

    return state
