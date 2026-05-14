"""Paquete de backup — local (legacy_local) + remoto cifrado E2E (BAK.B2).

Re-exporta los símbolos que los callers existentes esperaban encontrar
en el antiguo `services/backup.py` plano para preservar la API pública.
"""

# Backup local — funciones legacy del módulo plano original.
from app.services.backup.legacy_local import (
    _default_backup_dir,
    create_backup,
    delete_backup,
    get_backup_path,
    list_backups,
    restore_backup,
    rotate_backups,
    run_backup_job,
)

# Backup remoto E2E (BAK.B2 — crypto + retention).
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
    # Local (legacy)
    "_default_backup_dir",
    "create_backup",
    "delete_backup",
    "get_backup_path",
    "list_backups",
    "restore_backup",
    "rotate_backups",
    "run_backup_job",
    # Remote E2E
    "BackupCandidate",
    "apply_rolling_retention",
    "decrypt_e2e",
    "derive_key_from_password",
    "encrypt_e2e",
    "new_salt",
]
