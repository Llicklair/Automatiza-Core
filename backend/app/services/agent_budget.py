"""Agent budget management — control de presupuesto mensual por AIEmployee.

Verifica que el agente no ha superado su limite de gasto antes de cada
invocacion LLM. Si lo supera, pausa el agente y devuelve False.

No lanza HTTPException — el grafo LangGraph lo manejaria mal. El caller
comprueba el retorno y termina el grafo si es False.

Este modulo vive en `services/` (no en `agents/workers/`) porque es
budget management generico, no logica de agente. Lo usan tanto el
orchestrator (via shim en agents/workers/) como services/integration.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import AIEmployee, TokenLedger

logger = logging.getLogger(__name__)

# Umbral de alerta blanda: a partir del 80% del presupuesto mensual avisamos al
# usuario (toast) antes del hard-stop al 100%.
BUDGET_WARN_RATIO = 0.8


async def get_budget_status(employee_id: str, db: AsyncSession) -> dict | None:
    """Estado de presupuesto mensual de un empleado (solo lectura, sin efectos).

    Retorna None si el empleado no existe. Si no tiene límite configurado,
    `state='unlimited'`. En otro caso `state` es 'ok' | 'warning' (>=80%) |
    'exhausted' (>=100%). Es la única fuente del cálculo de gasto mensual:
    `check_agent_budget` y el heartbeat la reutilizan.
    """
    result = await db.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        return None

    if employee.budget_limit_usd is None:
        return {
            "state": "unlimited",
            "spend_usd": 0.0,
            "limit_usd": None,
            "ratio": 0.0,
            "name": employee.name,
        }

    limit = float(employee.budget_limit_usd)
    first_of_month = datetime.now(UTC).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    monthly_spend_result = await db.execute(
        select(func.sum(TokenLedger.cost_usd)).where(
            TokenLedger.employee_id == employee_id,
            TokenLedger.created_at >= first_of_month,
        )
    )
    spend = float(monthly_spend_result.scalar() or 0)
    ratio = spend / limit if limit > 0 else 1.0
    if ratio >= 1.0:
        state = "exhausted"
    elif ratio >= BUDGET_WARN_RATIO:
        state = "warning"
    else:
        state = "ok"

    return {
        "state": state,
        "spend_usd": spend,
        "limit_usd": limit,
        "ratio": ratio,
        "name": employee.name,
    }


async def check_agent_budget(employee_id: str, db: AsyncSession) -> bool:
    """Devuelve True si el agente tiene presupuesto. False si lo ha superado.

    Efecto secundario cuando False: pausa el agente (status='paused').
    """
    status = await get_budget_status(employee_id, db)
    if status is None:
        return False
    if status["state"] in ("unlimited", "ok", "warning"):
        return True

    # exhausted → pausar
    await db.execute(
        update(AIEmployee).where(AIEmployee.id == employee_id).values(status="paused")
    )
    await db.commit()
    logger.warning(
        "Empleado '%s' pausado por presupuesto agotado (%.4f$ / %.2f$)",
        status["name"],
        status["spend_usd"],
        status["limit_usd"],
    )
    return False


async def record_token_usage(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    llm_provider: str,
    task_id: str | None = None,
) -> None:
    """Registra el coste de una invocacion LLM en token_ledger.

    Estimacion de coste por defecto para Anthropic Claude Sonnet
    (ajustar si cambia provider). No hace commit — el caller gestiona
    la transaccion.
    """
    # Coste estimado: claude-sonnet ~$3/MTok input + $15/MTok output
    cost_usd = (prompt_tokens / 1000) * 0.003 + (completion_tokens / 1000) * 0.015

    entry = TokenLedger(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        employee_id=employee_id,
        task_id=task_id,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        llm_provider=llm_provider,
    )
    db.add(entry)
