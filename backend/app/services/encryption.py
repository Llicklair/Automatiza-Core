"""
Servicio de cifrado/descifrado de credenciales de integraciones por tenant.
Usa Fernet (AES-128-CBC + HMAC-SHA256). Nunca se almacenan en texto plano.
"""
import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """Devuelve la instancia Fernet con la clave maestra del entorno garantizando formato."""
    key_str = settings.TENANT_ENCRYPTION_KEY.encode()
    key_bytes = hashlib.sha256(key_str).digest()
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
