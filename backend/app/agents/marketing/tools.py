"""
Marketing agent — tools: catálogo de productos.
"""

from __future__ import annotations

import logging
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.db.base import AsyncSessionLocal
from app.db.models.inventory import Product

logger = logging.getLogger(__name__)


@tool
async def get_product_catalog(tenant_id: str) -> str:
    """
    Obtiene el catálogo de productos/servicios del tenant.
    Devuelve nombre, descripción y precio de hasta 20 productos activos.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product)
                .where(Product.tenant_id == UUID(tenant_id))
                .order_by(Product.created_at.desc())
                .limit(20)
            )
            products = result.scalars().all()

        if not products:
            return "Sin productos registrados. Generar contenido de marca genérico."

        lines = []
        for p in products:
            price = f"{p.price:.2f}€" if p.price else "precio no definido"
            desc = p.description or ""
            lines.append(f"- {p.name} | {price} | {desc[:120]}")
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Error obteniendo catálogo: %s", e)
        return f"Error al obtener catálogo: {e}"


tools = [get_product_catalog]
