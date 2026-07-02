"""Marketing: social accounts, campaigns, scheduled posts, OAuth callbacks."""

import base64
import datetime
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import frontend_origin, settings
from app.core.dependencies import get_current_user
from app.core.tenant_context import set_current_tenant
from app.db.base import get_db
from app.db.models.models import User
from app.services.encryption import decrypt_str, encrypt_str
from app.services.marketing.image_generation import generate_image as _generate_image
from app.services.marketing.provider_config import (
    add_zernio_config,
    client_for_config,
    get_config,
    list_configs_with_counts,
    list_provider_configs,
    set_default_profile_id,
)
from app.services.marketing.zernio_client import ZernioError

_logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketing", tags=["marketing"])


def _popup_html(success: bool, platform: str = "", message: str = "") -> HTMLResponse:
    if success:
        body = f"""
            <div class="icon">✓</div>
            <h2>{platform.capitalize()} conectado</h2>
            <p>Puedes cerrar esta ventana.</p>
        """
        # M2: targetOrigin explícito (no '*') para que solo el frontend reciba el mensaje.
        script = (
            "if (window.opener) {"
            "  window.opener.postMessage({ type: 'oauth-complete' }, " + json.dumps(frontend_origin()) + ");"
            "}"
            "setTimeout(() => window.close(), 1800);"
        )
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
    from app.services.marketing.social_accounts import list_accounts as _list_accounts

    return await _list_accounts(current_user.tenant_id, db)


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
    "instagram",
    "facebook",
    "linkedin",
    "twitter",
    "tiktok",
    "youtube",
    "threads",
    "pinterest",
    "bluesky",
    "reddit",
    "snapchat",
    "googlebusiness",
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
        raise HTTPException(status_code=400, detail=str(e)) from e

    profile_id = await _resolve_profile_id(db, cfg, client)
    base = settings.OAUTH_REDIRECT_URI.split("/api/v1")[0]
    state = _zernio_state(current_user.tenant_id, cfg.id)
    redirect_url = f"{base}/api/v1/marketing/zernio/callback/{state}"
    try:
        auth_url = await client.connect_url(platform, profile_id, redirect_url)
    except ZernioError as exc:
        _logger.exception("Error con el proveedor Zernio")
        raise HTTPException(status_code=502, detail="Error al comunicar con el proveedor Zernio") from exc
    if not auth_url:
        raise HTTPException(status_code=502, detail="Zernio no devolvió URL de conexión.")
    return {"auth_url": auth_url}


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing import social_accounts

    try:
        ok = await social_accounts.disconnect_account(account_id, current_user.tenant_id, db)
    except ZernioError as exc:
        _logger.exception("Error con el proveedor Zernio")
        raise HTTPException(status_code=502, detail="Error al comunicar con el proveedor Zernio") from exc
    if not ok:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")


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
    from app.services.marketing.social_accounts import upsert_from_callback

    try:
        tenant_id, config_id = _zernio_unstate(state)
    except Exception:
        return _popup_html(False, message="Estado de conexión inválido o expirado")
    # SEC.RLS: callback público sin JWT, pero el tenant viene firmado en el
    # `state` → lo fijamos para que el SELECT/upsert de SocialAccount quede
    # correctamente scoped (opción tighter que bypass; corrige bug latente).
    set_current_tenant(str(tenant_id))
    if not accountId:
        return _popup_html(False, message="Zernio no devolvió la cuenta conectada. Reinténtalo.")

    platform = connected if connected in _ZERNIO_PLATFORMS else "social"
    await upsert_from_callback(tenant_id, config_id, accountId, username, platform, db)
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
    items = await list_configs_with_counts(db, current_user.tenant_id)
    return [
        ZernioConfigOut(
            id=c.id,
            label=c.label,
            default_profile_id=c.default_profile_id,
            num_accounts=c.num_accounts,
        )
        for c in items
    ]


@router.post("/zernio-config", response_model=ZernioConfigOut, status_code=status.HTTP_201_CREATED)
async def add_zernio_config_endpoint(
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
    try:
        cfg = await add_zernio_config(db, current_user.tenant_id, key, label=body.label)
    except ZernioError as e:
        raise HTTPException(status_code=400, detail=f"La API key no es válida: {e}") from e
    return ZernioConfigOut(
        id=cfg.id,
        label=cfg.label,
        default_profile_id=cfg.default_profile_id,
        num_accounts=cfg.num_accounts,
    )


@router.delete("/zernio-config/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_zernio_config(
    config_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing.provider_config import delete_provider_config

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
    from app.services.marketing.campaigns import list_campaigns as _list_campaigns

    return await _list_campaigns(current_user.tenant_id, db)


@router.post("/campaigns", response_model=CampaignOut, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing.campaigns import create_campaign as _create_campaign

    return await _create_campaign(current_user.tenant_id, body.name, body.description, db)


@router.get("/campaigns/{campaign_id}/metrics")
async def campaign_metrics(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Métricas agregadas de una campaña (impresiones, alcance y engagement por post).

    Devuelve la última métrica conocida de cada post (el job diario las refresca).
    """
    from app.services.marketing.campaigns import get_campaign
    from app.services.marketing.metrics import get_campaign_metrics

    if await get_campaign(campaign_id, current_user.tenant_id, db) is None:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    return await get_campaign_metrics(db, current_user.tenant_id, campaign_id)


# ── Posts ──────────────────────────────────────────────────────────────────────


@router.get("/posts", response_model=list[PostOut])
async def list_posts(
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing.posts import list_posts as _list_posts

    return await _list_posts(current_user.tenant_id, db, status_filter=status_filter)


@router.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: PostCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing.posts import create_post as _create_post

    try:
        return await _create_post(
            current_user.tenant_id,
            body.social_account_id,
            body.platform,
            body.content,
            body.image_url,
            body.campaign_id,
            body.scheduled_at,
            db,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.services.marketing.posts import delete_post as _delete_post

    ok = await _delete_post(post_id, current_user.tenant_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Post no encontrado o ya publicado")


class BulkDeletePostsRequest(BaseModel):
    ids: Optional[list[UUID]] = None
    status: Optional[str] = None


@router.post("/posts/bulk-delete")
async def bulk_delete_posts(
    body: BulkDeletePostsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Elimina en masa los posts NO publicados: toda la lista o un subconjunto.

    `ids` acota a posts concretos; `status` a un estado (ej. "scheduled"). Sin
    ninguno de los dos, borra todos los posts no publicados del tenant.
    """
    from app.services.marketing.posts import delete_posts_bulk

    deleted = await delete_posts_bulk(current_user.tenant_id, db, ids=body.ids, status_filter=body.status)
    return {"deleted": deleted}


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
    from app.services.marketing.plan_generation import generate_plan as _generate_plan

    summary, post_ids = await _generate_plan(db, current_user.tenant_id, body.prompt)
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
    from app.services.marketing.publishing import PostAlreadyPublishedError, publish_single_post

    try:
        res = await publish_single_post(post_id, current_user.tenant_id, db)
    except PostAlreadyPublishedError as exc:
        raise HTTPException(status_code=409, detail="El post ya está publicado") from exc
    if res is None:
        raise HTTPException(status_code=404, detail="Post no encontrado")
    post, ok = res
    if not ok:
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
    from app.services.marketing.publishing import publish_posts_batch

    return await publish_posts_batch(body.post_ids, current_user.tenant_id, db)


@router.patch("/posts/{post_id}", response_model=PostOut)
async def update_post(
    post_id: UUID,
    body: PostUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edita contenido, imagen o horario de un post borrador o programado."""
    from app.services.marketing.posts import update_post as _update_post

    post = await _update_post(
        post_id,
        current_user.tenant_id,
        body.content,
        body.image_url,
        body.scheduled_at,
        db,
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post no encontrado o ya publicado")
    return post
