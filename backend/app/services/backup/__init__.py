"""Backup remoto cifrado E2E (BAK.B2)."""

from app.services.backup.crypto import (
    decrypt_e2e,
    derive_key_from_password,
    encrypt_e2e,
    new_salt,
)
from app.services.backup.retention import (
    BackupCandidate,
    apply_rolling_retention,
)

__all__ = [
    "BackupCandidate",
    "apply_rolling_retention",
    "decrypt_e2e",
    "derive_key_from_password",
    "encrypt_e2e",
    "new_salt",
]
