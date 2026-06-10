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
from app.db.models.marketing import Campaign, ScheduledPost, SocialAccount
from app.services.autonomy_gate import gated_tool
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


@tool
@gated_tool(
    domain="marketing",
    summary_fn=lambda kwargs: (
        f"Programar campaña «{kwargs.get('name', '?')}» con "
        f"{len(kwargs.get('posts') or [])} posts en redes sociales"
    ),
)
async def create_campaign(
    tenant_id: str,
    name: str,
    posts: list[dict],
    description: Optional[str] = None,
) -> str:
    """
    Crea una campaña de marketing y programa sus posts para publicación
    automática. Los posts quedan en estado 'scheduled' y el publicador los
    enviará a cada red social en la fecha indicada. Por la política de
    autonomía (CONFIRM por defecto) la campaña puede quedar pendiente de
    aprobación humana antes de programarse.

    Args:
        tenant_id: ID del tenant actual
        name: Nombre de la campaña (ej: "Lanzamiento colección verano")
        posts: Lista de posts. Cada post es un dict con claves:
            platform (twitter|linkedin|facebook|instagram),
            social_account_id (de list_social_accounts),
            content (texto completo con emojis y hashtags),
            scheduled_at (ISO 8601, ej: 2026-06-15T10:00:00Z),
            image_url (opcional, de search_image)
        description: Objetivo de la campaña (opcional)
    """
    try:
        if not posts:
            return "Error: la campaña necesita al menos un post"

        tenant_uuid = UUID(tenant_id)
        parsed: list[dict] = []
        for i, p in enumerate(posts, 1):
            missing = {"platform", "social_account_id", "content", "scheduled_at"} - set(p)
            if missing:
                return f"Error: al post #{i} le faltan campos: {', '.join(sorted(missing))}"
            try:
                sched = datetime.fromisoformat(str(p["scheduled_at"]).replace("Z", "+00:00"))
            except ValueError:
                return f"Error: scheduled_at inválido en post #{i}: {p['scheduled_at']}"
            parsed.append({**p, "_sched": sched})

        async with AsyncSessionLocal() as db:
            acc_ids = {p["social_account_id"] for p in parsed}
            result = await db.execute(
                select(SocialAccount.id).where(
                    SocialAccount.id.in_([UUID(a) for a in acc_ids]),
                    SocialAccount.tenant_id == tenant_uuid,
                    SocialAccount.is_active.is_(True),
                )
            )
            valid = {str(r) for r in result.scalars().all()}
            invalid = acc_ids - valid
            if invalid:
                return f"Error: cuentas sociales no encontradas o inactivas: {', '.join(sorted(invalid))}"

            campaign = Campaign(
                tenant_id=tenant_uuid,
                name=name,
                description=description,
                start_date=min(p["_sched"] for p in parsed),
                end_date=max(p["_sched"] for p in parsed),
            )
            db.add(campaign)
            await db.flush()

            for p in parsed:
                db.add(ScheduledPost(
                    tenant_id=tenant_uuid,
                    campaign_id=campaign.id,
                    social_account_id=UUID(p["social_account_id"]),
                    platform=p["platform"],
                    content=p["content"],
                    image_url=p.get("image_url"),
                    scheduled_at=p["_sched"],
                    status="scheduled",
                ))
            await db.commit()
            campaign_id = campaign.id

        return (
            f"Campaña «{name}» creada | ID={campaign_id} | {len(parsed)} posts programados. "
            "El publicador los enviará automáticamente en cada fecha."
        )

    except Exception as e:
        logger.error("Error creando campaña: %s", e)
        return f"Error al crear campaña: {e}"


tools = [get_product_catalog, search_image, list_social_accounts, create_post, create_campaign, create_pdf_report, create_pdf_text_report]


# Defensa multi-tenant: envolver tools para forzar tenant_id del ContextVar
from app.agents.tenant_context import isolated as _isolated

tools = _isolated(tools)
