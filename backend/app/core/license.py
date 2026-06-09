"""Validación de licencia contra el servidor externo.

Protecciones:
- Caché firmada con HMAC(machine_id) → edición manual invalida la firma.
- machine_id verificado en caché → el JSON copiado a otra máquina no sirve.
- Gracia offline limitada a 7 días → bloquear el servidor solo aguanta una semana.
- Variable de desarrollo no obvia → AP_DEVMODE=1.
"""

import hashlib
import hmac
import json
import logging
import os
import platform
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

LICENSE_SERVER    = "https://automatizapyme-license-server.onrender.com"
CACHE_TTL_HOURS   = 24
OFFLINE_GRACE_DAYS = 7
REQUEST_TIMEOUT   = 8

_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
LICENSE_FILE = Path(_appdata) / "AutomatizaPyme" / "license.json"


# ── Machine ID ────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    if platform.system() == "Windows":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(guid)
        except Exception:
            pass
    return str(uuid.getnode())


# ── HMAC de integridad ────────────────────────────────────────────────────────

def _sign(payload: str, machine_id: str) -> str:
    return hmac.new(
        machine_id.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def _cache_payload(key: str, plan: str, last_validated: str, machine_id: str) -> str:
    return f"{key}|{plan}|{last_validated}|{machine_id}"


# ── Lectura / escritura ───────────────────────────────────────────────────────

def _read_cache() -> dict:
    try:
        return json.loads(LICENSE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    try:
        LICENSE_FILE.parent.mkdir(parents=True, exist_ok=True)
        LICENSE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception as e:
        logger.warning("[LICENSE] No se pudo guardar la caché: %s", e)


def _verify_cache(cache: dict, machine_id: str) -> bool:
    """Verifica HMAC y machine_id. False si cualquier campo fue alterado."""
    try:
        sig = cache.get("sig", "")
        payload = _cache_payload(
            cache["key"], cache["plan"], cache["last_validated"], cache["machine_id"]
        )
        expected = _sign(payload, machine_id)
        if not hmac.compare_digest(sig, expected):
            logger.warning("[LICENSE] Firma de caché inválida — posible manipulación")
            return False
        if cache.get("machine_id") != machine_id:
            logger.warning("[LICENSE] machine_id no coincide — posible copia del fichero")
            return False
        return True
    except Exception:
        return False


def get_stored_key() -> str | None:
    return _read_cache().get("key")


def save_license(key: str, plan: str) -> None:
    machine_id = get_machine_id()
    last_validated = datetime.now(timezone.utc).isoformat()
    payload = _cache_payload(key, plan, last_validated, machine_id)
    cache = {
        "key": key,
        "plan": plan,
        "machine_id": machine_id,
        "last_validated": last_validated,
        "sig": _sign(payload, machine_id),
    }
    _write_cache(cache)


# ── Validación ────────────────────────────────────────────────────────────────

class LicenseResult:
    def __init__(self, valid: bool, plan: str = "", reason: str = ""):
        self.valid = valid
        self.plan  = plan
        self.reason = reason


async def validate_license() -> LicenseResult:
    """Valida la licencia. Llama al servidor solo si la caché expiró."""

    if os.environ.get("AP_DEVMODE") == "1":
        return LicenseResult(valid=True, plan="dev")

    machine_id = get_machine_id()
    cache = _read_cache()
    key = cache.get("key")

    if not key:
        return LicenseResult(valid=False, reason="Sin licencia. Ve a Configuración → Licencia.")

    # Verificar integridad y machine_id
    if not _verify_cache(cache, machine_id):
        logger.warning("[LICENSE] Caché inválida — forzando validación con servidor")
        cache = {}  # forzar llamada al servidor

    # Comprobar caché < 24 h (solo si la firma es válida)
    last_str = cache.get("last_validated", "")
    if last_str:
        try:
            last = datetime.fromisoformat(last_str)
            age = datetime.now(timezone.utc) - last
            if age < timedelta(hours=CACHE_TTL_HOURS):
                logger.info("[LICENSE] Caché válida (%s)", age)
                return LicenseResult(valid=True, plan=cache.get("plan", "pro"))
        except Exception:
            pass

    # Llamada al servidor
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{LICENSE_SERVER}/licenses/validate",
                json={"key": key, "machine_id": machine_id},
            )
        if resp.status_code == 200:
            plan = resp.json().get("plan", "pro")
            save_license(key, plan)
            logger.info("[LICENSE] Válida · plan=%s", plan)
            return LicenseResult(valid=True, plan=plan)
        logger.warning("[LICENSE] Servidor rechazó la clave: %s", resp.text[:200])
        return LicenseResult(valid=False, reason="Licencia desactivada o inválida.")

    except Exception as e:
        # Servidor inalcanzable — gracia máxima 7 días desde la última validación exitosa
        logger.warning("[LICENSE] Servidor inalcanzable: %s", e)
        if last_str:
            try:
                last = datetime.fromisoformat(last_str)
                if datetime.now(timezone.utc) - last <= timedelta(days=OFFLINE_GRACE_DAYS):
                    logger.info("[LICENSE] Gracia offline concedida")
                    return LicenseResult(valid=True, plan=cache.get("plan", "pro"), reason="offline")
            except Exception:
                pass
        return LicenseResult(valid=False, reason="No se pudo verificar la licencia y el período de gracia ha expirado.")


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
