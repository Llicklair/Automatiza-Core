"""
Dispatcher de Recursos Humanos (HR agent).
"""
import logging

from app.agents.orchestrator.state import AgentResult, OrchestratorState
from app.agents.orchestrator.utils import _format_summary, _extract_month_year
from app.agents.orchestrator.helpers import _save_ai_result_as_document

logger = logging.getLogger(__name__)


async def _dispatch_hr(state: OrchestratorState, subtask: dict) -> AgentResult:
    """Invoca el agente de Recursos Humanos — modo determinista:
    1. Extrae NIF del prompt usando el LLM.
    2. Llama directamente a _create_payroll_async para crear la nómina y PDF.
    3. Guarda el resultado como documento visible.
    """
    import re
    import uuid

    from sqlalchemy import select

    from app.db.base import AsyncSessionLocal
    from app.db.models.models import Employee
    from app.agents.hr_agent import _create_payroll_async

    tenant_id = state["tenant_id"]
    intent = subtask.get("params", {}).get("intent", state.get("current_intent", state["user_intent"]))

    # Extraer NIF del intent con regex (patrón español: 8 dígitos + letra)
    nif_match = re.search(r'\b(\d{8}[A-Z])\b', intent.upper())
    nif = nif_match.group(1) if nif_match else None

    # Extraer mes/año del intent con lógica robusta de lenguaje natural
    month, year = _extract_month_year(intent)

    action_taken = ""
    success = True

    try:
        if not nif:
            # Si no hay NIF en el prompt, tomar el primer empleado activo
            async with AsyncSessionLocal() as db:
                emp_result = await db.execute(
                    select(Employee).where(
                        Employee.tenant_id == uuid.UUID(tenant_id),
                        Employee.status == "active"
                    ).limit(1)
                )
                emp = emp_result.scalars().first()
                nif = emp.nif if emp else None

        if not nif:
            action_taken = "No se encontró ningún empleado activo en RRHH."
            success = False
        else:
            action_taken = await _create_payroll_async(tenant_id, nif, month, year, 0.0)
    except Exception as e:
        success = False
        action_taken = f"Error generando nómina: {str(e)}"

    # Guardar resumen como documento txt adicional en el Escáner
    await _save_ai_result_as_document(
        tenant_id=tenant_id,
        task_id=state["task_id"],
        category="nominas",
        title=f"Resultado Nómina IA — {state['user_intent'][:60]}",
        content=action_taken
    )

    _hr_output = {"action": action_taken}
    return {
        "subtask_id": subtask["id"],
        "agent": "hr",
        "success": success,
        "output": _hr_output,
        "summary": _format_summary("hr", _hr_output, success, None if success else action_taken),
        "error": None if success else action_taken,
    }
