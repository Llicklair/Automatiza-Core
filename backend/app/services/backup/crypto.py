"""Cifrado E2E para backup remoto Backblaze B2 (BAK.B2).

Consensuado (Ronda 17 §93 + Ronda 18 §99): backup B2 **opcional**, cifrado
**client-side** con AES-256-GCM. La clave se deriva del password del usuario
con PBKDF2-HMAC-SHA256 (1M iteraciones). El VPS guarda blobs opacos que no
puede descifrar.

Copy aceptado en MARKETING.md: *"Si activas la copia en la nube,
AutomatizaCore almacena tus datos cifrados en un servidor externo. Solo tú
tienes la clave."*

Formato del blob cifrado (versionado para evolución futura):

    [1 byte  version=1]
    [16 bytes salt]
    [12 bytes nonce]
    [N bytes ciphertext + 16 bytes tag GCM]

El salt se persiste DENTRO del blob para que el restore sea posible sin
metadata adicional — basta con tener el password.
"""

from __future__ import annotations

import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

_PBKDF2_ITERATIONS = 1_000_000  # ~1.2s en CPU moderna — coste deliberado
_SALT_BYTES = 16
_NONCE_BYTES = 12
_KEY_BYTES = 32  # AES-256
_BLOB_VERSION = 1


def new_salt() -> bytes:
    """Genera un salt aleatorio criptográficamente seguro."""
    return secrets.token_bytes(_SALT_BYTES)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Deriva clave AES-256 desde password + salt con PBKDF2-HMAC-SHA256.

    Coste deliberadamente alto (1M iteraciones) para resistir ataques por
    diccionario si el blob cae en manos del atacante.
    """
    if not password:
        raise ValueError("password vacío no admitido")
    if len(salt) != _SALT_BYTES:
        raise ValueError(f"salt debe ser de {_SALT_BYTES} bytes")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_BYTES,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_e2e(data: bytes, password: str, salt: bytes | None = None) -> bytes:
    """Cifra `data` con AES-256-GCM usando clave derivada del password.

    Genera salt nuevo si no se proporciona. El blob resultante incluye
    versión + salt + nonce + ciphertext+tag de forma que `decrypt_e2e()`
    pueda descifrar conociendo solo el password.
    """
    if salt is None:
        salt = new_salt()

    key = derive_key_from_password(password, salt)
    nonce = secrets.token_bytes(_NONCE_BYTES)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, data, associated_data=None)

    # Estructura: version(1) | salt(16) | nonce(12) | ciphertext+tag
    return bytes([_BLOB_VERSION]) + salt + nonce + ciphertext


def decrypt_e2e(blob: bytes, password: str) -> bytes:
    """Descifra un blob producido por `encrypt_e2e()`.

    Lanza `ValueError` si:
    - El blob tiene versión desconocida.
    - El password es incorrecto (GCM detecta tampering).
    - El blob es demasiado corto para ser válido.
    """
    min_len = 1 + _SALT_BYTES + _NONCE_BYTES + 16  # 16 = tag GCM
    if len(blob) < min_len:
        raise ValueError("Blob corrupto: tamaño insuficiente.")

    version = blob[0]
    if version != _BLOB_VERSION:
        raise ValueError(f"Versión de blob no soportada: {version}")

    salt = blob[1 : 1 + _SALT_BYTES]
    nonce = blob[1 + _SALT_BYTES : 1 + _SALT_BYTES + _NONCE_BYTES]
    ciphertext = blob[1 + _SALT_BYTES + _NONCE_BYTES :]

    key = derive_key_from_password(password, salt)
    aesgcm = AESGCM(key)
    try:
        return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    except Exception as e:
        raise ValueError("Password incorrecto o blob corrupto.") from e
