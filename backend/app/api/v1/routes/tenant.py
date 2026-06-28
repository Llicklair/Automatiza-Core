from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.schemas.tenant import (
    ClaudeCodeSetupResponse,
    LlmConfigResponse,
    LlmConfigUpdate,
    TenantMeResponse,
    TenantMeUpdate,
)
from app.core.dependencies import get_current_user, require_role
from app.db.base import get_db
from app.db.models.auth import Tenant
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
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/me", response_model=TenantMeResponse)
@limiter.limit("20/minute")
async def update_tenant_me(
    request: Request,
    payload: TenantMeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
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
        raise HTTPException(status_code=status, detail=detail) from e


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
    current_user: User = Depends(require_role("admin")),
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
        raise HTTPException(status_code=422, detail=str(e)) from e
    return LlmConfigResponse(**data)


@router.post("/claude-code-setup", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_setup(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Verifica/instala Claude Code CLI y comprueba autenticación."""
    data = await svc.claude_code_setup()
    return ClaudeCodeSetupResponse(**data)


@router.post("/claude-code-login", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_login(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Lanza claude auth login (abre navegador para OAuth)."""
    data = await svc.claude_code_login()
    return ClaudeCodeSetupResponse(**data)


@router.post("/claude-code-logout", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_logout(
    request: Request,
    current_user: User = Depends(require_role("admin")),
):
    """Cierra la sesión de Claude Code CLI."""
    data = await svc.claude_code_logout()
    return ClaudeCodeSetupResponse(**data)


# ── Firma digital (certificado PKCS#12) ──────────────────────────────────────


@router.get("/certificate", tags=["tenant"])
@limiter.limit("20/minute")
async def get_certificate_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant or not tenant.cert_path:
        return {"has_certificate": False}
    return {
        "has_certificate": True,
        "cert_subject": tenant.cert_subject,
        "cert_expires_at": tenant.cert_expires_at.isoformat() if tenant.cert_expires_at else None,
    }


@router.post("/certificate", tags=["tenant"])
@limiter.limit("10/minute")
async def upload_certificate(
    request: Request,
    file: UploadFile = File(...),
    password: str = Form(default=""),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if not file.filename or not file.filename.lower().endswith((".p12", ".pfx")):
        raise HTTPException(status_code=400, detail="El archivo debe ser .p12 o .pfx")

    content = await file.read()

    from app.services.tenant.certificates import CertificateError, install_certificate

    try:
        info = await install_certificate(
            file_bytes=content,
            password=password,
            tenant_id=current_user.tenant_id,
            db=db,
        )
    except CertificateError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "message": "Certificado cargado correctamente",
        "cert_subject": info.subject,
        "cert_expires_at": info.expires_at.isoformat(),
    }


@router.delete("/certificate", status_code=204, tags=["tenant"])
@limiter.limit("10/minute")
async def delete_certificate(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    if tenant and tenant.cert_path:
        p = Path(tenant.cert_path)
        if p.exists():
            p.unlink()
        tenant.cert_path = None
        tenant.cert_password = None
        tenant.cert_subject = None
        tenant.cert_expires_at = None
        await db.commit()


# ── Logo corporativo ─────────────────────────────────────────────────────────

_LOGO_DIR = Path("uploads/logos")
_LOGO_ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
_LOGO_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


@router.get("/logo", tags=["tenant"])
@limiter.limit("20/minute")
async def get_logo_status(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    if not tenant or not tenant.logo_path or not Path(tenant.logo_path).exists():
        return {"has_logo": False}
    return {"has_logo": True, "logo_path": tenant.logo_path}


@router.post("/logo", tags=["tenant"])
@limiter.limit("10/minute")
async def upload_logo(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Falta el nombre del archivo")
    ext = Path(file.filename).suffix.lower()
    if ext not in _LOGO_ALLOWED_EXT:
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado. Usa: {', '.join(sorted(_LOGO_ALLOWED_EXT))}",
        )

    content = await file.read()
    if len(content) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=413, detail="El logo no puede superar 2 MB")
    if not content:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    logo_dir = _LOGO_DIR / str(current_user.tenant_id)
    logo_dir.mkdir(parents=True, exist_ok=True)
    # Borrar logo previo si existía con otra extensión
    for prev in logo_dir.glob("logo.*"):
        try:
            prev.unlink()
        except OSError:
            pass
    logo_path = logo_dir / f"logo{ext}"
    logo_path.write_bytes(content)

    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    tenant.logo_path = str(logo_path)
    await db.commit()

    return {"message": "Logo cargado correctamente", "logo_path": str(logo_path)}


@router.delete("/logo", status_code=204, tags=["tenant"])
@limiter.limit("10/minute")
async def delete_logo(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    res = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = res.scalar_one_or_none()
    if tenant and tenant.logo_path:
        p = Path(tenant.logo_path)
        if p.exists():
            p.unlink(missing_ok=True)
        tenant.logo_path = None
        await db.commit()
