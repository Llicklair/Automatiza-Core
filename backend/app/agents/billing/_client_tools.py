"""
Client resolution helper for the billing agent.
The user-facing `search_client` tool now lives in `agent_tools/clients.py`
because CRM also needs it. This module keeps `_resolve_client`, used
internally by billing to bind a client to an invoice before creation.
"""

import logging
from uuid import UUID

from sqlalchemy import func, select

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
