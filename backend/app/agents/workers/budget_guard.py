"""Budget Guard — Control de presupuesto mensual por AIEmployee.

Verifica que el agente no ha superado su límite de gasto antes de
cada invocación LLM. Si lo supera, pausa el agente y devuelve False.

No lanza HTTPException — el grafo LangGraph lo manejaría mal.
El caller comprueba el retorno y termina el grafo si es False.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import AIEmployee, TokenLedger

logger = logging.getLogger(__name__)


async def check_agent_budget(employee_id: str, db: AsyncSession) -> bool:
    """Devuelve True si el agente tiene presupuesto. False si lo ha superado.

    Efecto secundario cuando False: pausa el agente (status='paused').
    """
    result = await db.execute(select(AIEmployee).where(AIEmployee.id == employee_id))
    employee = result.scalar_one_or_none()
    if not employee:
        return False

    if employee.budget_limit_usd is None:
        return True  # Sin límite configurado

    first_of_month = datetime.now(UTC).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    monthly_spend_result = await db.execute(
        select(func.sum(TokenLedger.cost_usd)).where(
            TokenLedger.employee_id == employee_id,
            TokenLedger.created_at >= first_of_month,
        )
    )
    monthly_spend = monthly_spend_result.scalar() or 0

    if monthly_spend >= employee.budget_limit_usd:
        employee.status = "paused"
        await db.commit()
        logger.warning(
            "Empleado '%s' pausado por presupuesto agotado (%.4f$ / %.2f$)",
            employee.name,
            monthly_spend,
            employee.budget_limit_usd,
        )
        return False

    return True


async def record_token_usage(
    db: AsyncSession,
    tenant_id: str,
    employee_id: str,
    prompt_tokens: int,
    completion_tokens: int,
    llm_provider: str,
    task_id: str | None = None,
) -> None:
    """Registra el coste de una invocación LLM en token_ledger.

    Estimación de coste por defecto para Anthropic Claude Sonnet (ajustar si cambia provider).
    No hace commit — el caller gestiona la transacción.
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
