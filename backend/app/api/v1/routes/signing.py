"""Rutas de firma electrónica AutoFirma (F3.11)."""

from __future__ import annotations

import base64
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.base import get_db
from app.db.models.auth import User
from app.middleware.rate_limit import limiter
from app.services.signing import (
    AutoFirmaError,
    SignatureFormat,
    process_signed_callback,
    start_signing_session,
)

router = APIRouter(prefix="/signing", tags=["signing"])


def _default_servlet_url(path: str) -> str:
    """Construye URL absoluta del callback usando el host del backend.

    AutoFirma necesita una URL accesible para POST. En desktop esto será
    `http://localhost:<port>/api/v1/signing/...`; en cloud el dominio real.
    """
    base = getattr(settings, "PUBLIC_BASE_URL", None) or "http://localhost:8080"
    return f"{base.rstrip('/')}{path}"


@router.post("/autofirma/init", status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def init_autofirma(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Inicia una sesión de firma. Devuelve URI `afirma://` y session_token.

    Body:
        {
          "document_b64": "<base64 del PDF/XML/binario>",
          "document_id": "<uuid del TenantDocument>"|null,
          "signature_format": "PAdES"|"XAdES"|"CAdES",
          "visible_signature": true|false  (solo PAdES)
        }
    """
    doc_b64 = (payload or {}).get("document_b64")
    if not doc_b64:
        raise HTTPException(status_code=422, detail="document_b64 requerido.")
    try:
        document_bytes = base64.b64decode(doc_b64)
    except Exception:
        raise HTTPException(status_code=422, detail="document_b64 inválido.")

    fmt_raw = (payload or {}).get("signature_format") or "PAdES"
    try:
        fmt = SignatureFormat(fmt_raw)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail=f"signature_format inválido: {fmt_raw}. Usa PAdES, XAdES o CAdES.",
        )

    document_id_raw = (payload or {}).get("document_id")
    document_id: uuid.UUID | None = None
    if document_id_raw:
        try:
            document_id = uuid.UUID(str(document_id_raw))
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="document_id no es UUID.")

    try:
        return await start_signing_session(
            db,
            current_user.tenant_id,
            document_bytes=document_bytes,
            document_id=document_id,
            signature_format=fmt,
            storage_servlet_url=_default_servlet_url("/api/v1/signing/autofirma/callback"),
            retriever_servlet_url=_default_servlet_url("/api/v1/signing/autofirma/retrieve"),
            visible_signature=bool((payload or {}).get("visible_signature", False)),
        )
    except AutoFirmaError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/autofirma/callback")
@limiter.limit("20/minute")
async def autofirma_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Recibe el documento firmado desde AutoFirma del cliente.

    Tres formatos posibles de body soportados:
      - JSON `{id, data}`
      - text/plain con base64
      - application/octet-stream con bytes del firmado

    Este endpoint NO requiere autenticación de usuario porque AutoFirma
    no envía cookies — la sesión se identifica por `session_token` /
    parámetro `id`. La autorización se hace por la validez del token
    creado previamente en `/autofirma/init`.
    """
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("application/json"):
        body = await request.json()
        session_token = body.get("id") or request.query_params.get("id")
        if not session_token:
            raise HTTPException(status_code=422, detail="id (session_token) requerido.")
        payload = body
    elif content_type.startswith("application/octet-stream"):
        session_token = request.query_params.get("id")
        if not session_token:
            raise HTTPException(status_code=422, detail="?id= requerido en query.")
        payload = await request.body()
    else:
        # text/plain o sin tipo
        session_token = request.query_params.get("id")
        if not session_token:
            raise HTTPException(status_code=422, detail="?id= requerido en query.")
        payload = (await request.body()).decode("utf-8", errors="ignore")

    try:
        result = await process_signed_callback(db, session_token, payload)
    except AutoFirmaError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # No devolvemos los bytes firmados al callback de AutoFirma (no los
    # necesita); sí persistimos el hash y la metadata.
    return {
        "session_token": result["session_token"],
        "status": result["status"],
        "signed_hash": result["signed_hash"],
    }
