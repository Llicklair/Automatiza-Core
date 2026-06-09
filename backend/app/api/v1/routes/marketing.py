"""Marketing: social accounts, campaigns, scheduled posts, OAuth callbacks."""

import base64
import datetime
import os
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.marketing import Campaign, ScheduledPost, SocialAccount
from app.db.models.models import User

router = APIRouter(prefix="/marketing", tags=["marketing"])

# ── Helpers OAuth ──────────────────────────────────────────────────────────────

def _encode_state(platform: str, tenant_id: str) -> str:
    raw = f"{platform}|{tenant_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def _decode_state(state: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        platform, tenant_id = raw.split("|", 1)
        return platform, tenant_id
    except Exception:
        raise HTTPException(status_code=400, detail="Estado OAuth inválido")


def _redirect_uri() -> str:
    return os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/api/v1/marketing/oauth/callback")


def _oauth_url(platform: str, state: str) -> str:
    client_id = os.getenv(f"{platform.upper()}_CLIENT_ID")
    if not client_id:
        raise HTTPException(
            status_code=503,
            detail=f"OAuth para {platform} no configurado. Añade {platform.upper()}_CLIENT_ID al .env",
        )
    redirect = _redirect_uri()
    urls = {
        "instagram": (
            f"https://api.instagram.com/oauth/authorize"
            f"?client_id={client_id}&redirect_uri={redirect}"
            f"&scope=user_profile,user_media&response_type=code&state={state}"
        ),
        "facebook": (
            f"https://www.facebook.com/v18.0/dialog/oauth"
            f"?client_id={client_id}&redirect_uri={redirect}"
            f"&scope=pages_manage_posts,pages_read_engagement&state={state}"
        ),
        "linkedin": (
            f"https://www.linkedin.com/oauth/v2/authorization"
            f"?response_type=code&client_id={client_id}&redirect_uri={redirect}"
            f"&scope=openid+profile+w_member_social&state={state}"
        ),
        "twitter": (
            f"https://twitter.com/i/oauth2/authorize"
            f"?response_type=code&client_id={client_id}&redirect_uri={redirect}"
            f"&scope=tweet.write+users.read+offline.access"
            f"&state={state}&code_challenge=challenge&code_challenge_method=plain"
        ),
    }
    return urls[platform]


async def _exchange_token(platform: str, code: str) -> dict:
    """Intercambia el authorization code por un access token."""
    client_id = os.getenv(f"{platform.upper()}_CLIENT_ID", "")
    client_secret = os.getenv(f"{platform.upper()}_CLIENT_SECRET", "")
    redirect = _redirect_uri()

    async with httpx.AsyncClient(timeout=15) as client:
        if platform in ("instagram", "facebook"):
            r = await client.post(
                "https://graph.facebook.com/v18.0/oauth/access_token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect,
                    "code": code,
                },
            )
        elif platform == "linkedin":
            r = await client.post(
                "https://www.linkedin.com/oauth/v2/accessToken",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        elif platform == "twitter":
            r = await client.post(
                "https://api.twitter.com/2/oauth2/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect,
                    "code_verifier": "challenge",
                },
                auth=(client_id, client_secret),
            )
        else:
            raise HTTPException(status_code=400, detail=f"Plataforma no soportada: {platform}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Error al obtener token de {platform}: {r.text}")
    return r.json()


async def _fetch_profile(platform: str, access_token: str) -> tuple[str, str]:
    """Devuelve (account_id, account_name) desde la API de la plataforma."""
    async with httpx.AsyncClient(timeout=15) as client:
        if platform == "instagram":
            r = await client.get(
                "https://graph.instagram.com/me",
                params={"fields": "id,username", "access_token": access_token},
            )
            data = r.json()
            return data.get("id", ""), data.get("username", "")

        elif platform == "facebook":
            r = await client.get(
                "https://graph.facebook.com/me",
                params={"fields": "id,name", "access_token": access_token},
            )
            data = r.json()
            return data.get("id", ""), data.get("name", "")

        elif platform == "linkedin":
            r = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            data = r.json()
            return data.get("sub", ""), data.get("name", "")

        elif platform == "twitter":
            r = await client.get(
                "https://api.twitter.com/2/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            data = r.json().get("data", {})
            return data.get("id", ""), data.get("name", "")

    return "", ""


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
        script = "setTimeout(() => window.close(), 4000);"

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
        return _popup_html(False, message="Parámetros de callback incompletos")

    try:
        platform, tenant_id_str = _decode_state(state)
        tenant_id = UUID(tenant_id_str)
    except Exception:
        return _popup_html(False, message="Estado OAuth inválido o expirado")

    try:
        token_data = await _exchange_token(platform, code)
    except HTTPException as e:
        return _popup_html(False, message=e.detail)
    except Exception as e:
        return _popup_html(False, message=f"Error al obtener token: {e}")

    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")
    token_expires_at = None
    if expires_in:
        token_expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(seconds=int(expires_in))

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

    if account:
        account.access_token = access_token
        account.refresh_token = refresh_token
        account.token_expires_at = token_expires_at
        account.account_name = account_name
        account.is_active = True
    else:
        account = SocialAccount(
            tenant_id=tenant_id,
            platform=platform,
            account_id=account_id_str or "unknown",
            account_name=account_name,
            access_token=access_token,
            refresh_token=refresh_token,
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
