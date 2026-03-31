from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from app.middleware.rate_limit import limiter
from typing import Any
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import Tenant, User, TenantLlmConfig
from app.services.encryption import encrypt_credentials, decrypt_credentials


class TenantMeResponse(BaseModel):
    id: UUID
    name: str
    nif: str
    address: str | None = None
    phone: str | None = None
    contact_email: str | None = None

    class Config:
        from_attributes = True


class TenantMeUpdate(BaseModel):
    name: str | None = None
    nif: str | None = None
    address: str | None = None
    phone: str | None = None
    contact_email: str | None = None


router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/me", response_model=TenantMeResponse)
@limiter.limit("20/minute")
async def get_tenant_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")
    return tenant


@router.patch("/me", response_model=TenantMeResponse)
@limiter.limit("20/minute")
async def update_tenant_me(
    request: Request,
    payload: TenantMeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant no encontrado")

    if payload.name is not None:
        tenant.name = payload.name
    if payload.nif is not None:
        tenant.nif = payload.nif
    if payload.address is not None:
        tenant.address = payload.address
    if payload.phone is not None:
        tenant.phone = payload.phone
    if payload.contact_email is not None:
        tenant.contact_email = payload.contact_email

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Ya existe otra empresa con ese NIF. Usa un NIF distinto.",
        )

    await db.refresh(tenant)
    return tenant


# ── LLM Config ────────────────────────────────────────────────────────────────

ALLOWED_LLM_PROVIDERS = {"gemini", "anthropic", "groq", "openai", "openrouter", "claude_code"}
ALLOWED_EMBEDDINGS_PROVIDERS = {"local", "gemini", "openai"}

_MASKED = "••••••••"


class LlmProviderConfig(BaseModel):
    api_key: str | None = None       # vacío = no cambiar; _MASKED = ya guardada
    model: str | None = None
    enabled: bool = False


class LlmConfigUpdate(BaseModel):
    active_llm_provider: str | None = None
    active_embeddings_provider: str | None = None
    providers: dict[str, LlmProviderConfig] | None = None


class LlmConfigResponse(BaseModel):
    active_llm_provider: str
    active_embeddings_provider: str
    providers: dict[str, Any]  # {provider: {model, enabled, has_key}}


@router.get("/llm-config", response_model=LlmConfigResponse)
@limiter.limit("20/minute")
async def get_llm_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == current_user.tenant_id)
    )
    cfg = result.scalar_one_or_none()

    keys: dict = {}
    if cfg and cfg.encrypted_keys:
        try:
            keys = decrypt_credentials(cfg.encrypted_keys)
        except Exception:
            keys = {}

    # Construir respuesta enmascarando las claves
    providers_out = {}
    for p in ALLOWED_LLM_PROVIDERS:
        pdata = keys.get(p, {})
        providers_out[p] = {
            "model": pdata.get("model", ""),
            "enabled": pdata.get("enabled", False),
            "has_key": bool(pdata.get("api_key")),
        }

    return LlmConfigResponse(
        active_llm_provider=cfg.active_llm_provider if cfg else "gemini",
        active_embeddings_provider=cfg.active_embeddings_provider if cfg else "local",
        providers=providers_out,
    )


@router.put("/llm-config", response_model=LlmConfigResponse)
@limiter.limit("20/minute")
async def update_llm_config(
    request: Request,
    payload: LlmConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.active_llm_provider and payload.active_llm_provider not in ALLOWED_LLM_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Provider LLM no válido: {payload.active_llm_provider}")
    if payload.active_embeddings_provider and payload.active_embeddings_provider not in ALLOWED_EMBEDDINGS_PROVIDERS:
        raise HTTPException(status_code=422, detail=f"Provider embeddings no válido: {payload.active_embeddings_provider}")

    result = await db.execute(
        select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == current_user.tenant_id)
    )
    cfg = result.scalar_one_or_none()

    # Cargar claves existentes
    existing_keys: dict = {}
    if cfg and cfg.encrypted_keys:
        try:
            existing_keys = decrypt_credentials(cfg.encrypted_keys)
        except Exception:
            existing_keys = {}

    # Mezclar con cambios enviados
    if payload.providers:
        for provider, pdata in payload.providers.items():
            if provider not in ALLOWED_LLM_PROVIDERS:
                continue
            entry = existing_keys.get(provider, {})
            # Solo sobreescribir la api_key si viene una nueva (no _MASKED y no vacía)
            if pdata.api_key and pdata.api_key != _MASKED:
                entry["api_key"] = pdata.api_key
            if pdata.model is not None:
                entry["model"] = pdata.model
            entry["enabled"] = pdata.enabled
            existing_keys[provider] = entry

    if not cfg:
        cfg = TenantLlmConfig(tenant_id=current_user.tenant_id)
        db.add(cfg)

    if payload.active_llm_provider:
        cfg.active_llm_provider = payload.active_llm_provider
    if payload.active_embeddings_provider:
        cfg.active_embeddings_provider = payload.active_embeddings_provider
    if existing_keys:
        cfg.encrypted_keys = encrypt_credentials(existing_keys)

    await db.commit()
    await db.refresh(cfg)

    # Construir respuesta
    providers_out = {}
    for p in ALLOWED_LLM_PROVIDERS:
        pdata = existing_keys.get(p, {})
        providers_out[p] = {
            "model": pdata.get("model", ""),
            "enabled": pdata.get("enabled", False),
            "has_key": bool(pdata.get("api_key")),
        }

    return LlmConfigResponse(
        active_llm_provider=cfg.active_llm_provider,
        active_embeddings_provider=cfg.active_embeddings_provider,
        providers=providers_out,
    )

