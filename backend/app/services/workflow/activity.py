"""Helper para escribir entradas en el activity_feed.

Usado desde tools y agentes al completar una acción significativa.
NO llama a db.commit() — la transacción la gestiona el caller.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_employees import ActivityEntry


async def log_activity(
    db: AsyncSession,
    tenant_id: str,
    category: str,
    message: str,
    employee_id: str | None = None,
    task_id: str | None = None,
    icon: str = "📋",
    metadata: dict | None = None,
) -> ActivityEntry:
    """Registra una acción completada en el timeline de actividad.

    El mensaje debe estar en primera persona desde la perspectiva
    del empleado virtual: "He enviado...", "He generado...", etc.

    No hace commit — el caller es responsable de la transacción.
    """
    def _to_uuid(val):
        return uuid.UUID(val) if isinstance(val, str) else val

    entry = ActivityEntry(
        id=uuid.uuid4(),
        tenant_id=_to_uuid(tenant_id),
        employee_id=_to_uuid(employee_id) if employee_id else None,
        task_id=_to_uuid(task_id) if task_id else None,
        category=category,
        icon=icon,
        message=message,
        metadata_json=metadata,
    )
    db.add(entry)
    return entry
