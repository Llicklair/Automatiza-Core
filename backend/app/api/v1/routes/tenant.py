from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.tenant import (
    ClaudeCodeSetupResponse,
    LlmConfigResponse,
    LlmConfigUpdate,
    TenantMeResponse,
    TenantMeUpdate,
)
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.models import User
from app.middleware.rate_limit import limiter
from app.services import tenant_service as svc

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("/me", response_model=TenantMeResponse)
@limiter.limit("20/minute")
async def get_tenant_me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.get_tenant(db, current_user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/me", response_model=TenantMeResponse)
@limiter.limit("20/minute")
async def update_tenant_me(
    request: Request,
    payload: TenantMeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await svc.update_tenant(
            db,
            current_user.tenant_id,
            name=payload.name,
            nif=payload.nif,
            address=payload.address,
            phone=payload.phone,
            contact_email=payload.contact_email,
        )
    except ValueError as e:
        detail = str(e)
        status = 400 if "NIF" in detail else 404
        raise HTTPException(status_code=status, detail=detail)


@router.get("/llm-config", response_model=LlmConfigResponse)
@limiter.limit("20/minute")
async def get_llm_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await svc.get_llm_config(db, current_user.tenant_id)
    return LlmConfigResponse(**data)


@router.put("/llm-config", response_model=LlmConfigResponse)
@limiter.limit("20/minute")
async def update_llm_config(
    request: Request,
    payload: LlmConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await svc.update_llm_config(
            db,
            current_user.tenant_id,
            active_llm_provider=payload.active_llm_provider,
            active_embeddings_provider=payload.active_embeddings_provider,
            providers=payload.providers,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return LlmConfigResponse(**data)


@router.post("/claude-code-setup", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Verifica/instala Claude Code CLI y comprueba autenticación."""
    data = await svc.claude_code_setup()
    return ClaudeCodeSetupResponse(**data)


@router.post("/claude-code-login", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_login(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Lanza claude auth login (abre navegador para OAuth)."""
    data = await svc.claude_code_login()
    return ClaudeCodeSetupResponse(**data)


@router.post("/claude-code-logout", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Cierra la sesión de Claude Code CLI."""
    data = await svc.claude_code_logout()
    return ClaudeCodeSetupResponse(**data)
