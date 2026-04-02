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


# ---------------------------------------------------------------------------
# Claude Code CLI — setup automático
# ---------------------------------------------------------------------------

class ClaudeCodeSetupResponse(BaseModel):
    status: str  # "ready" | "needs_auth" | "installed" | "error"
    version: str | None = None
    message: str = ""


def _run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Ejecuta un comando y devuelve (returncode, stdout, stderr)."""
    import subprocess, shutil, os
    # Resolver binario
    bin_path = shutil.which(args[0])
    if not bin_path:
        # Windows: probar con .cmd
        bin_path = shutil.which(args[0] + ".cmd")
    if bin_path:
        args = [bin_path] + args[1:]
    try:
        r = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
            env={**os.environ, "NO_COLOR": "1"},
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Comando no encontrado: {args[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Timeout ejecutando: {' '.join(args)}"
    except Exception as e:
        return -3, "", str(e)


@router.post("/claude-code-setup", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Verifica/instala Claude Code CLI y comprueba autenticación."""
    import asyncio, shutil

    loop = asyncio.get_event_loop()

    # Step 1: ¿Está claude instalado?
    claude_bin = shutil.which("claude") or shutil.which("claude.cmd")

    if not claude_bin:
        # Step 2: Intentar instalar
        npm_bin = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_bin:
            return ClaudeCodeSetupResponse(
                status="error",
                message="Node.js no está instalado. Descárgalo desde https://nodejs.org/",
            )

        code, out, err = await loop.run_in_executor(
            None, _run_cmd, ["npm", "install", "-g", "@anthropic-ai/claude-code"]
        )
        if code != 0:
            return ClaudeCodeSetupResponse(
                status="error",
                message=f"Error instalando Claude Code: {err or out}",
            )

        # Verificar que se instaló
        claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
        if not claude_bin:
            return ClaudeCodeSetupResponse(
                status="error",
                message="Se instaló pero no se encuentra en el PATH. Reinicia la aplicación.",
            )

    # Step 3: Obtener versión
    code, version, err = await loop.run_in_executor(
        None, _run_cmd, ["claude", "--version"]
    )
    if code != 0:
        version = "desconocida"

    # Step 4: Comprobar autenticación
    code, auth_out, auth_err = await loop.run_in_executor(
        None, _run_cmd, ["claude", "auth", "status"]
    )

    # claude auth status devuelve JSON: {"loggedIn": true, ...}
    is_authenticated = False
    if code == 0 and auth_out:
        try:
            import json as _json
            auth_data = _json.loads(auth_out)
            is_authenticated = auth_data.get("loggedIn", False) is True
        except (ValueError, KeyError):
            # Fallback: buscar texto
            full_output = f"{auth_out} {auth_err}".lower()
            is_authenticated = "logged in" in full_output or "authenticated" in full_output or "active" in full_output

    if is_authenticated:
        return ClaudeCodeSetupResponse(
            status="ready",
            version=version,
            message="Claude Code instalado y autenticado.",
        )

    return ClaudeCodeSetupResponse(
        status="needs_auth",
        version=version,
        message="Abre un terminal y ejecuta: claude",
    )


@router.post("/claude-code-login", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_login(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Lanza claude auth login (abre navegador para OAuth)."""
    import asyncio, shutil, subprocess, os

    loop = asyncio.get_event_loop()

    # Verificar que claude está instalado
    claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
    if not claude_bin:
        # Intentar instalar primero
        npm_bin = shutil.which("npm") or shutil.which("npm.cmd")
        if not npm_bin:
            return ClaudeCodeSetupResponse(
                status="error",
                message="Node.js no está instalado. Descárgalo desde https://nodejs.org/",
            )
        code, out, err = await loop.run_in_executor(
            None, _run_cmd, ["npm", "install", "-g", "@anthropic-ai/claude-code"]
        )
        if code != 0:
            return ClaudeCodeSetupResponse(
                status="error",
                message=f"Error instalando Claude Code: {err or out}",
            )
        claude_bin = shutil.which("claude") or shutil.which("claude.cmd")
        if not claude_bin:
            return ClaudeCodeSetupResponse(
                status="error",
                message="Se instaló pero no se encuentra en el PATH. Reinicia la aplicación.",
            )

    # Lanzar login en background (abre navegador, no bloqueamos)
    try:
        subprocess.Popen(
            [claude_bin, "auth", "login"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as e:
        return ClaudeCodeSetupResponse(
            status="error",
            message=f"Error lanzando login: {e}",
        )

    return ClaudeCodeSetupResponse(
        status="needs_auth",
        message="Se ha abierto el navegador para iniciar sesión. Completa el login y pulsa 'Verificar conexión'.",
    )


@router.post("/claude-code-logout", response_model=ClaudeCodeSetupResponse)
@limiter.limit("5/minute")
async def claude_code_logout(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Cierra la sesión de Claude Code CLI."""
    import asyncio

    loop = asyncio.get_event_loop()
    code, out, err = await loop.run_in_executor(
        None, _run_cmd, ["claude", "auth", "logout"]
    )

    if code == 0:
        return ClaudeCodeSetupResponse(
            status="needs_auth",
            message="Sesión de Claude Code cerrada correctamente.",
        )

    return ClaudeCodeSetupResponse(
        status="error",
        message=f"Error al cerrar sesión: {err or out}",
    )

