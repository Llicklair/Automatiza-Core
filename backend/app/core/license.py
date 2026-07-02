"""Validación de licencia contra el servidor externo.

Protecciones:
- GRANT firmado por el servidor (Ed25519) que ata clave+machine_id+fecha+plan;
  se verifica OFFLINE con la clave pública embebida. Un license.json forjado a
  mano NO puede producir esta firma sin la clave privada → caché infalsificable.
- machine_id verificado en el grant → el JSON copiado a otra máquina no sirve.
- Gracia offline limitada a 7 días desde la fecha del SERVIDOR (no el reloj
  local) + marca de agua monotónica → adelantar/atrasar el reloj no la alarga.
- Sin bypass por entorno: no existe modo desarrollo que salte la validación.

Nota: nada de esto protege contra editar este propio .py (corre en la máquina
del atacante). Esa barrera es el empaquetado sin fuente, no este módulo.
"""

import base64
import hashlib
import hmac
import json
import logging
import platform
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from app.core.paths import app_data_dir

logger = logging.getLogger(__name__)

LICENSE_SERVER = "https://automatizapyme-license-server.onrender.com"
CACHE_TTL_HOURS = 24
OFFLINE_GRACE_DAYS = 7
# Cubre el cold start del free tier de Render (el dyno hiberna y tarda ~30-60s en
# despertar). Con un timeout corto, una clave válida se marcaba inválida por timeout.
REQUEST_TIMEOUT = 60

# Ed25519 public key — hardcoded to prevent fake-server attacks
_PUBLIC_KEY_B64 = "0Pop065Ihkr11kYsaA3mwv5vUPH+Vx7C9vIvCtDRgQA="


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


def _verify_grant(key: str, machine_id: str, issued_at: str, plan: str, grant_sig: str) -> bool:
    """Verifica el grant firmado por el servidor (clave privada Ed25519).

    Es el ancla de confianza REAL de la caché: sin la clave privada del servidor
    nadie puede fabricar un grant válido, así que un license.json escrito a mano
    no pasa por aquí aunque el atacante conozca el esquema (a diferencia del HMAC,
    cuya clave —el machine_id— es pública para quien lee este archivo)."""
    if not grant_sig or not key or not issued_at:
        return False
    try:
        pub_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(_PUBLIC_KEY_B64))
        message = f"{key}:{machine_id}:{issued_at}:{plan}".encode()
        pub_key.verify(base64.b64decode(grant_sig), message)
        return True
    except (InvalidSignature, Exception):
        return False


LICENSE_FILE = app_data_dir("license.json")


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


def _within_grace(issued_at: str) -> bool:
    """True si `issued_at` (fecha del SERVIDOR) está dentro de la gracia offline.

    Ancla en la fecha firmada por el servidor, no en el reloj local, así que
    adelantar el reloj no crea gracia nueva (la fecha va dentro del grant firmado).
    """
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(issued_at) <= timedelta(days=OFFLINE_GRACE_DAYS)
    except Exception:
        return False


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
        payload = _cache_payload(cache["key"], cache["plan"], cache["last_validated"], cache["machine_id"])
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


def save_license(key: str, plan: str, issued_at: str = "", grant_sig: str = "") -> None:
    machine_id = get_machine_id()
    last_validated = datetime.now(timezone.utc).isoformat()
    payload = _cache_payload(key, plan, last_validated, machine_id)
    cache = {
        "key": key,
        "plan": plan,
        "machine_id": machine_id,
        "last_validated": last_validated,
        # Grant firmado por el servidor (ancla de confianza offline) + su fecha.
        "issued_at": issued_at,
        "grant_sig": grant_sig,
        "sig": _sign(payload, machine_id),
    }
    _write_cache(cache)


# ── Validación ────────────────────────────────────────────────────────────────


class LicenseResult:
    def __init__(self, valid: bool, plan: str = "", reason: str = "", retriable: bool = False):
        self.valid = valid
        self.plan = plan
        self.reason = reason
        # retriable = fallo transitorio (servidor iniciándose), NO una clave inválida.
        self.retriable = retriable


def cached_license_state() -> LicenseResult:
    """Estado de licencia SOLO desde la caché local (sin red).

    Para el arranque instantáneo: la app no se cuelga esperando al servidor (que en
    cold start tarda ~30-60s). Concede validez si la última validación exitosa está
    dentro de la gracia offline (OFFLINE_GRACE_DAYS); la validación real contra el
    servidor corre después en background y refresca el estado.
    """
    machine_id = get_machine_id()
    cache = _read_cache()
    key = cache.get("key")
    if not key:
        return LicenseResult(valid=False, reason="sin licencia")
    if not _verify_cache(cache, machine_id):
        return LicenseResult(valid=False, reason="caché inválida o manipulada")
    # Ancla de confianza real: el grant firmado por el servidor. Sin grant válido
    # (caché forjada o de una versión antigua) no hay acceso offline: fuerza una
    # revalidación online que lo re-emite. La firma HMAC de arriba solo detecta
    # ediciones torpes; el grant es lo que un atacante NO puede fabricar.
    if not _verify_grant(
        key, machine_id, cache.get("issued_at", ""), cache.get("plan", ""), cache.get("grant_sig", "")
    ):
        return LicenseResult(valid=False, reason="grant no verificado (revalida online)")
    if _within_grace(cache.get("issued_at", "")):
        return LicenseResult(valid=True, plan=cache.get("plan", "pro"), reason="cache")
    return LicenseResult(valid=False, reason="caché caducada")


async def validate_license() -> LicenseResult:
    """Valida la licencia. Llama al servidor solo si la caché expiró.

    Sin bypass por entorno: la única vía de acceso es una licencia válida emitida
    por el servidor. Los tests fijan `app.state.license_valid` directamente; el
    flujo de validación nunca se cortocircuita.
    """
    machine_id = get_machine_id()
    cache = _read_cache()
    key = cache.get("key")

    if not key:
        return LicenseResult(valid=False, reason="Sin licencia. Ve a Configuración → Licencia.")

    # Verificar integridad y machine_id
    if not _verify_cache(cache, machine_id):
        logger.warning("[LICENSE] Caché inválida — forzando validación con servidor")
        cache = {}  # forzar llamada al servidor

    # El grant firmado es requisito para CUALQUIER acceso sin ir al servidor.
    # Una caché sin grant válido (forjada, o de una versión anterior a esta
    # protección) obliga a revalidar online, que lo re-emite.
    grant_ok = _verify_grant(
        key, machine_id, cache.get("issued_at", ""), cache.get("plan", ""), cache.get("grant_sig", "")
    )

    # Ruta rápida: evita llamar al servidor si la última validación fue hace <24h.
    # Requiere grant verificado Y que el grant siga dentro de la gracia (anclado en
    # issued_at, la fecha FIRMADA), no solo que la caché se escribiera hace poco.
    last_str = cache.get("last_validated", "")
    if grant_ok and last_str and _within_grace(cache.get("issued_at", "")):
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(last_str)
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
            sig = data.get("sig", "")
            if not _verify_server_sig(nonce, plan, sig):
                logger.error("[LICENSE] Firma del servidor inválida — posible servidor falso")
                return LicenseResult(valid=False, reason="Respuesta del servidor no autenticada.")
            # Persistir el grant firmado (ancla offline). Si el servidor no lo
            # devuelve (versión antigua), issued_at/grant_sig quedan vacíos y la
            # próxima gracia offline no se concederá — se degrada seguro.
            issued_at = data.get("issued_at", "")
            grant_sig = data.get("grant_sig", "")
            if grant_sig and not _verify_grant(key, machine_id, issued_at, plan, grant_sig):
                logger.error("[LICENSE] Grant del servidor no verifica — descartado")
                grant_sig, issued_at = "", ""
            save_license(key, plan, issued_at=issued_at, grant_sig=grant_sig)
            logger.info("[LICENSE] Válida · plan=%s", plan)
            return LicenseResult(valid=True, plan=plan)
        logger.warning("[LICENSE] Servidor rechazó la clave: %s", resp.text[:200])
        return LicenseResult(valid=False, reason="Licencia desactivada o inválida.")

    except Exception as e:
        # Servidor inalcanzable — gracia offline anclada en la fecha FIRMADA por el
        # servidor (issued_at dentro del grant), no en el reloj local manipulable.
        logger.warning("[LICENSE] Servidor inalcanzable: %s", e)
        if grant_ok and _within_grace(cache.get("issued_at", "")):
            logger.info("[LICENSE] Gracia offline concedida")
            return LicenseResult(valid=True, plan=cache.get("plan", "pro"), reason="offline")
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
            data = resp.json()
            plan = data.get("plan", "pro")
            issued_at = data.get("issued_at", "")
            grant_sig = data.get("grant_sig", "")
            if grant_sig and not _verify_grant(key, machine_id, issued_at, plan, grant_sig):
                grant_sig, issued_at = "", ""
            save_license(key, plan, issued_at=issued_at, grant_sig=grant_sig)
            return LicenseResult(valid=True, plan=plan)
        detail = resp.json().get("detail", resp.text[:200])
        return LicenseResult(valid=False, reason=detail)
    except Exception as e:
        logger.warning("[LICENSE] Activación: servidor inalcanzable (posible cold start): %s", e)
        return LicenseResult(
            valid=False,
            reason="El servidor de licencias se está iniciando. Espera unos segundos y reinténtalo.",
            retriable=True,
        )


async def warm_up_server() -> None:
    """Despierta el servidor de licencias (Render free hiberna ~30-60s).

    Fire-and-forget: se llama al ABRIR el modal de activación para que el dyno esté
    despierto cuando el usuario pulse Activar (wake-up bajo demanda, no un ping
    sintético 24/7). Ignora el resultado.
    """
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            await client.get(LICENSE_SERVER + "/", follow_redirects=True)
    except Exception:
        logger.debug("[LICENSE] warm-up del servidor falló (irrelevante)", exc_info=True)


async def refresh_app_license_state(app) -> None:
    """Revalida la licencia y refresca `app.state` (L5 — revalidación periódica).

    Pensado para el scheduler (cada 24 h): sesiones largas no se quedan con un
    estado obsoleto. Si la revalidación lanza un error inesperado, deja el estado
    como estaba (no bloquea por un fallo transitorio); `validate_license` ya
    gestiona la gracia offline internamente.
    """
    try:
        lic = await validate_license()
        app.state.license_valid = lic.valid
        app.state.license_plan = lic.plan
        logger.info("[LICENSE] Revalidación periódica: valid=%s plan=%s", lic.valid, lic.plan)
    except Exception:
        logger.exception("[LICENSE] Revalidación periódica falló (estado sin cambios)")
