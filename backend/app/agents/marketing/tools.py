"""Marketing agent — tools: catálogo, búsqueda de imágenes y creación de posts."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from langchain_core.tools import tool
from sqlalchemy import select

from app.agents.agent_tools.reports import create_pdf_report, create_pdf_text_report
from app.db.base import AsyncSessionLocal
from app.db.models.inventory import Product
from app.db.models.marketing import ScheduledPost, SocialAccount
from app.services.marketing.image_search import search_image as _search_image

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


@tool
async def search_image(query: str, tenant_id: str = "") -> str:
    """
    Busca una imagen de stock relevante en Unsplash para ilustrar un post.
    Devuelve la URL de la imagen o un aviso si no hay clave configurada.
    Úsala para cada post del plan de contenidos.

    `tenant_id` se acepta por consistencia con el resto de tools de marketing
    (el LLM lo pasa siempre) pero se ignora: Unsplash es un recurso global.
    """
    url = await _search_image(query)
    if url:
        return url
    return "Sin imagen disponible (configura UNSPLASH_ACCESS_KEY para activar búsqueda de imágenes)"


@tool
async def list_social_accounts(tenant_id: str) -> str:
    """
    Lista las cuentas de redes sociales conectadas del tenant con sus IDs.
    Llama a esta herramienta ANTES de create_post para obtener los social_account_id válidos.
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.tenant_id == UUID(tenant_id),
                    SocialAccount.is_active.is_(True),
                )
            )
            accounts = result.scalars().all()

        if not accounts:
            return "No hay cuentas sociales conectadas. El usuario debe conectar sus redes en la pestaña Cuentas."

        lines = [f"- {a.platform} | ID={a.id} | @{a.account_name or a.account_id}" for a in accounts]
        return "\n".join(lines)

    except Exception as e:
        logger.warning("Error listando cuentas: %s", e)
        return f"Error: {e}"


@tool
async def create_post(
    tenant_id: str,
    platform: str,
    content: str,
    social_account_id: str,
    image_url: Optional[str] = None,
    scheduled_at: Optional[str] = None,
) -> str:
    """
    Crea un post borrador en la base de datos listo para revisión y publicación.
    El post queda en estado 'draft' hasta que el usuario lo apruebe desde el frontend.

    Args:
        tenant_id: ID del tenant actual
        platform: Red social (twitter, linkedin, facebook, instagram)
        content: Texto completo del post con emojis y hashtags
        social_account_id: ID de la cuenta social (obtenido de list_social_accounts)
        image_url: URL de imagen (opcional, obtenida de search_image)
        scheduled_at: Fecha/hora programada ISO 8601 (opcional, ej: 2026-06-10T19:00:00Z)
    """
    try:
        async with AsyncSessionLocal() as db:
            acc_result = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.id == UUID(social_account_id),
                    SocialAccount.tenant_id == UUID(tenant_id),
                    SocialAccount.is_active.is_(True),
                )
            )
            if not acc_result.scalar_one_or_none():
                return f"Error: cuenta social {social_account_id} no encontrada para el tenant"

            sched_dt = None
            if scheduled_at:
                try:
                    sched_dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                except ValueError:
                    return f"Error: formato de scheduled_at inválido: {scheduled_at}"

            post = ScheduledPost(
                tenant_id=UUID(tenant_id),
                social_account_id=UUID(social_account_id),
                platform=platform,
                content=content,
                image_url=image_url,
                scheduled_at=sched_dt,
                status="draft",
            )
            db.add(post)
            await db.commit()
            await db.refresh(post)

        return f"Post creado | ID={post.id} | platform={platform} | status=draft"

    except Exception as e:
        logger.error("Error creando post: %s", e)
        return f"Error al crear post: {e}"


tools = [get_product_catalog, search_image, list_social_accounts, create_post, create_pdf_report, create_pdf_text_report]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
