"""Validación de licencia contra el servidor externo.

Protecciones:
- Caché firmada con HMAC(machine_id) → edición manual invalida la firma.
- machine_id verificado en caché → el JSON copiado a otra máquina no sirve.
- Gracia offline limitada a 7 días → bloquear el servidor solo aguanta una semana.
- Variable de desarrollo no obvia → AP_DEVMODE=1.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import platform
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from app.core.config import settings

logger = logging.getLogger(__name__)

LICENSE_SERVER    = "https://automatizacore-license-server.onrender.com"
CACHE_TTL_HOURS   = 24
OFFLINE_GRACE_DAYS = 7
REQUEST_TIMEOUT   = 8

# Ed25519 public key — hardcoded to prevent fake-server attacks
_PUBLIC_KEY_B64 = "Jen8cURct8egCXVhCxHlnXjo8Qaczi7X9Ml6uAkHHxY="

def _verify_server_sig(nonce: str, plan: str, sig_b64: str) -> bool:
    """Verify that the validate response was signed by our real server."""
    if not sig_b64:
        return False
    try:
        raw_pub = base64.b64decode(_PUBLIC_KEY_B64)
        pub_key = Ed25519PublicKey.from_public_bytes(raw_pub)
        message = f"{nonce}:{plan}".encode()
        pub_key.verify(base64.b64decode(sig_b64), message)
        return True
    except (InvalidSignature, Exception):
        return False

_appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
LICENSE_FILE = Path(_appdata) / "AutomatizaCore" / "license.json"


# ── Machine ID ────────────────────────────────────────────────────────────────

def get_machine_id() -> str:
    if platform.system() == "Windows":
        try:
            import winreg
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            guid, _ = winreg.QueryValueEx(k, "MachineGuid")
            return str(guid)
        except Exception:
            logger.debug("No se pudo leer MachineGuid del registro; uso uuid.getnode()", exc_info=True)
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

    if settings.AP_DEVMODE == "1":
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
            logger.debug("Fecha de caché ilegible; revalido contra el servidor", exc_info=True)

    # Llamada al servidor
    try:
        nonce = secrets.token_hex(16)
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(
                f"{LICENSE_SERVER}/licenses/validate",
                json={"key": key, "machine_id": machine_id, "nonce": nonce},
            )
        if resp.status_code == 200:
            data = resp.json()
            plan = data.get("plan", "pro")
            sig  = data.get("sig", "")
            if not _verify_server_sig(nonce, plan, sig):
                logger.error("[LICENSE] Firma del servidor inválida — posible servidor falso")
                return LicenseResult(valid=False, reason="Respuesta del servidor no autenticada.")
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
                logger.debug("Fecha de última validación ilegible; sin gracia offline", exc_info=True)
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
