"""Marketing: social accounts, campaigns, scheduled posts, OAuth callbacks."""

import asyncio
import base64
import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.marketing import Campaign, ScheduledPost, SocialAccount
from app.db.models.models import User
from app.services.encryption import decrypt_str, encrypt_str
from app.services.marketing.image_generation import generate_image as _generate_image
from app.services.marketing.provider_config import (
    add_provider_config,
    client_for_account,
    client_for_config,
    delete_provider_config,
    get_config,
    list_provider_configs,
    set_default_profile_id,
)
from app.services.marketing.zernio_client import ZernioClient, ZernioError

router = APIRouter(prefix="/marketing", tags=["marketing"])


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


def _zernio_state(tenant_id, config_id) -> str:
    """State tamper-proof y URL-safe (cifrado) para el path del redirect de Zernio.
    Lleva el tenant y la cuenta de Zernio (config) por la que se conecta."""
    token = encrypt_str(f"{tenant_id}|{config_id}")
    return base64.urlsafe_b64encode(token.encode()).decode().rstrip("=")


def _zernio_unstate(state: str) -> tuple[UUID, UUID]:
    pad = "=" * (-len(state) % 4)
    raw = decrypt_str(base64.urlsafe_b64decode(state + pad).decode())
    tenant_str, config_str = raw.split("|", 1)
    return UUID(tenant_str), UUID(config_str)


# ── Schemas ────────────────────────────────────────────────────────────────────


class SocialAccountOut(BaseModel):
    id: UUID
    platform: str
    account_id: str
    account_name: Optional[str] = None
    is_active: bool
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


class GenerateImageRequest(BaseModel):
    prompt: str


@router.post("/generate-image")
async def generate_image_endpoint(
    body: GenerateImageRequest,
    current_user: User = Depends(get_current_user),
):
    """Genera una imagen con IA a partir de un prompt y devuelve su URL (temporal).

    La URL la aloja OpenAI ~2h: pensada para previsualizar y publicar al momento.
    """
    prompt = (body.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="El prompt no puede estar vacío")
    url = await _generate_image(prompt)
    if not url:
        raise HTTPException(
            status_code=503,
            detail="No se pudo generar la imagen. Revisa que OPENAI_API_KEY esté configurada.",
        )
    return {"url": url}


_ZERNIO_PLATFORMS = {
    "instagram", "facebook", "linkedin", "twitter", "tiktok", "youtube",
    "threads", "pinterest", "bluesky", "reddit", "snapchat", "googlebusiness",
}


async def _pick_config(db: AsyncSession, tenant_id, config_id):
    """Cuenta de Zernio a usar: la indicada, o la primera del tenant."""
    if config_id is not None:
        cfg = await get_config(db, config_id, tenant_id)
        if cfg is None:
            raise HTTPException(status_code=404, detail="Cuenta de Zernio no encontrada")
        return cfg
    configs = await list_provider_configs(db, tenant_id)
    if not configs:
        raise HTTPException(
            status_code=400,
            detail="Añade primero tu API key de Zernio en Configuración → Marketing.",
        )
    return configs[0]


async def _resolve_profile_id(db: AsyncSession, cfg, client) -> str:
    """Devuelve el profileId de Zernio de esta cuenta (lo cachea como default)."""
    if cfg.default_profile_id:
        return cfg.default_profile_id
    profiles = await client.list_profiles()
    if not profiles:
        raise HTTPException(
            status_code=502,
            detail="Tu cuenta de Zernio no tiene ningún profile. Crea uno en zernio.com y reinténtalo.",
        )
    pid = str(profiles[0].get("_id") or profiles[0].get("id") or "")
    await set_default_profile_id(db, cfg, pid)
    await db.commit()
    return pid


@router.post("/accounts/connect/{platform}", status_code=status.HTTP_200_OK)
async def connect_account(
    platform: str,
    provider_config_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if platform not in _ZERNIO_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {platform}")
    cfg = await _pick_config(db, current_user.tenant_id, provider_config_id)
    try:
        client = client_for_config(cfg)
    except ZernioError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile_id = await _resolve_profile_id(db, cfg, client)
    base = settings.OAUTH_REDIRECT_URI.split("/api/v1")[0]
    state = _zernio_state(current_user.tenant_id, cfg.id)
    redirect_url = f"{base}/api/v1/marketing/zernio/callback/{state}"
    try:
        auth_url = await client.connect_url(platform, profile_id, redirect_url)
    except ZernioError as e:
        raise HTTPException(status_code=502, detail=f"Zernio: {e}")
    if not auth_url:
        raise HTTPException(status_code=502, detail="Zernio no devolvió URL de conexión.")
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
    # Libera el hueco en Zernio (plan gratis: 2 redes/email) para poder conectar otra.
    try:
        client = await client_for_account(db, account)
    except ZernioError:
        client = None
    if client is not None:
        try:
            await client.disconnect_account(account.account_id)
        except ZernioError as e:
            if e.status != 404:  # 404 = ya no existe en Zernio; continuamos
                raise HTTPException(status_code=502, detail=f"No se pudo desconectar en Zernio: {e}")
    account.is_active = False
    await db.commit()


@router.get("/zernio/callback/{state}")
async def zernio_callback(
    state: str,
    connected: Optional[str] = Query(None),
    accountId: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    profileId: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Callback de la conexión vía Zernio: upsert de la cuenta con su accountId.

    Zernio redirige aquí (state en el path para robustez) añadiendo en la query
    `connected`, `accountId`, `username`. No hay tokens de cuenta: en BYO la
    publicación usa la API key del tenant, no credenciales OAuth de la cuenta.
    """
    try:
        tenant_id, config_id = _zernio_unstate(state)
    except Exception:
        return _popup_html(False, message="Estado de conexión inválido o expirado")
    if not accountId:
        return _popup_html(False, message="Zernio no devolvió la cuenta conectada. Reinténtalo.")

    platform = connected or "social"
    existing = await db.execute(
        select(SocialAccount).where(
            SocialAccount.tenant_id == tenant_id,
            SocialAccount.account_id == accountId,
        )
    )
    account = existing.scalar_one_or_none()
    if account:
        account.platform = platform
        account.account_name = username or account.account_name
        account.provider_config_id = config_id
        account.is_active = True
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            platform=platform,
            account_id=accountId,
            account_name=username,
            provider_config_id=config_id,
            is_active=True,
        )
        db.add(account)
    await db.commit()
    return _popup_html(True, platform=platform)


# ── Configuración Zernio (BYO API keys) ─────────────────────────────────────────


class ZernioConfigCreate(BaseModel):
    api_key: str
    label: Optional[str] = None


class ZernioConfigOut(BaseModel):
    id: UUID
    label: Optional[str] = None
    default_profile_id: Optional[str] = None
    num_accounts: int = 0


@router.get("/zernio-config", response_model=list[ZernioConfigOut])
async def list_zernio_configs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista las cuentas de Zernio del tenant (sin exponer la API key)."""
    configs = await list_provider_configs(db, current_user.tenant_id)
    out: list[ZernioConfigOut] = []
    for c in configs:
        n = await db.scalar(
            select(func.count())
            .select_from(SocialAccount)
            .where(
                SocialAccount.provider_config_id == c.id,
                SocialAccount.is_active.is_(True),
            )
        )
        out.append(ZernioConfigOut(
            id=c.id, label=c.label, default_profile_id=c.default_profile_id, num_accounts=n or 0,
        ))
    return out


@router.post("/zernio-config", response_model=ZernioConfigOut, status_code=status.HTTP_201_CREATED)
async def add_zernio_config(
    body: ZernioConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Añade una cuenta de Zernio (un email/API key) validándola contra la API.

    El free tier de Zernio da 2 cuentas sociales por email, así que se pueden añadir
    varias cuentas para conectar más redes gratis.
    """
    key = (body.api_key or "").strip()
    if not key.startswith("sk_"):
        raise HTTPException(status_code=400, detail="La API key de Zernio debe empezar por 'sk_'.")
    client = ZernioClient(key)
    try:
        profiles = await client.list_profiles()
    except ZernioError as e:
        raise HTTPException(status_code=400, detail=f"La API key no es válida: {e}")
    default_pid = str(profiles[0].get("_id") or profiles[0].get("id")) if profiles else None
    cfg = await add_provider_config(
        db, current_user.tenant_id, key, label=body.label, default_profile_id=default_pid,
    )
    await db.commit()
    return ZernioConfigOut(
        id=cfg.id, label=cfg.label, default_profile_id=cfg.default_profile_id, num_accounts=0,
    )


@router.delete("/zernio-config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zernio_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ok = await delete_provider_config(db, config_id, current_user.tenant_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Cuenta de Zernio no encontrada")
    await db.commit()


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
            tenant_id=current_user.tenant_id,
            domain="marketing",
            action_summary="Generar plan de marketing (borradores) desde el catálogo",
        )
        if decision.mode == "MANUAL":
            fallback_blocked_manual = True
        else:
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
                # Imágenes en paralelo con timeout global (no en serie): el proxy
                # de Render puede estar frío y N búsquedas secuenciales colgaban
                # la request HTTP. Sin imagen → None (editable después).
                imgs = await _search_images_bounded([p.name for p in products])
                for day, (prod, img) in enumerate(zip(products, imgs), start=1):
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

        # (2) Imágenes: rellena las que falten en paralelo con timeout global
        # (Instagram las exige). Si el proxy está frío, no cuelga la request.
        missing = [p for p in created if not p.image_url]
        if missing:
            imgs = await _search_images_bounded([p.content[:80] for p in missing])
            for p, img in zip(missing, imgs):
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
    from app.services.marketing.publishing import get_publisher

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

    publish_result = await get_publisher().publish_post(post, db)
    await db.commit()
    await db.refresh(post)
    if not publish_result.ok:
        # No dar por publicado un post que falló: propagar el error al cliente
        # (antes se devolvía 200 con status='failed' y el front lo daba por OK).
        raise HTTPException(
            status_code=502,
            detail=post.error_message or "No se pudo publicar el post.",
        )
    return post


@router.post("/posts/publish-batch")
async def publish_batch(
    body: PublishBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Publica varios posts inmediatamente. Devuelve resumen con ok/failed."""
    from app.services.marketing.publishing import get_publisher

    publisher = get_publisher()
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
        success = await publisher.publish_post(post, db)
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
        # En el modal de edición el campo refleja el estado final: cadena vacía
        # = "quitar imagen" → NULL (no '' falsy, que rompe los checks `if image_url`
        # de la publicación, p.ej. Instagram).
        post.image_url = body.image_url.strip() or None
    if body.scheduled_at is not None:
        post.scheduled_at = body.scheduled_at
        post.status = "scheduled"

    await db.commit()
    await db.refresh(post)
    return post
