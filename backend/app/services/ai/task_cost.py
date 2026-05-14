"""Agregador de coste por tarea (UI.COST).

Suma los `AgentExecutionTrace` de una task y devuelve totales de tokens
y EUR estimados. Diseñado para el modal post-abort: al cancelar una task,
el usuario ve "Has consumido N tokens (≈ 0,XX€)".

Aislado por `tenant_id` — un usuario solo puede ver coste de sus tasks.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import AgentExecutionTrace, Task

logger = logging.getLogger("services.task_cost")


async def summarize_task_cost(
    db: AsyncSession, *, tenant_id: UUID, task_id: UUID
) -> dict:
    """Devuelve totales de coste agregando las trazas de ejecución de la task.

    Si la task no existe o no pertenece al tenant, devuelve `None` en
    `task_status` y ceros en métricas — el caller (endpoint) decide si
    eso debe ser 404 o response normal.
    """
    task_q = await db.execute(
        select(Task).where(Task.id == task_id, Task.tenant_id == tenant_id)
    )
    task = task_q.scalar_one_or_none()
    if task is None:
        return {
            "task_id": str(task_id),
            "task_status": None,
            "tokens_in": 0,
            "tokens_out": 0,
            "tokens_total": 0,
            "cost_eur": 0.0,
            "trace_count": 0,
            "agents": [],
        }

    agg_q = await db.execute(
        select(
            func.coalesce(func.sum(AgentExecutionTrace.tokens_in), 0),
            func.coalesce(func.sum(AgentExecutionTrace.tokens_out), 0),
            func.coalesce(func.sum(AgentExecutionTrace.cost_eur), Decimal("0")),
            func.count(AgentExecutionTrace.id),
        ).where(
            AgentExecutionTrace.task_id == task_id,
            AgentExecutionTrace.tenant_id == tenant_id,
        )
    )
    tokens_in, tokens_out, cost_eur, trace_count = agg_q.one()

    # Desglose por agente (para mostrar "billing 1.2k tokens, accounting 800...").
    agents_q = await db.execute(
        select(
            AgentExecutionTrace.agent_name,
            func.coalesce(func.sum(AgentExecutionTrace.tokens_in + AgentExecutionTrace.tokens_out), 0),
            func.coalesce(func.sum(AgentExecutionTrace.cost_eur), Decimal("0")),
        )
        .where(
            AgentExecutionTrace.task_id == task_id,
            AgentExecutionTrace.tenant_id == tenant_id,
        )
        .group_by(AgentExecutionTrace.agent_name)
    )
    agents = [
        {"agent": row[0], "tokens": int(row[1] or 0), "cost_eur": float(row[2] or 0)}
        for row in agents_q.all()
    ]

    return {
        "task_id": str(task_id),
        "task_status": task.status,
        "tokens_in": int(tokens_in or 0),
        "tokens_out": int(tokens_out or 0),
        "tokens_total": int((tokens_in or 0) + (tokens_out or 0)),
        "cost_eur": float(cost_eur or 0),
        "trace_count": int(trace_count or 0),
        "agents": agents,
    }
