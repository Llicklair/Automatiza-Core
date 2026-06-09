"""Validación de licencia contra el servidor externo.

Flujo:
- ENV=development → siempre válida (sin llamada al servidor).
- Caché local de 24 h en %APPDATA%/AutomatizaPyme/license.json para evitar
  bloqueos por cold-start de Render (Render duerme ~15 min de inactividad).
- Si el servidor es inalcanzable → concedemos gracia (no bloqueamos al usuario).
- Si el servidor devuelve 403/404 → licencia inválida.
"""

import json
import logging
import os
import platform
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

LICENSE_SERVER = "https://automatizapyme-license-server.onrender.com"
CACHE_TTL_HOURS = 24
REQUEST_TIMEOUT = 8  # segundos; Render puede tardar en despertar

# Ruta del fichero de caché/licencia
_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
LICENSE_FILE = Path(_appdata) / "AutomatizaPyme" / "license.json"


# ── Machine ID ────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    """ID estable de la máquina. Windows: MachineGuid del registro."""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
            )
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(guid)
        except Exception:
            pass
    return str(uuid.getnode())


# ── Lectura / escritura del fichero local ─────────────────────────────────────

def _read_cache() -> dict:
    try:
        return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    try:
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LICENSE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("[LICENSE] No se pudo guardar la caché: %s", e)


def get_stored_key() -> str | None:
    return _read_cache().get("key")


def save_license(key: str, plan: str) -> None:
    cache = _read_cache()
    cache.update(
        key=key,
        plan=plan,
        machine_id=get_machine_id(),
        last_validated=datetime.now(timezone.utc).isoformat(),
    )
    _write_cache(cache)


# ── Validación ────────────────────────────────────────────────────────────────

class LicenseResult:
    def __init__(self, valid: bool, plan: str = "", reason: str = ""):
        self.valid = valid
        self.plan = plan
        self.reason = reason


async def validate_license() -> LicenseResult:
    """Valida la licencia. Llama al servidor solo si la caché expiró."""

    # Modo desarrollo: sin validación
    if os.environ.get("ENV") == "development":
        return LicenseResult(valid=True, plan="dev")

    cache = _read_cache()
    key = cache.get("key")

    if not key:
        return LicenseResult(valid=False, reason="Sin licencia. Ve a Configuración → Licencia.")

    # Comprobar caché < 24 h
    last_str = cache.get("last_validated", "")
    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
            if datetime.now(timezone.utc) - last < timedelta(hours=CACHE_TTL_HOURS):
                logger.info("[LICENSE] Caché válida hasta %s", last + timedelta(hours=CACHE_TTL_HOURS))
                return LicenseResult(valid=True, plan=cache.get("plan", "pro"))
        except Exception:
            pass

    # Llamada al servidor
    machine_id = get_machine_id()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{LICENSE_SERVER}/licenses/validate",
                json={"key": key, "machine_id": machine_id},
            )
        if resp.status_code == 200:
            data = resp.json()
            plan = data.get("plan", "pro")
            save_license(key, plan)
            logger.info("[LICENSE] Válida · plan=%s", plan)
            return LicenseResult(valid=True, plan=plan)
        else:
            logger.warning("[LICENSE] Servidor rechazó la clave: %s", resp.text[:200])
            return LicenseResult(valid=False, reason="Licencia desactivada o inválida.")
    except Exception as e:
        # Servidor inalcanzable → gracia: no bloqueamos al usuario
        logger.warning("[LICENSE] Servidor inalcanzable (%s) — gracia concedida", e)
        return LicenseResult(valid=True, plan=cache.get("plan", "pro"), reason="offline")


async def activate_license(key: str) -> LicenseResult:
    """Primera activación: vincula esta máquina a la clave."""
    machine_id = get_machine_id()
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{LICENSE_SERVER}/licenses/activate",
                json={"key": key, "machine_id": machine_id},
            )
        if resp.status_code == 200:
            plan = resp.json().get("plan", "pro")
            save_license(key, plan)
            return LicenseResult(valid=True, plan=plan)
        detail = resp.json().get("detail", resp.text[:200])
        return LicenseResult(valid=False, reason=detail)
    except Exception as e:
        return LicenseResult(valid=False, reason=f"No se pudo conectar al servidor: {e}")
