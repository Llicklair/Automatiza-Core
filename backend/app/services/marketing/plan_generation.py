"""Service: generate marketing plan via agent + deterministic fallback.

SEC.AUT contract: in MANUAL mode the fallback MUST NOT create drafts.
The autonomy gate check is positioned BEFORE any db.add() call — do not reorder.
"""

import asyncio
import datetime
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.marketing import ScheduledPost, SocialAccount

_logger = logging.getLogger(__name__)


# ── Image helper (route-local, moved here; used only by generate_plan) ─────────

async def _search_images_bounded(
    queries: list[str], *, timeout: float = 15.0
) -> list[Optional[str]]:
    """Busca imágenes en paralelo con un timeout GLOBAL.

    Devuelve una lista alineada con `queries`; cada elemento es la URL o None.
    Evita el cuelgue de la request HTTP cuando el proxy de imágenes (Render)
    está frío: N búsquedas en serie podían sumar minutos. Si expira el timeout
    global, devuelve None para todas (la imagen no es bloqueante: los posts son
    borradores editables).
    """
    from app.services.marketing.image_search import search_image

    async def _one(q: str) -> Optional[str]:
        try:
            img = await search_image(q)
            return img if isinstance(img, str) and img else None
        except Exception:
            return None

    if not queries:
        return []
    try:
        return await asyncio.wait_for(
            asyncio.gather(*(_one(q) for q in queries)),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return [None] * len(queries)


# ── Public service function ─────────────────────────────────────────────────────

async def generate_plan(
    db: AsyncSession,
    tenant_id: UUID,
    prompt: str,
) -> tuple[str, list[str]]:
    """Orchestrate the full plan-generation flow and return (summary, post_ids).

    All business logic from the /agent/generate route lives here verbatim.
    The route keeps only auth deps + input validation + delegate + build response.
    """
    from app.agents.marketing import run_agent

    run_started = datetime.datetime.now(datetime.timezone.utc)

    async def _created_since():
        # Posts creados EN ESTA EJECUCIÓN, en cualquier estado: borradores
        # (create_post) y programados de campaña (create_campaign → scheduled).
        r = await db.execute(
            select(ScheduledPost)
            .where(
                ScheduledPost.tenant_id == tenant_id,
                ScheduledPost.created_at >= run_started,
            )
            .order_by(ScheduledPost.created_at.desc())
            .limit(50)
        )
        return r.scalars().all()

    results = await run_agent(prompt=prompt, tenant_id=str(tenant_id))
    created = await _created_since()

    if not created:
        # El modelo respondió preguntando/ofreciendo opciones en vez de crear.
        # Reintenta UNA vez forzando la acción (algunos modelos ignoran la regla
        # del system prompt según el fraseo del usuario).
        forced = (
            prompt
            + "\n\n[INSTRUCCIÓN OBLIGATORIA] No preguntes ni ofrezcas opciones: crea "
            "YA los posts con create_campaign (varios) o create_post (uno) para TODAS "
            "las cuentas conectadas. Debes dejar la campaña/borradores creados."
        )
        results = await run_agent(prompt=forced, tenant_id=str(tenant_id))
        created = await _created_since()

    # ── Fallback determinista: si el agente (claude_code) NO creó nada, generamos
    # un plan básico desde el catálogo, sin depender del LLM. Borradores editables.
    fallback_used = False
    fallback_blocked_manual = False
    if not created:
        from app.db.models.inventory import Product
        from app.services.autonomy_gate import evaluate_autonomy

        # Respeta SEC.AUT: en modo MANUAL el tenant pidió "solo sugerir, no crear",
        # así que crear borradores aquí saltándose el gate violaría ese contrato.
        # En CONFIRM (default de marketing) los borradores SÍ son válidos: son la
        # "acción preparada" que el humano publica luego con un clic explícito.
        decision = await evaluate_autonomy(
            db,
            tenant_id=tenant_id,
            domain="marketing",
            action_summary="Generar plan de marketing (borradores) desde el catálogo",
        )
        if decision.mode == "MANUAL":
            fallback_blocked_manual = True
        else:
            prod_res = await db.execute(
                select(Product)
                .where(Product.tenant_id == tenant_id)
                .order_by(Product.created_at.desc())
                .limit(3)
            )
            products = prod_res.scalars().all()
            acc_res = await db.execute(
                select(SocialAccount).where(
                    SocialAccount.tenant_id == tenant_id,
                    SocialAccount.is_active.is_(True),
                )
            )
            accounts = acc_res.scalars().all()

            if products and accounts:
                # Imágenes en paralelo con timeout global (no en serie): el proxy
                # de Render puede estar frío y N búsquedas secuenciales colgaban
                # la request HTTP. Sin imagen → None (editable después).
                imgs = await _search_images_bounded([p.name for p in products])
                for day, (prod, img) in enumerate(zip(products, imgs, strict=False), start=1):
                    price = f"{prod.price:.0f}€" if prod.price else ""
                    desc = (prod.description or "").strip()
                    hook = desc[:180] if desc else "La solución que tu empresa necesita para dar el siguiente paso."
                    tag = "".join(ch for ch in (prod.name.split()[0] if prod.name else "") if ch.isalnum()).lower()
                    cuerpo = (
                        f"✨ {prod.name}" + (f" · {price}" if price else "") + "\n\n"
                        + f"{hook}\n\n"
                        + "👉 Escríbenos y te asesoramos sin compromiso.\n\n"
                        + f"#pyme #negocio{(' #' + tag) if tag else ''}"
                    )
                    for acc in accounts:
                        db.add(ScheduledPost(
                            tenant_id=tenant_id,
                            social_account_id=acc.id,
                            platform=acc.platform,
                            content=cuerpo[:280] if acc.platform == "twitter" else cuerpo[:2200],
                            image_url=img,
                            scheduled_at=run_started + datetime.timedelta(days=day, hours=10),
                            status="draft",
                        ))
                await db.commit()
                created = await _created_since()
                fallback_used = bool(created)

    # ── Red de seguridad determinista ─────────────────────────────────────────
    # El LLM a veces ignora plataformas (solo crea 1 red) o no añade imagen. Aquí
    # garantizamos, sin depender del modelo: (1) un post por CADA cuenta conectada
    # (replicando contenido si falta), y (2) una imagen en todos los posts.
    if created:
        acc_res = await db.execute(
            select(SocialAccount).where(
                SocialAccount.tenant_id == tenant_id,
                SocialAccount.is_active.is_(True),
            )
        )
        accounts = acc_res.scalars().all()
        covered = {p.platform for p in created}
        template = created[0]

        # (1) Cobertura: crea un post espejo en cada plataforma sin post.
        for acc in accounts:
            if acc.platform not in covered:
                mirror = ScheduledPost(
                    tenant_id=tenant_id,
                    social_account_id=acc.id,
                    platform=acc.platform,
                    content=template.content,
                    image_url=template.image_url,
                    scheduled_at=template.scheduled_at,
                    status=template.status,
                )
                db.add(mirror)
                created.append(mirror)
                covered.add(acc.platform)

        # (2) Imágenes: rellena las que falten en paralelo con timeout global
        # (Instagram las exige). Si el proxy está frío, no cuelga la request.
        missing = [p for p in created if not p.image_url]
        if missing:
            imgs = await _search_images_bounded([p.content[:80] for p in missing])
            for p, img in zip(missing, imgs, strict=False):
                if img:
                    p.image_url = img

        await db.commit()

    post_ids = [str(p.id) for p in created]
    if fallback_blocked_manual:
        agent_text = results[0].get("result", "") if results else ""
        summary = (
            "Tu política de marketing está en modo MANUAL: te propongo el plan, "
            "pero no creo borradores automáticamente. Revísalo y créalos tú, o "
            "cambia la autonomía a 'Confirmar' en Ajustes.\n\n" + agent_text
        ).strip()
    elif fallback_used:
        summary = (
            f"Plan básico generado desde tu catálogo: {len(created)} posts en borrador "
            "con imagen, listos para que los edites y publiques."
        )
    else:
        summary = results[0].get("result", "Plan generado.") if results else "Plan generado."

    return summary, post_ids
