"""
Servicio de auditoría.
Registra TODAS las acciones de los agentes en audit_log.
Este módulo es determinista — no usa LLM.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import AuditLog


async def log_action(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    agent_name: str,
    action_type: str,
    status: str,
    task_id: UUID | None = None,
    input_data: dict | None = None,
    output_data: dict | None = None,
    llm_prompt: str | None = None,
    llm_response: str | None = None,
    validation_result: dict | None = None,
    error_detail: str | None = None,
) -> AuditLog:
    """
    Registra una acción en el audit log de forma inmutable.
    Llamar siempre ANTES y DESPUÉS de cualquier acción de agente.
    """
    entry = AuditLog(
        task_id=task_id,
        tenant_id=tenant_id,
        agent_name=agent_name,
        action_type=action_type,
        input_data=input_data,
        output_data=output_data,
        llm_prompt=llm_prompt,
        llm_response=llm_response,
        validation_result=validation_result,
        status=status,
        error_detail=error_detail,
        executed_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.flush()  # Obtener ID sin hacer commit final (lo hace el caller)
    return entry


async def log_llm_call(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    agent_name: str,
    action_type: str,
    prompt: str,
    response: str,
    output_data: dict | None = None,
    task_id: UUID | None = None,
    status: str = "success",
) -> AuditLog:
    """Shortcut específico para registrar llamadas LLM con prompt completo."""
    return await log_action(
        db,
        tenant_id=tenant_id,
        agent_name=agent_name,
        action_type=action_type,
        status=status,
        task_id=task_id,
        llm_prompt=prompt,
        llm_response=response,
        output_data=output_data,
    )
