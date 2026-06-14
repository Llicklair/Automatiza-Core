"""Custodia de certificados digitales (.pfx/.p12) de cada tenant.

El binario PFX y su contraseña se almacenan cifrados con Fernet usando la
clave global `settings.TENANT_ENCRYPTION_KEY`. Solo se descifran en memoria
al firmar un XML. El endpoint público NUNCA devuelve el contenido cifrado
ni la contraseña — solo metadatos del certificado (sujeto, validez, sha256).

Política: máximo 1 certificado `status='active'` por tenant. Subir uno nuevo
revoca automáticamente el anterior. Mantener histórico para auditoría.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.accounting import TenantCertificate

_log = logging.getLogger(__name__)


class CertificateError(RuntimeError):
    pass


def _fernet() -> Fernet:
    # Reutiliza la derivación de clave de services.encryption: si
    # TENANT_ENCRYPTION_KEY no es un Fernet key válido (p.ej. la base64url de 43
    # chars que genera el desktop por safeStorage), la deriva con PBKDF2. Antes
    # se llamaba a Fernet(key) directo y petaba con esa clave.
    from app.services.encryption import get_fernet

    try:
        return get_fernet()
    except Exception as e:
        raise CertificateError(f"TENANT_ENCRYPTION_KEY inválida: {e}") from e


@dataclass
class CertificateMetadata:
    subject_cn: str | None
    issuer_cn: str | None
    valid_from: datetime | None
    valid_until: datetime | None
    serial_number: str | None
    sha256_fingerprint: str | None


def _extract_metadata(pfx_bytes: bytes, password: str) -> CertificateMetadata:
    """Extrae metadatos del PFX sin guardar nada. Si cryptography no soporta
    PFX (windows en algunos casos), devuelve metadatos vacíos.
    """
    try:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.serialization import pkcs12
    except ImportError:
        return CertificateMetadata(None, None, None, None, None, None)

    try:
        priv_key, cert, _ = pkcs12.load_key_and_certificates(
            pfx_bytes, password.encode("utf-8") if password else None,
        )
    except Exception as e:
        raise CertificateError(f"No se pudo leer el PFX (contraseña incorrecta o fichero inválido): {e}") from e

    if cert is None:
        raise CertificateError("El PFX no contiene un certificado X.509 válido.")

    subject = cert.subject.rfc4514_string() if cert.subject else None
    issuer = cert.issuer.rfc4514_string() if cert.issuer else None
    fp = cert.fingerprint(hashes.SHA256()).hex()
    return CertificateMetadata(
        subject_cn=subject[:255] if subject else None,
        issuer_cn=issuer[:255] if issuer else None,
        valid_from=cert.not_valid_before_utc if hasattr(cert, "not_valid_before_utc") else cert.not_valid_before,
        valid_until=cert.not_valid_after_utc if hasattr(cert, "not_valid_after_utc") else cert.not_valid_after,
        serial_number=str(cert.serial_number)[:80],
        sha256_fingerprint=fp,
    )


async def store_certificate(
    db: AsyncSession,
    tenant_id: UUID,
    user_id: UUID | None,
    label: str,
    pfx_bytes: bytes,
    password: str,
    notes: str | None = None,
) -> TenantCertificate:
    """Sube un certificado nuevo. Revoca el anterior si existe."""
    if not pfx_bytes or len(pfx_bytes) < 100:
        raise CertificateError("El fichero PFX está vacío o es demasiado pequeño.")
    if len(pfx_bytes) > 200 * 1024:
        raise CertificateError("El fichero PFX supera el límite de 200 KB.")
    if not password:
        raise CertificateError("La contraseña del PFX es obligatoria.")

    meta = _extract_metadata(pfx_bytes, password)

    fer = _fernet()
    enc_pfx = fer.encrypt(pfx_bytes)
    enc_pwd = fer.encrypt(password.encode("utf-8")).decode("ascii")

    # Revocar activo previo
    await db.execute(
        update(TenantCertificate)
        .where(TenantCertificate.tenant_id == tenant_id)
        .where(TenantCertificate.status == "active")
        .values(status="revoked", revoked_at=datetime.now())
    )

    cert = TenantCertificate(
        tenant_id=tenant_id,
        label=label[:120] or "Certificado",
        subject_cn=meta.subject_cn,
        issuer_cn=meta.issuer_cn,
        valid_from=meta.valid_from,
        valid_until=meta.valid_until,
        serial_number=meta.serial_number,
        sha256_fingerprint=meta.sha256_fingerprint,
        encrypted_pfx=enc_pfx,
        encrypted_password=enc_pwd,
        status="active",
        uploaded_by_id=user_id,
        notes=(notes or "")[:500] or None,
    )
    db.add(cert)
    await db.commit()
    await db.refresh(cert)
    _log.info("Certificate stored for tenant=%s subject=%s", tenant_id, meta.subject_cn)
    return cert


async def get_active_certificate(
    db: AsyncSession, tenant_id: UUID,
) -> TenantCertificate | None:
    res = await db.execute(
        select(TenantCertificate)
        .where(TenantCertificate.tenant_id == tenant_id)
        .where(TenantCertificate.status == "active")
        .order_by(TenantCertificate.uploaded_at.desc())
        .limit(1)
    )
    return res.scalar_one_or_none()


async def load_decrypted(
    db: AsyncSession, tenant_id: UUID,
) -> tuple[bytes, str]:
    """Devuelve (pfx_bytes, password) descifrados. Solo para firma en memoria."""
    cert = await get_active_certificate(db, tenant_id)
    if cert is None:
        raise CertificateError("No hay certificado activo para este tenant.")
    fer = _fernet()
    try:
        pfx = fer.decrypt(cert.encrypted_pfx)
        pwd = fer.decrypt(cert.encrypted_password.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise CertificateError("Clave de cifrado inválida — no se puede descifrar el certificado.") from e
    return pfx, pwd


async def revoke_certificate(
    db: AsyncSession, tenant_id: UUID, certificate_id: UUID,
) -> TenantCertificate:
    res = await db.execute(
        select(TenantCertificate)
        .where(TenantCertificate.id == certificate_id)
        .where(TenantCertificate.tenant_id == tenant_id)
    )
    cert = res.scalar_one_or_none()
    if cert is None:
        raise LookupError("Certificado no encontrado")
    cert.status = "revoked"
    cert.revoked_at = datetime.now()
    await db.commit()
    await db.refresh(cert)
    return cert


def cert_to_dict(cert: TenantCertificate) -> dict:
    """Metadatos seguros (sin secretos)."""
    return {
        "id": str(cert.id),
        "label": cert.label,
        "subject_cn": cert.subject_cn,
        "issuer_cn": cert.issuer_cn,
        "valid_from": cert.valid_from.isoformat() if cert.valid_from else None,
        "valid_until": cert.valid_until.isoformat() if cert.valid_until else None,
        "serial_number": cert.serial_number,
        "sha256_fingerprint": cert.sha256_fingerprint,
        "status": cert.status,
        "uploaded_at": cert.uploaded_at.isoformat() if cert.uploaded_at else None,
        "revoked_at": cert.revoked_at.isoformat() if cert.revoked_at else None,
        "notes": cert.notes,
        "is_expired": (
            cert.valid_until is not None
            and cert.valid_until.replace(tzinfo=None) < datetime.utcnow()
        ),
    }
