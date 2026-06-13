"""Marketing: social accounts, campaigns, scheduled posts, OAuth callbacks."""

import datetime
import traceback
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.paths import app_data_dir
from app.db.base import get_db
from app.db.models.marketing import Campaign, ScheduledPost, SocialAccount
from app.db.models.models import User
from app.services.encryption import encrypt_str
from app.services.marketing.oauth import (
    _decode_state,
    _encode_state,
    _exchange_token,
    _fetch_profile,
    _oauth_url,
    _resolve_facebook_page,
    _resolve_instagram_account,
)

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _log_oauth_error(stage: str, exc: Exception) -> None:
    """Vuelca el traceback completo del fallo OAuth a oauth_debug.log (diagnóstico)."""
    try:
        p = app_data_dir("oauth_debug.log")
        p.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with p.open("a", encoding="utf-8") as f:
            f.write(f"\n===== {ts} · {stage} =====\n")
            f.write(f"{type(exc).__name__}: {exc!r}\n")
            f.write(traceback.format_exc())
    except Exception:
        pass


def _popup_html(success: bool, platform: str = "", message: str = "") -> HTMLResponse:
    if success:
        body = f"""
            <div class="icon">✓</div>
            <h2>{platform.capitalize()} conectado</h2>
            <p>Puedes cerrar esta ventana.</p>
        """
        script = """
            if (window.opener) {
                window.opener.postMessage({ type: 'oauth-complete' }, '*');
            }
            setTimeout(() => window.close(), 1800);
        """
    else:
        body = f"""
            <div class="icon error">✗</div>
            <h2>Error al conectar</h2>
            <p>{message}</p>
        """
        script = "setTimeout(() => window.close(), 15000);"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>{'Conectado' if success else 'Error'}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; display: flex; align-items: center;
           justify-content: center; min-height: 100vh; margin: 0;
           background: #0f0f0f; color: #e5e5e5; text-align: center; }}
    .card {{ padding: 2rem; border-radius: 12px; background: #1a1a1a;
             border: 1px solid #333; max-width: 300px; }}
    .icon {{ font-size: 2.5rem; margin-bottom: 0.75rem; }}
    .icon.error {{ color: #f87171; }}
    h2 {{ margin: 0 0 0.5rem; font-size: 1.1rem; }}
    p {{ margin: 0; color: #999; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="card">{body}</div>
  <script>{script}</script>
</body>
</html>"""
    return HTMLResponse(html)


# ── Schemas ────────────────────────────────────────────────────────────────────


class SocialAccountOut(BaseModel):
    id: UUID
    platform: str
    account_id: str
    account_name: Optional[str] = None
    is_active: bool
    token_expires_at: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None


class CampaignOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    is_active: bool

    model_config = {"from_attributes": True}


class PostCreate(BaseModel):
    social_account_id: UUID
    platform: str
    content: str
    image_url: Optional[str] = None
    campaign_id: Optional[UUID] = None
    scheduled_at: Optional[datetime.datetime] = None


class PostOut(BaseModel):
    id: UUID
    platform: str
    content: str
    image_url: Optional[str] = None
    scheduled_at: Optional[datetime.datetime] = None
    published_at: Optional[datetime.datetime] = None
    status: str
    platform_post_id: Optional[str] = None
    error_message: Optional[str] = None
    social_account_id: UUID
    campaign_id: Optional[UUID] = None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Accounts ───────────────────────────────────────────────────────────────────


@router.get("/accounts", response_model=list[SocialAccountOut])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == current_user.tenant_id,
            SocialAccount.is_active.is_(True),
        )
    )
    return result.scalars().all()


@router.post("/accounts/connect/{platform}", status_code=status.HTTP_200_OK)
async def connect_account(
    platform: str,
    current_user: User = Depends(get_current_user),
):
    supported = {"instagram", "facebook", "linkedin", "twitter"}
    if platform not in supported:
        raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {platform}")

    state = _encode_state(platform, str(current_user.tenant_id))
    auth_url = _oauth_url(platform, state)
    return {"auth_url": auth_url}


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.tenant_id == current_user.tenant_id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    account.is_active = False
    await db.commit()


# ── OAuth Callback ─────────────────────────────────────────────────────────────


@router.get("/oauth/callback")
async def oauth_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Callback OAuth — recibe el code del proveedor, intercambia por token y guarda la cuenta."""

    if error:
        return _popup_html(False, message=f"El usuario denegó el acceso: {error}")

    if not code or not state:
        detail = f"code={'sí' if code else 'NO'} · state={'sí' if state else 'NO'} · error={error!r}"
        _log_oauth_error("callback-incompleto", Exception(detail))
        return _popup_html(False, message=f"Parámetros de callback incompletos ({detail})")

    try:
        platform, tenant_id_str = _decode_state(state)
        tenant_id = UUID(tenant_id_str)
    except Exception:
        return _popup_html(False, message="Estado OAuth inválido o expirado")

    try:
        token_data = await _exchange_token(platform, code, state)
    except HTTPException as e:
        _log_oauth_error(f"exchange:{platform}", e)
        return _popup_html(False, message=str(e.detail))
    except Exception as e:
        _log_oauth_error(f"exchange:{platform}", e)
        return _popup_html(False, message=f"Error al obtener token: {e!r}")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=int(expires_in))

    if platform in ("facebook", "instagram"):
        # Facebook: Page token (no se publica en perfiles personales).
        # Instagram: cuenta Business vinculada a una página; se publica con el
        # Page token y el IG user id. En ambos el token es de larga duración.
        resolver = _resolve_facebook_page if platform == "facebook" else _resolve_instagram_account
        try:
            target = await resolver(access_token)
        except HTTPException as e:
            _log_oauth_error(f"resolve:{platform}", e)
            return _popup_html(False, message=str(e.detail))
        except Exception as e:
            _log_oauth_error(f"resolve:{platform}", e)
            return _popup_html(False, message=f"Error al resolver la cuenta de {platform}: {e!r}")
        access_token = target["access_token"]
        account_id_str, account_name = target["id"], target["name"]
        token_expires_at = None
        refresh_token = None
    else:
        try:
            account_id_str, account_name = await _fetch_profile(platform, access_token)
        except Exception:
            account_id_str, account_name = "", ""

    # Upsert: si ya existe una cuenta para esta plataforma+account_id, actualiza el token
    existing = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.platform == platform,
            SocialAccount.account_id == account_id_str,
        )
    )
    account = existing.scalar_one_or_none()

    enc_access = encrypt_str(access_token)
    enc_refresh = encrypt_str(refresh_token) if refresh_token else None

    if account:
        account.access_token = enc_access
        account.refresh_token = enc_refresh
        account.token_expires_at = token_expires_at
        account.account_name = account_name
        account.is_active = True
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            platform=platform,
            account_id=account_id_str or "unknown",
            account_name=account_name,
            access_token=enc_access,
            refresh_token=enc_refresh,
            token_expires_at=token_expires_at,
        )
        db.add(account)

    await db.commit()
    return _popup_html(True, platform=platform)


# ── Campaigns ──────────────────────────────────────────────────────────────────


@router.get("/campaigns", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Campaign)
        .where(Campaign.tenant_id == current_user.tenant_id)
        .order_by(Campaign.created_at.desc())
    )
    return result.scalars().all()


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    campaign = Campaign(
        tenant_id=current_user.tenant_id,
        name=body.name,
        description=body.description,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("/campaigns/{campaign_id}/metrics")
async def campaign_metrics(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Métricas agregadas de una campaña (impresiones, alcance y engagement por post).

    Devuelve la última métrica conocida de cada post (el job diario las refresca).
    """
    from app.services.marketing.metrics import get_campaign_metrics

    result = await db.execute(
        select(Campaign).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == current_user.tenant_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return await get_campaign_metrics(db, current_user.tenant_id, campaign_id)


# ── Posts ──────────────────────────────────────────────────────────────────────


@router.get("/posts", response_model=list[PostOut])
async def list_posts(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(ScheduledPost).where(ScheduledPost.tenant_id == current_user.tenant_id)
    if status_filter:
        q = q.where(ScheduledPost.status == status_filter)
    q = q.order_by(
        ScheduledPost.scheduled_at.asc().nulls_last(),
        ScheduledPost.created_at.desc(),
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    acc = await db.execute(
        select(SocialAccount).where(
            SocialAccount.id == body.social_account_id,
            SocialAccount.tenant_id == current_user.tenant_id,
            SocialAccount.is_active.is_(True),
        )
    )
    if not acc.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Cuenta social no encontrada")

    post = ScheduledPost(
        tenant_id=current_user.tenant_id,
        social_account_id=body.social_account_id,
        campaign_id=body.campaign_id,
        platform=body.platform,
        content=body.content,
        image_url=body.image_url,
        scheduled_at=body.scheduled_at,
        status="scheduled" if body.scheduled_at else "draft",
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == current_user.tenant_id,
            ScheduledPost.status != "published",
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado o ya publicado")
    await db.delete(post)
    await db.commit()


# ── Agent: generar plan ────────────────────────────────────────────────────────


class GeneratePlanRequest(BaseModel):
    prompt: str


class GeneratePlanResponse(BaseModel):
    summary: str
    post_ids: list[str]


@router.post("/agent/generate", response_model=GeneratePlanResponse)
async def generate_plan(
    body: GeneratePlanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Llama al agente de marketing con un prompt y crea los posts en DB."""
    from app.agents.marketing import run_agent

    run_started = datetime.datetime.now(datetime.timezone.utc)

    async def _created_since():
        # Posts creados EN ESTA EJECUCIÓN, en cualquier estado: borradores
        # (create_post) y programados de campaña (create_campaign → scheduled).
        r = await db.execute(
            select(ScheduledPost)
            .where(
                ScheduledPost.tenant_id == current_user.tenant_id,
                ScheduledPost.created_at >= run_started,
            )
            .order_by(ScheduledPost.created_at.desc())
            .limit(50)
        )
        return r.scalars().all()

    results = await run_agent(prompt=body.prompt, tenant_id=str(current_user.tenant_id))
    created = await _created_since()

    if not created:
        # El modelo respondió preguntando/ofreciendo opciones en vez de crear.
        # Reintenta UNA vez forzando la acción (algunos modelos ignoran la regla
        # del system prompt según el fraseo del usuario).
        forced = (
            body.prompt
            + "\n\n[INSTRUCCIÓN OBLIGATORIA] No preguntes ni ofrezcas opciones: crea "
            "YA los posts con create_campaign (varios) o create_post (uno) para TODAS "
            "las cuentas conectadas. Debes dejar la campaña/borradores creados."
        )
        results = await run_agent(prompt=forced, tenant_id=str(current_user.tenant_id))
        created = await _created_since()

    # ── Fallback determinista: si el agente (claude_code) NO creó nada, generamos
    # un plan básico desde el catálogo, sin depender del LLM. Borradores editables.
    fallback_used = False
    if not created:
        from app.db.models.inventory import Product
        from app.services.marketing.image_search import search_image

        prod_res = await db.execute(
            select(Product)
            .where(Product.tenant_id == current_user.tenant_id)
            .order_by(Product.created_at.desc())
            .limit(3)
        )
        products = prod_res.scalars().all()
        acc_res = await db.execute(
            select(SocialAccount).where(
                SocialAccount.tenant_id == current_user.tenant_id,
                SocialAccount.is_active.is_(True),
            )
        )
        accounts = acc_res.scalars().all()

        if products and accounts:
            for day, prod in enumerate(products, start=1):
                price = f"{prod.price:.0f}€" if prod.price else ""
                img = await search_image(prod.name)
                cuerpo = (
                    f"✨ {prod.name}" + (f" — {price}" if price else "")
                    + "\n\nDescúbrelo y lleva tu negocio al siguiente nivel 🚀\n#pyme #negocio"
                )
                for acc in accounts:
                    db.add(ScheduledPost(
                        tenant_id=current_user.tenant_id,
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
        import asyncio

        from app.services.marketing.image_search import search_image

        acc_res = await db.execute(
            select(SocialAccount).where(
                SocialAccount.tenant_id == current_user.tenant_id,
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
                    tenant_id=current_user.tenant_id,
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

        # (2) Imágenes: rellena las que falten EN PARALELO (Instagram las exige).
        missing = [p for p in created if not p.image_url]
        if missing:
            imgs = await asyncio.gather(
                *(search_image(p.content[:80]) for p in missing),
                return_exceptions=True,
            )
            for p, img in zip(missing, imgs):
                if isinstance(img, str) and img:
                    p.image_url = img

        await db.commit()

    post_ids = [str(p.id) for p in created]
    if fallback_used:
        summary = (
            f"Plan básico generado desde tu catálogo: {len(created)} posts en borrador "
            "con imagen, listos para que los edites y publiques."
        )
    else:
        summary = results[0].get("result", "Plan generado.") if results else "Plan generado."
    return GeneratePlanResponse(summary=summary, post_ids=post_ids)


# ── Publish individual / batch ─────────────────────────────────────────────────


class PublishBatchRequest(BaseModel):
    post_ids: list[UUID]


class PostUpdateRequest(BaseModel):
    content: Optional[str] = None
    image_url: Optional[str] = None
    scheduled_at: Optional[datetime.datetime] = None


@router.post("/posts/{post_id}/publish", response_model=PostOut)
async def publish_post_now(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publica un post borrador o programado inmediatamente."""
    from app.services.marketing.publisher import publish_post

    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == current_user.tenant_id,
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    if post.status == "published":
        raise HTTPException(status_code=409, detail="El post ya está publicado")

    await publish_post(post, db)
    await db.commit()
    await db.refresh(post)
    return post


@router.post("/posts/publish-batch")
async def publish_batch(
    body: PublishBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publica varios posts inmediatamente. Devuelve resumen con ok/failed."""
    from app.services.marketing.publisher import publish_post

    ok_ids, failed_ids = [], []
    for pid in body.post_ids:
        result = await db.execute(
            select(ScheduledPost).where(
                ScheduledPost.id == pid,
                ScheduledPost.tenant_id == current_user.tenant_id,
                ScheduledPost.status != "published",
            )
        )
        post = result.scalar_one_or_none()
        if not post:
            failed_ids.append(str(pid))
            continue
        success = await publish_post(post, db)
        (ok_ids if success.ok else failed_ids).append(str(pid))

    await db.commit()
    return {"published": ok_ids, "failed": failed_ids}


@router.patch("/posts/{post_id}", response_model=PostOut)
async def update_post(
    post_id: UUID,
    body: PostUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita contenido, imagen o horario de un post borrador o programado."""
    result = await db.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.tenant_id == current_user.tenant_id,
            ScheduledPost.status.in_(["draft", "scheduled"]),
        )
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado o ya publicado")

    if body.content is not None:
        post.content = body.content
    if body.image_url is not None:
        post.image_url = body.image_url
    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
        post.status = "scheduled"

    await db.commit()
    await db.refresh(post)
    return post
