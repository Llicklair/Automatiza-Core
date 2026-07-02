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
import logging
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.tasks import AgentExecutionTrace

logger = logging.getLogger("services.agent_trace")

# Conversión USD→EUR para el coste estimado. El tracker de uso LLM
# (llm_usage_tracker.estimate_cost) trabaja en USD porque las tarifas de los
# proveedores se publican en USD; la columna `cost_eur` y la UI (modal de
# consumo) muestran €. Constante fija deliberada: el coste es una *estimación*
# orientativa, no una factura — no justifica una llamada a una API de FX.
# Revisar periódicamente junto con _PRICE_TABLE en llm_usage_tracker.
USD_TO_EUR = Decimal("0.92")


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


async def record_task_cost_trace(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    task_id: UUID,
    agent_name: str,
    tokens_in: int,
    tokens_out: int,
    cost_usd: float,
    llm_provider: str | None = None,
    execution_id: UUID | None = None,
) -> AgentExecutionTrace | None:
    """Persiste una traza-resumen con el coste real (tokens + EUR) de una task.

    Atribución a nivel de TASK, no por-agente. Las trazas por-dispatch
    (`_persist_agent_trace`) registran status/latencia para el AI Act, pero NO
    tienen acceso a los tokens de cada llamada LLM: el `UsageTrackingCallback`
    se engancha al grafo vía `config["callbacks"]` y acumula el total de TODA la
    ejecución, sin exponer un delta por dispatch. Exponer tokens por-agente
    exigiría un callback con scope por dispatcher + propagar tokens en el
    `AgentResult` de los 12 dispatchers — coste/riesgo desproporcionado.

    Como la tabla es append-only (triggers SEC.WORM bloquean UPDATE), el coste
    no puede añadirse a las filas ya insertadas; se inserta UNA fila-resumen
    extra. `summarize_task_cost` suma todas las filas de la task, así que el
    total (tokens + €) que ve el modal/dashboard queda correcto.

    Best-effort: nunca propaga errores (igual que el resto de observabilidad).
    """
    if tokens_in + tokens_out <= 0:
        return None
    try:
        cost_eur = (Decimal(str(cost_usd)) * USD_TO_EUR).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
        return await record_agent_execution(
            db,
            tenant_id=tenant_id,
            agent_name=agent_name,
            task_id=task_id,
            execution_id=execution_id,
            llm_provider=llm_provider,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_eur=cost_eur,
            status="ok",
        )
    except Exception as e:  # noqa: BLE001 — observabilidad nunca rompe el flujo
        logger.warning("No se pudo persistir traza de coste de task %s: %s", task_id, e)
        return None
