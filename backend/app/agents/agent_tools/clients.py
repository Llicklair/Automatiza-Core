"""
Shared client lookup tools.
Live here (not under a single agent) because client search is needed
across domains: billing (resolve client before invoice), CRM (look up
customer by NIF), etc.
"""

from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import func, or_, select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client


@tool
async def search_client(tenant_id: str, query: str = "") -> str:
    """
    Busca clientes del tenant por nombre o NIF.
    Útil para encontrar el NIF antes de crear una factura, para consultas
    de clientes desde el CRM, o para resolver datos de contacto.

    Args:
        tenant_id: ID del tenant
        query: Texto a buscar (nombre parcial o NIF). Si vacío, lista los primeros 10 clientes.
    """
    return await _search_client_async(tenant_id, query)


async def _search_client_async(tenant_id: str, query: str) -> str:
    try:
        async with AsyncSessionLocal() as db:
            base_q = select(Client).where(Client.tenant_id == UUID(tenant_id))
            if query.strip():
                q = query.strip()
                base_q = base_q.where(
                    or_(
                        func.lower(Client.name).contains(q.lower()),
                        Client.nif.ilike(f"%{q}%"),
                    )
                )
            base_q = base_q.order_by(Client.name).limit(10)

            result = await db.execute(base_q)
            clients = result.scalars().all()

            if not clients:
                return f"No se encontraron clientes{' con búsqueda: ' + query if query else ''}."

            lines = [f"- {c.name} | NIF: {c.nif or 'N/A'} | Email: {c.email or 'N/A'} | ID: {c.id}" for c in clients]
            return f"Clientes encontrados ({len(clients)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error buscando clientes: {e}"
