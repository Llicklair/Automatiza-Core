"""Business logic for tenant management."""

from __future__ import annotations

import asyncio
import json as _json
import os
import shutil
import subprocess
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.models import Tenant, TenantLlmConfig
from app.services._tenant_schemas import LlmProviderConfig
from app.services.encryption import decrypt_credentials, encrypt_credentials

ALLOWED_LLM_PROVIDERS = {"anthropic", "groq", "openai", "openrouter", "claude_code"}
ALLOWED_EMBEDDINGS_PROVIDERS = {"local", "openai"}

_MASKED = "••••••••"


# ── Tenant CRUD ──────────────────────────────────────────────────────────────


async def get_tenant(db: AsyncSession, tenant_id: UUID) -> Tenant:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise ValueError("Tenant no encontrado")
    return tenant


async def update_tenant(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    name: str | None = None,
    nif: str | None = None,
    address: str | None = None,
    phone: str | None = None,
    contact_email: str | None = None,
) -> Tenant:
    tenant = await get_tenant(db, tenant_id)

    if name is not None:
        tenant.name = name
    if nif is not None:
        tenant.nif = nif
    if address is not None:
        tenant.address = address
    if phone is not None:
        tenant.phone = phone
    if contact_email is not None:
        tenant.contact_email = contact_email

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ValueError("Ya existe otra empresa con ese NIF. Usa un NIF distinto.")

    await db.refresh(tenant)
    return tenant


# ── LLM Config ───────────────────────────────────────────────────────────────


def _decrypt_keys(cfg: TenantLlmConfig | None) -> dict:
    if cfg and cfg.encrypted_keys:
        try:
            return decrypt_credentials(cfg.encrypted_keys)
        except Exception:
            return {}
    return {}


def _build_providers_out(keys: dict) -> dict[str, Any]:
    providers_out: dict[str, Any] = {}
    for p in ALLOWED_LLM_PROVIDERS:
        pdata = keys.get(p, {})
        providers_out[p] = {
            "model": pdata.get("model", ""),
            "enabled": pdata.get("enabled", False),
            "has_key": bool(pdata.get("api_key")),
        }
    return providers_out


async def get_llm_config(db: AsyncSession, tenant_id: UUID) -> dict[str, Any]:
    result = await db.execute(select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == tenant_id))
    cfg = result.scalar_one_or_none()
    keys = _decrypt_keys(cfg)

    return {
        "active_llm_provider": cfg.active_llm_provider if cfg else "claude_code",
        "active_embeddings_provider": cfg.active_embeddings_provider if cfg else "local",
        "providers": _build_providers_out(keys),
    }


async def update_llm_config(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    active_llm_provider: str | None = None,
    active_embeddings_provider: str | None = None,
    providers: dict[str, LlmProviderConfig] | None = None,
) -> dict[str, Any]:
    if active_llm_provider and active_llm_provider not in ALLOWED_LLM_PROVIDERS:
        raise ValueError(f"Provider LLM no válido: {active_llm_provider}")
    if (
        active_embeddings_provider
        and active_embeddings_provider not in ALLOWED_EMBEDDINGS_PROVIDERS
    ):
        raise ValueError(f"Provider embeddings no válido: {active_embeddings_provider}")

    result = await db.execute(select(TenantLlmConfig).where(TenantLlmConfig.tenant_id == tenant_id))
    cfg = result.scalar_one_or_none()
    existing_keys = _decrypt_keys(cfg)

    if providers:
        for provider, pdata in providers.items():
            if provider not in ALLOWED_LLM_PROVIDERS:
                continue
            entry = existing_keys.get(provider, {})
            if pdata.api_key and pdata.api_key != _MASKED:
                entry["api_key"] = pdata.api_key
            if pdata.model is not None:
                entry["model"] = pdata.model
            entry["enabled"] = pdata.enabled
            existing_keys[provider] = entry

    if not cfg:
        cfg = TenantLlmConfig(tenant_id=tenant_id)
        db.add(cfg)

    if active_llm_provider:
        cfg.active_llm_provider = active_llm_provider
    if active_embeddings_provider:
        cfg.active_embeddings_provider = active_embeddings_provider
    if existing_keys:
        cfg.encrypted_keys = encrypt_credentials(existing_keys)

    await db.commit()
    await db.refresh(cfg)

    return {
        "active_llm_provider": cfg.active_llm_provider,
        "active_embeddings_provider": cfg.active_embeddings_provider,
        "providers": _build_providers_out(existing_keys),
    }


# ── Claude Code CLI ──────────────────────────────────────────────────────────


def _run_cmd(args: list[str], timeout: int = 120) -> tuple[int, str, str]:
    """Ejecuta un comando y devuelve (returncode, stdout, stderr)."""
    bin_path = shutil.which(args[0])
    if not bin_path:
        bin_path = shutil.which(args[0] + ".cmd")
    if bin_path:
        args = [bin_path] + args[1:]
    try:
        r = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
            env={**os.environ, "NO_COLOR": "1"},
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except FileNotFoundError:
        return -1, "", f"Comando no encontrado: {args[0]}"
    except subprocess.TimeoutExpired:
        return -2, "", f"Timeout ejecutando: {' '.join(args)}"
    except Exception as e:
        return -3, "", str(e)


def _find_claude_bin() -> str | None:
    return shutil.which("claude") or shutil.which("claude.cmd")


async def _ensure_claude_installed() -> tuple[str | None, str | None]:
    """Returns (claude_bin_path, error_message). One will be None."""
    loop = asyncio.get_event_loop()
    claude_bin = _find_claude_bin()

    if claude_bin:
        return claude_bin, None

    npm_bin = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm_bin:
        return None, "Node.js no está instalado. Descárgalo desde https://nodejs.org/"

    code, out, err = await loop.run_in_executor(
        None, _run_cmd, ["npm", "install", "-g", "@anthropic-ai/claude-code"]
    )
    if code != 0:
        return None, f"Error instalando Claude Code: {err or out}"

    claude_bin = _find_claude_bin()
    if not claude_bin:
        return None, "Se instaló pero no se encuentra en el PATH. Reinicia la aplicación."

    return claude_bin, None


async def claude_code_setup() -> dict[str, Any]:
    loop = asyncio.get_event_loop()

    claude_bin, error = await _ensure_claude_installed()
    if error:
        return {"status": "error", "version": None, "message": error}

    code, version, _err = await loop.run_in_executor(None, _run_cmd, ["claude", "--version"])
    if code != 0:
        version = "desconocida"

    code, auth_out, auth_err = await loop.run_in_executor(
        None, _run_cmd, ["claude", "auth", "status"]
    )

    is_authenticated = False
    if code == 0 and auth_out:
        try:
            auth_data = _json.loads(auth_out)
            is_authenticated = auth_data.get("loggedIn", False) is True
        except (ValueError, KeyError):
            full_output = f"{auth_out} {auth_err}".lower()
            is_authenticated = (
                "logged in" in full_output
                or "authenticated" in full_output
                or "active" in full_output
            )

    if is_authenticated:
        return {
            "status": "ready",
            "version": version,
            "message": "Claude Code instalado y autenticado.",
        }

    return {
        "status": "needs_auth",
        "version": version,
        "message": "Abre un terminal y ejecuta: claude",
    }


async def claude_code_login() -> dict[str, Any]:
    claude_bin, error = await _ensure_claude_installed()
    if error:
        return {"status": "error", "version": None, "message": error}

    try:
        subprocess.Popen(
            [claude_bin, "auth", "login"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except Exception as e:
        return {"status": "error", "version": None, "message": f"Error lanzando login: {e}"}

    return {
        "status": "needs_auth",
        "version": None,
        "message": "Se ha abierto el navegador para iniciar sesión. Completa el login y pulsa 'Verificar conexión'.",
    }


async def claude_code_logout() -> dict[str, Any]:
    loop = asyncio.get_event_loop()
    code, out, err = await loop.run_in_executor(None, _run_cmd, ["claude", "auth", "logout"])

    if code == 0:
        return {
            "status": "needs_auth",
            "version": None,
            "message": "Sesión de Claude Code cerrada correctamente.",
        }

    return {
        "status": "error",
        "version": None,
        "message": f"Error al cerrar sesión: {err or out}",
    }
