"""Instalación de certificados digitales PKCS#12 (.p12 / .pfx) por tenant.

Toda la gestión del filesystem (escribir el .p12, borrarlo en caso de
contraseña inválida) y la actualización del modelo `Tenant` viven aquí.
La ruta HTTP solo valida el MIME y delega.

Reutilizable desde un workflow de renovación automática de certificados
o desde un comando CLI de setup inicial.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.auth import Tenant
from app.services.billing.xades_signer import load_certificate_info

_CERT_DIR = Path("uploads/certs")


class CertificateError(Exception):
    """Error de carga o validación del certificado (contraseña, formato)."""


@dataclass
class CertificateInfo:
    subject: str
    expires_at: datetime
    fingerprint: str | None = None


async def install_certificate(
    file_bytes: bytes,
    password: str,
    tenant_id: UUID,
    db: AsyncSession,
) -> CertificateInfo:
    """Persiste el certificado en disco, valida con la contraseña y actualiza
    el tenant.

    Levanta `CertificateError` si la contraseña es inválida o el archivo
    no es un PKCS#12 válido. En ese caso, el .p12 escrito se elimina del
    disco antes de propagar el error.
    """
    cert_dir = _CERT_DIR / str(tenant_id)
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_path = cert_dir / "cert.p12"

    cert_path.write_bytes(file_bytes)

    try:
        info = load_certificate_info(str(cert_path), password)
    except Exception as exc:  # noqa: BLE001 — wrap en error de dominio
        cert_path.unlink(missing_ok=True)
        raise CertificateError(
            f"Certificado inválido o contraseña incorrecta: {exc}"
        ) from exc

    expires_at = datetime.fromisoformat(info["expires_at"])

    res = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = res.scalar_one_or_none()
    if tenant is None:
        cert_path.unlink(missing_ok=True)
        raise CertificateError("Tenant no encontrado")

    tenant.cert_path = str(cert_path)
    tenant.cert_password = password
    tenant.cert_subject = info["subject"]
    tenant.cert_expires_at = expires_at
    await db.commit()

    return CertificateInfo(
        subject=info["subject"],
        expires_at=expires_at,
        fingerprint=info.get("fingerprint"),
    )
