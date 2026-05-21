"""Persistencia de sesiones de firma AutoFirma (F3.11).

Encadena `build_autofirma_uri` + persistencia en `signed_documents`. La
ruta usa estas dos funciones; la lógica de URI/parse vive en
`autofirma.py` para poder testearla sin DB.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.signed_document import SignedDocument
from app.services.signing.autofirma import (
    AutoFirmaError,
    SignatureFormat,
    build_autofirma_uri,
    extract_signature_metadata,
    file_sha256,
    parse_autofirma_response,
)


def _new_session_token() -> str:
    # 32 chars hex = 16 bytes — suficiente entropía y compat AutoFirma.
    return secrets.token_hex(16)


async def start_signing_session(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    document_bytes: bytes,
    document_id: UUID | None,
    signature_format: SignatureFormat,
    storage_servlet_url: str,
    retriever_servlet_url: str,
    algorithm: str = "SHA512withRSA",
    visible_signature: bool = False,
) -> dict[str, Any]:
    """Crea la fila pending en `signed_documents` y devuelve URI + token."""
    token = _new_session_token()
    uri, doc_hash = build_autofirma_uri(
        document_bytes,
        signature_format=signature_format,
        storage_servlet_url=storage_servlet_url,
        retriever_servlet_url=retriever_servlet_url,
        session_token=token,
        algorithm=algorithm,
        visible_signature=visible_signature,
    )

    sd = SignedDocument(
        tenant_id=tenant_id,
        document_id=document_id,
        session_token=token,
        signature_format=signature_format.value,
        status="pending",
        original_hash=doc_hash,
    )
    db.add(sd)
    await db.commit()
    await db.refresh(sd)

    return {
        "session_token": token,
        "signed_document_id": str(sd.id),
        "autofirma_uri": uri,
        "original_hash": doc_hash,
        "signature_format": signature_format.value,
    }


async def process_signed_callback(
    db: AsyncSession,
    session_token: str,
    payload: dict | bytes | str,
) -> dict[str, Any]:
    """Procesa la respuesta del cliente AutoFirma.

    Marca la fila como `signed` (o `failed`), extrae metadata mínima del
    documento firmado, calcula el hash del resultado. Devuelve el dict
    actualizado.
    """
    res = await db.execute(
        sa.select(SignedDocument).where(SignedDocument.session_token == session_token)
    )
    sd = res.scalar_one_or_none()
    if sd is None:
        raise AutoFirmaError(f"Sesión de firma no encontrada: {session_token}")
    if sd.status == "signed":
        return _signed_doc_to_dict(sd)

    try:
        parsed = parse_autofirma_response(payload)
    except AutoFirmaError as e:
        sd.status = "failed"
        sd.metadata_json = {"error": str(e)}
        await db.commit()
        raise

    signed_bytes = parsed["signed_bytes"]
    if not signed_bytes:
        sd.status = "failed"
        sd.metadata_json = {"error": "Respuesta vacía."}
        await db.commit()
        raise AutoFirmaError("Respuesta de AutoFirma sin datos firmados.")

    fmt = SignatureFormat(sd.signature_format)
    meta = extract_signature_metadata(signed_bytes, fmt)

    sd.signed_hash = file_sha256(signed_bytes)
    sd.signer_nif = meta.get("signer_nif")
    sd.signer_cn = meta.get("signer_cn")
    sd.issuer_cn = meta.get("issuer_cn")
    sd.metadata_json = {
        "has_signature": bool(meta.get("has_signature")),
        "raw_size": len(signed_bytes),
    }
    sd.signed_at = datetime.utcnow()
    sd.status = "signed" if meta.get("has_signature") else "failed"
    await db.commit()
    await db.refresh(sd)

    return _signed_doc_to_dict(sd) | {"signed_bytes": signed_bytes}


def _signed_doc_to_dict(sd: SignedDocument) -> dict[str, Any]:
    return {
        "id": str(sd.id),
        "tenant_id": str(sd.tenant_id),
        "document_id": str(sd.document_id) if sd.document_id else None,
        "session_token": sd.session_token,
        "signature_format": sd.signature_format,
        "status": sd.status,
        "original_hash": sd.original_hash,
        "signed_hash": sd.signed_hash,
        "signer_nif": sd.signer_nif,
        "signer_cn": sd.signer_cn,
        "issuer_cn": sd.issuer_cn,
        "signed_at": sd.signed_at.isoformat() if sd.signed_at else None,
    }
