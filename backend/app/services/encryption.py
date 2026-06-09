"""
Servicio de cifrado/descifrado de credenciales de integraciones por tenant.
Usa Fernet (AES-128-CBC + HMAC-SHA256). Nunca se almacenan en texto plano.
"""

import base64
import logging

_logger = logging.getLogger(__name__)

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Devuelve la instancia Fernet con la clave maestra derivada mediante PBKDF2."""
    key_str = settings.TENANT_ENCRYPTION_KEY.encode()
    # Si la clave ya es un Fernet key válido (44 bytes base64url), usarla directamente
    try:
        Fernet(key_str)
        return Fernet(key_str)
    except Exception:
        _logger.debug("Raw key is not valid Fernet format, deriving with PBKDF2")
    # Derivar con PBKDF2 (100k iteraciones) para claves arbitrarias
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"automatizacore_tenant_enc_v1",
        iterations=100_000,
    )
    key_bytes = kdf.derive(key_str)
    urlsafe_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(urlsafe_key)


def get_fernet() -> Fernet:
    """Instancia Fernet con la clave maestra del tenant (derivada con PBKDF2 si
    la clave configurada no es un Fernet key válido). Reutilizable por otros
    servicios que cifran binarios (p.ej. custodia de certificados AEAT)."""
    return _get_fernet()


def encrypt_credentials(credentials: dict) -> str:
    """Cifra un diccionario de credenciales y devuelve un string base64."""
    import json

    f = _get_fernet()
    plaintext = json.dumps(credentials).encode()
    return f.encrypt(plaintext).decode()


def decrypt_credentials(encrypted: str) -> dict:
    """Descifra credenciales. Lanza excepción si el token es inválido."""
    import json

    f = _get_fernet()
    plaintext = f.decrypt(encrypted.encode())
    return json.loads(plaintext)


def encrypt_str(plaintext: str) -> str:
    """Cifra un string y devuelve base64. Cadena vacía/None → se devuelve igual."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_str(token: str) -> str:
    """Descifra un string cifrado con `encrypt_str`.

    Compat hacia atrás: si el valor no es un token Fernet válido (filas legacy
    guardadas en texto plano antes de introducir el cifrado), lo devuelve tal
    cual con un warning, en vez de lanzar. Permite migrar sin script de datos.
    """
    if not token:
        return token
    from cryptography.fernet import InvalidToken

    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        _logger.warning("decrypt_str: valor no cifrado (legacy en texto plano), devuelto tal cual")
        return token
