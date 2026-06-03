"""La custodia de certificados AEAT debe funcionar con la clave del desktop.

Bug: certificate_storage._fernet() llamaba a Fernet(key) directo, así que con la
clave que genera el desktop (base64url de 32 bytes, 43 chars sin padding — NO es
un Fernet key válido) lanzaba CertificateError y la subida del .p12 fallaba.
Fix: delega en encryption.get_fernet(), que deriva con PBKDF2 si hace falta.
"""

import base64
import os

from app.services.aeat import certificate_storage as cs


def _desktop_style_key() -> str:
    # Igual que desktop/service-manager.js: randomBytes(32).base64url (sin padding).
    return base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("=")


def test_fernet_works_with_desktop_base64url_key(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_ENCRYPTION_KEY", _desktop_style_key())
    # Antes: CertificateError. Ahora: Fernet válido (derivado con PBKDF2).
    fer = cs._fernet()
    token = fer.encrypt(b"contenido-pfx-de-prueba")
    assert fer.decrypt(token) == b"contenido-pfx-de-prueba"


def test_fernet_still_works_with_valid_fernet_key(monkeypatch):
    from cryptography.fernet import Fernet

    from app.core.config import settings

    monkeypatch.setattr(settings, "TENANT_ENCRYPTION_KEY", Fernet.generate_key().decode())
    fer = cs._fernet()
    token = fer.encrypt(b"x")
    assert fer.decrypt(token) == b"x"
