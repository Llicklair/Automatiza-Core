"""Guard de aislamiento multi-tenant para escrituras de FK (anti IDOR cross-tenant).

Compartido por los servicios que escriben claves foráneas venidas del payload
(projects, crm, sales): evita asignar/enlazar filas de OTRO tenant y la
enumeración de IDs entre tenants. Fuente única — antes había 3 copias idénticas.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def assert_fk_in_tenant(
    db: AsyncSession,
    model: type,
    entity_id: UUID | None,
    tenant_id: UUID,
    label: str,
) -> None:
    """Reject a foreign key pointing to another tenant's row (cross-tenant IDOR).

    No-op when ``entity_id`` is None (the FK is optional). Raises LookupError when the
    referenced row does not exist within ``tenant_id`` — the same 'not found' semantics
    the services use, so a caller cannot assign across tenants nor probe which IDs exist
    in other tenants.
    """
    if entity_id is None:
        return
    found = await db.execute(
        select(model.id).where(model.id == entity_id, model.tenant_id == tenant_id)
    )
    if found.scalar_one_or_none() is None:
        raise LookupError(f"{label} not found")
