"""Helper para registrar trazas de ejecución de agentes (SEC.WORM + AI Act).

Cumplimiento Art. 12 Reglamento UE 2024/1689 — log automático de cada
invocación con retención ≥ 6 meses. Las trazas son append-only (triggers
PL/pgSQL en Postgres + comportamiento documentado en código).

El patrón típico desde un agente LangGraph:

    from app.services.observability.agent_trace import record_agent_execution

    await record_agent_execution(
        db,
        tenant_id=tenant_id,
        agent_name="billing",
        prompt_text=full_prompt,
        output_text=agent_output,
        llm_provider="anthropic",
        llm_model="claude-3-7-sonnet",
        tokens_in=1200,
        tokens_out=420,
        duration_ms=2350,
    )
"""

import hashlib
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import AgentExecutionTrace


def _sha256_hex(text: str | None) -> str | None:
    if text is None:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


async def record_agent_execution(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    agent_name: str,
    prompt_text: str | None = None,
    output_text: str | None = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    prompt_version: str | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
    cost_eur: Decimal | None = None,
    duration_ms: int | None = None,
    execution_id: UUID | None = None,
    task_id: UUID | None = None,
    status: str = "ok",
    error_class: str | None = None,
) -> AgentExecutionTrace:
    """Persiste una traza append-only de una ejecución del agente.

    `prompt_text` y `output_text` NO se persisten en plano — solo su SHA-256.
    Esto minimiza superficie PII en logs y reduce coste de almacenamiento.
    Si se requiere el contenido completo para auditoría externa, la fuente
    son los prompts versionados en BD (AI.4) más los outputs en `audit_log`
    según política de retención.
    """
    trace = AgentExecutionTrace(
        tenant_id=tenant_id,
        execution_id=execution_id,
        task_id=task_id,
        agent_name=agent_name,
        llm_provider=llm_provider,
        llm_model=llm_model,
        prompt_hash=_sha256_hex(prompt_text),
        prompt_version=prompt_version,
        tool_calls_json=tool_calls,
        output_hash=_sha256_hex(output_text),
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_eur=cost_eur,
        duration_ms=duration_ms,
        status=status,
        error_class=error_class,
    )
    db.add(trace)
    await db.flush()
    return trace
