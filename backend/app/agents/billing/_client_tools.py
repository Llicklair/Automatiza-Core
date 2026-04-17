"""
Client resolution and search tools for the billing agent.
"""

import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import func, or_, select

from app.db.base import AsyncSessionLocal
from app.db.models.models import Client

logger = logging.getLogger(__name__)


async def _resolve_client(
    tenant_id: str, client_name: str, client_nif: str = ""
) -> "tuple[UUID | None, str, str] | str":
    """
    Busca un cliente por nombre (y opcionalmente NIF).
    Devuelve (client_id, resolved_name, resolved_nif) o un string de error.
    Si se pasa client_nif, omite la búsqueda y devuelve (None, name, nif).
    """
    name = client_name.strip()
    nif = client_nif.strip()
    if nif:
        return None, name, nif
    if not name:
        return "Error: Debes indicar el nombre del cliente o su NIF."

    async with AsyncSessionLocal() as db:
        res = await db.execute(
            select(Client).where(
                Client.tenant_id == UUID(tenant_id),
                func.lower(Client.name) == name.lower(),
            )
        )
        exact = res.scalars().all()
        if len(exact) == 1:
            c = exact[0]
            return c.id, c.name, c.nif or ""
        if len(exact) > 1:
            opts = ", ".join(f"'{c.name}' (NIF: {c.nif or 'N/A'})" for c in exact)
            return f"Error: Hay {len(exact)} clientes con el nombre '{client_name}': {opts}. Especifica el NIF."

        res = await db.execute(
            select(Client)
            .where(
                Client.tenant_id == UUID(tenant_id),
                func.lower(Client.name).contains(name.lower()),
            )
            .order_by(Client.name)
            .limit(5)
        )
        partial = res.scalars().all()
        if len(partial) == 1:
            c = partial[0]
            return c.id, c.name, c.nif or ""
        if len(partial) > 1:
            opts = ", ".join(f"'{c.name}' (NIF: {c.nif or 'N/A'})" for c in partial)
            return (
                f"Error: '{client_name}' coincide con {len(partial)} clientes: {opts}. "
                "Especifica el NIF del cliente para evitar facturar al equivocado."
            )
    return (
        f"Error: No se encontró el cliente '{client_name}'. "
        "Comprueba el nombre o proporciona el NIF directamente."
    )


@tool
async def search_client(tenant_id: str, query: str = "") -> str:
    """
    Busca clientes del tenant por nombre o NIF.
    Útil para encontrar el NIF antes de crear una factura, o para consultas de clientes.

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

            lines = [
                f"- {c.name} | NIF: {c.nif or 'N/A'} | Email: {c.email or 'N/A'} | ID: {c.id}"
                for c in clients
            ]
            return f"Clientes encontrados ({len(clients)}):\n" + "\n".join(lines)
    except Exception as e:
        return f"Error buscando clientes: {e}"
