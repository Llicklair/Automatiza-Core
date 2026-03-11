"""
Servicio de cifrado/descifrado de credenciales de integraciones por tenant.
Usa Fernet (AES-128-CBC + HMAC-SHA256). Nunca se almacenan en texto plano.
"""
import base64
import hashlib

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Devuelve la instancia Fernet con la clave maestra derivada mediante PBKDF2."""
    key_str = settings.TENANT_ENCRYPTION_KEY.encode()
    # Si la clave ya es un Fernet key válido (44 bytes base64url), usarla directamente
    try:
        Fernet(key_str)
        return Fernet(key_str)
    except Exception:
        pass
    # Derivar con PBKDF2 (100k iteraciones) para claves arbitrarias
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"automatizapyme_tenant_enc_v1",
        iterations=100_000,
    )
    key_bytes = kdf.derive(key_str)
    urlsafe_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(urlsafe_key)


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
